from __future__ import annotations

import asyncio
import os
import time
from dataclasses import dataclass
from typing import Any

MODEL_VERSION = "jev-1.13.0"

class JevError(Exception): pass
class JevAuthError(JevError): pass
class JevSchemaError(JevError): pass
class JevRateLimited(JevError): pass
class JevOverloaded(JevError): pass
class JevTimeout(JevError): pass
class JevInvalidResponse(JevError): pass

@dataclass
class ModelOutput:
    model: str
    answers: dict[str, Any]
    usage: dict[str, int]
    mode: str
    latency_ms: float
    attempts: int

class JevClient:
    def __init__(self, api_key: str, model: str = MODEL_VERSION, mode: str = "live", deadline: float = 120, max_retries: int = 2):
        self.api_key, self.model, self.mode = api_key, model, mode
        self.deadline, self.max_retries = deadline, max_retries

    def ask(self, state: Any, question_map: dict[str, dict]) -> ModelOutput:
        if self.mode == "mock": return self._mock(question_map)
        started = time.monotonic(); attempt = 0
        while True:
            attempt += 1
            try:
                remaining = min(120.0, self.deadline) - (time.monotonic() - started)
                if remaining <= 0:
                    raise JevTimeout("Jev deadline exceeded")
                raw = self._invoke(state, question_map, remaining)
                return validate_response(raw, question_map, (time.monotonic()-started)*1000, attempt)
            except Exception as exc:
                status = getattr(exc, "status_code", None)
                if status == 401:
                    raise JevAuthError("Jev authentication failed") from None
                if status == 422:
                    raise JevSchemaError("Jev rejected request schema") from None
                if status == 429:
                    classified = JevRateLimited("Jev rate limit")
                elif status == 529:
                    classified = JevOverloaded("Jev overloaded")
                elif isinstance(exc, (TimeoutError, asyncio.TimeoutError)):
                    classified = JevTimeout("Jev request timed out")
                elif isinstance(exc, JevError):
                    classified = exc
                else:
                    raise
                if isinstance(classified, (JevAuthError, JevSchemaError, JevInvalidResponse)):
                    raise classified from None
                remaining = min(120.0, self.deadline) - (time.monotonic() - started)
                if attempt > self.max_retries or remaining <= 0:
                    raise classified from None
                response = getattr(exc, "response", None)
                headers = getattr(response, "headers", {}) or {}
                retry_after = headers.get("Retry-After") or headers.get("retry-after")
                try:
                    delay = max(0.0, float(retry_after)) if retry_after is not None else 2 ** (attempt - 1)
                except (TypeError, ValueError):
                    delay = 2 ** (attempt - 1)
                time.sleep(min(delay, remaining))

    def _invoke(self, state, questions, timeout):
        from typesafe_sdk import AsyncTypeSafeClient, Choice, Noul, RetryPolicy, Score
        async def call():
            retry = RetryPolicy(max_retries=0, backoff_initial=0.5, backoff_max=5.0, http_statuses={429, 529}, respect_retry_after=True, api_connection_error=True, api_timeout_error=True, timeout=timeout)
            async with AsyncTypeSafeClient(api_key=self.api_key, model=self.model, retry=retry, timeout=timeout) as sdk:
                qs = {k: (Choice(instructions=v["instructions"], criteria=v["criteria"]) if v["type"]=="choice" else Score(instructions=v["instructions"], criteria=v["criteria"]) if v["type"]=="score" else Noul(instructions=v["instructions"], criteria=v["criteria"])) for k,v in questions.items()}
                return await sdk.system_one(state, qs)
        result = asyncio.run(call())
        raw = result.model_dump(mode="json") if hasattr(result, "model_dump") else result
        # SDK exposes typed maps; normalize without synthesizing answer fields.
        if "answers" not in raw:
            answers = {}
            for group in ("choices", "scores", "nouls"):
                for key, value in raw.get(group, {}).items(): answers[key] = value
            raw = {"model": raw.get("model", self.model), "answers": answers, "usage": raw.get("usage", {})}
        return raw

    def _mock(self, questions):
        # Fault injection is deliberately confined to the explicitly selected mock mode.
        delay = float(os.getenv("JEV_MOCK_DELAY_SECONDS", "0"))
        if delay > 0:
            time.sleep(delay)
        fault = os.getenv("JEV_MOCK_FAULT", "").lower()
        if fault == "timeout":
            raise JevTimeout("injected mock timeout")
        if fault == "429":
            raise JevRateLimited("injected mock rate limit")
        if fault == "529":
            raise JevOverloaded("injected mock overload")
        if fault == "schema":
            return validate_response({"model": self.model, "answers": {}, "usage": {}},
                                     questions, 0, 1, "mock")
        if fault:
            raise ValueError("unknown JEV_MOCK_FAULT")
        answers = {}
        for key, q in questions.items():
            if q["type"] == "choice":
                choice = "판단 보류" if key in {"urgency", "lead_org"} else "정보 부족"
                answers[key] = {"type":"choice", "choice":choice, "confidence":0.25, "probabilities":{o: 1/len(q["criteria"]) for o in q["criteria"]}}
            elif q["type"] == "noul": answers[key] = {"type":"noul", "noul":0.5}
            else: answers[key] = {"type":"score", "score":1.0,"confidence":0.5,"probabilities":{"0":0.2,"1":0.6,"2":0.2}}
        return validate_response({"model":self.model,"answers":answers,"usage":{"input_tokens":0,"output_tokens":0}}, questions, 0, 1, "mock")

def validate_response(raw, questions, latency_ms=0, attempts=1, mode="live"):
    try:
        assert isinstance(raw, dict) and isinstance(raw["model"], str) and isinstance(raw["answers"], dict) and isinstance(raw["usage"], dict)
        assert all(isinstance(raw["usage"][k], int) and raw["usage"][k] >= 0 for k in ("input_tokens", "output_tokens"))
        assert set(questions) <= set(raw["answers"])
        for key,q in questions.items():
            a=raw["answers"][key]; assert isinstance(a,dict) and a.get("type")==q["type"]
            if q["type"]=="choice":
                assert a["choice"] in q["criteria"] and 0<=a["confidence"]<=1 and set(a["probabilities"]) == set(q["criteria"])
            elif q["type"]=="noul": assert isinstance(a["noul"],(int,float)) and 0<=a["noul"]<=1
            else: assert isinstance(a["score"],(int,float)) and isinstance(a["probabilities"],dict)
        return ModelOutput(raw["model"],raw["answers"],raw["usage"],mode,latency_ms,attempts)
    except (AssertionError, KeyError, TypeError, ValueError): raise JevInvalidResponse("Jev response schema is invalid") from None
