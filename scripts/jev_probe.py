#!/usr/bin/env python3
"""Run a real, non-sensitive Jev contract probe and write redacted evidence."""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
import httpx2

from typesafe_sdk import Choice, Noul, RetryPolicy, Score, TypeSafeClient


ROOT = Path(__file__).resolve().parents[1]
ENDPOINT = "https://api.typesafe.ai/v1/systemone"
MODELS_ENDPOINT = "https://api.typesafe.ai/v1/models"
MODEL = "jev-1.13.0"
STATE = "SAP에서 내려받은 매출 CSV를 월별로 집계해 화면에 보여 달라."


def load_jev_key() -> str:
    """Read JEV_API_KEY from .env without printing or modifying that file."""
    env_path = ROOT / ".env"
    if not env_path.is_file():
        raise RuntimeError(".env file is missing")
    for line in env_path.read_text(encoding="utf-8").splitlines():
        key, sep, value = line.partition("=")
        if sep and key.strip() == "JEV_API_KEY":
            value = value.strip().strip("\"'")
            if value:
                return value
    raise RuntimeError("JEV_API_KEY is missing from .env")


def error_probe(url: str, api_key: str, body: dict, label: str) -> dict:
    started = time.perf_counter()
    try:
        response = httpx2.post(
            url,
            json=body,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30.0,
        )
        status = response.status_code
        raw = response.text[:2048]
    except httpx2.HTTPError as exc:
        return {
            "status": "transport_error",
            "error_type": type(exc).__name__,
            "elapsed_ms": round((time.perf_counter() - started) * 1000, 1),
        }
    # Error bodies can echo request values; store only the status and a bounded
    # error code/message after removing any occurrence of the secret/state.
    redacted = raw.replace(api_key, "[REDACTED]").replace(STATE, "[REDACTED]")
    try:
        parsed = json.loads(redacted)
        if not isinstance(parsed, dict):
            parsed = {"body_type": type(parsed).__name__}
    except json.JSONDecodeError:
        parsed = {"body_excerpt": redacted[:300]}
    return {
        "status": status,
        "body": parsed if status >= 400 else {"omitted": True},
        "elapsed_ms": round((time.perf_counter() - started) * 1000, 1),
    }


def main() -> int:
    api_key = load_jev_key()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_dir = ROOT / "artifacts" / "validation" / "t02"
    output_dir.mkdir(parents=True, exist_ok=True)

    evidence: dict = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "sdk": {"distribution": "typesafe-sdk", "version": version("typesafe-sdk")},
        "requested_model": MODEL,
    }

    # Explicit api_key keeps the project-specific JEV_API_KEY independent of
    # the SDK's TYPESAFE_API_KEY default.
    with TypeSafeClient(
        api_key=api_key,
        model=MODEL,
        retry=RetryPolicy(max_retries=0, timeout=30.0),
    ) as client:
        start = time.perf_counter()
        models = client.models.list()
        evidence["models"] = models.model_dump(mode="json")
        evidence["models_elapsed_ms"] = round((time.perf_counter() - start) * 1000, 1)

        questions = {
            "ai_need": Choice(
                instructions="이 업무에서 AI가 필요한가? 요청에 근거해 가장 적절한 하나를 고르라.",
                criteria={
                    "필요": "규칙 기반 일반 기술만으로 해결하기 어려운 학습·추론이 핵심이다.",
                    "불필요": "일반적인 소프트웨어 기능과 결정적 로직만으로 충분하다.",
                    "혼합": "일부는 AI가 유용하고 일부는 일반 기술로 충분하다.",
                    "정보 부족": "요청 정보만으로 판단할 수 없다.",
                },
            ),
            "feasibility": Choice(
                instructions="현재 요청을 소프트웨어 개발로 구현할 수 있는가? 요청에 근거해 고르라.",
                criteria={
                    "가능": "요청만으로 현실적인 구현 경로가 명확하다.",
                    "조건부 가능": "데이터·권한·승인·범위 확인 등 전제가 충족되어야 한다.",
                    "현재 불가": "현재 기술 또는 알려진 조건에서 구현할 수 없다.",
                    "정보 부족": "요청 정보만으로 판단할 수 없다.",
                },
            ),
            "urgency": Choice(
                instructions="요청에 명시된 업무 영향과 기한으로 볼 때 긴급도는 무엇인가? 근거가 없으면 판단 보류.",
                criteria={
                    "긴급": "명시된 임박한 기한 또는 즉각적인 중대한 업무 영향이 있다.",
                    "일반": "긴급하다는 구체적 근거가 없다.",
                    "판단 보류": "긴급도를 판단할 정보가 부족하다.",
                },
            ),
            "lead_org": Choice(
                instructions="요청된 결과의 주관 조직은 어디인가? 가장 적합한 하나를 고르라.",
                criteria={
                    "AI팀": "AI 모델·AI 판단 기능을 주로 설계하거나 구현한다.",
                    "IT팀": "일반 시스템·데이터 처리·화면·연동을 주로 구현한다.",
                    "현업": "업무 정의·분석 기준·최종 결과 확인을 주도한다.",
                    "판단 보류": "요청 정보만으로 주관 조직을 정할 수 없다.",
                },
            ),
            "review_signal": Score(
                instructions="요청이 사람의 검토를 받아야 할 정도를 평가하라. 조직 검토 여부 질문이 아니라 정보 부족과 책임 확인 필요를 평가.",
                criteria=[
                    "낮음: 범위와 책임이 명확하고 추가 검토 근거가 없다.",
                    "보통: 기준이나 결과 확인에 담당자 검토가 유용하다.",
                    "높음: 핵심 정보·권한·업무 책임이 불명확하여 검토가 필요하다.",
                ],
            ),
            "ai_team_involvement": Noul(
                instructions="요청의 성공적 수행에 AI팀의 참여가 필요하다는 말이 사실인가?",
            ),
            "it_team_involvement": Noul(
                instructions="요청의 성공적 수행에 IT팀의 참여가 필요하다는 말이 사실인가?",
            ),
            "business_involvement": Noul(
                instructions="요청의 성공적 수행에 현업의 참여가 필요하다는 말이 사실인가?",
            ),
        }
        start = time.perf_counter()
        response = client.system_one(state=STATE, questions=questions)
        evidence["judgment_elapsed_ms"] = round((time.perf_counter() - start) * 1000, 1)
        evidence["response"] = response.model_dump(mode="json")

    # Verify without rewriting the SDK response: its model/answers/usage and
    # each raw typed field remain available for the contract evidence.
    answers = evidence["response"].get("answers", {})
    expected_ids = set(questions)
    evidence["schema_check"] = {
        "model_present": bool(evidence["response"].get("model")),
        "usage_present": isinstance(evidence["response"].get("usage"), dict),
        "all_question_ids_present": expected_ids.issubset(answers),
        "answer_count": len(answers),
    }

    # Verify error paths with direct HTTP so invalid credentials/schema reach
    # the service boundary. Never store request headers or the real key.
    evidence["error_probes"] = {
        "invalid_key_401": error_probe(
            ENDPOINT,
            "jev_t02_intentionally_invalid_key",
            {"state": STATE, "model": MODEL, "questions": {"x": {"type": "noul", "instructions": "Is this a test?"}}},
            "invalid_key_401",
        ),
        "invalid_schema_422": error_probe(
            ENDPOINT,
            api_key,
            {"state": STATE, "model": MODEL, "questions": {"x": {"type": "choice", "instructions": "Choose", "criteria": []}}},
            "invalid_schema_422",
        ),
    }
    evidence["not_exercised"] = [
        "429 rate limit: do not intentionally consume account rate limit; verify with controlled low quota or service response",
        "529 overload: provider-side transient; record naturally observed response",
        "timeout: controlled network fault or short client deadline; distinguish connect/read timeout",
    ]

    output_path = output_dir / f"response-{stamp}.json"
    output_path.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"evidence={output_path.relative_to(ROOT)}")
    print(f"typesafe_sdk={evidence['sdk']['version']}")
    print(f"model={evidence['response'].get('model', 'MISSING')}")
    print(f"usage={json.dumps(evidence['response'].get('usage', {}))}")
    print(f"judgment_elapsed_ms={evidence['judgment_elapsed_ms']}")
    print(f"schema_check={json.dumps(evidence['schema_check'])}")
    print("error_statuses=" + json.dumps({k: v.get("status") for k, v in evidence["error_probes"].items()}))
    return 0 if all(evidence["schema_check"].values()) else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # redact messages that could include provider config
        print(f"probe_failed={type(exc).__name__}: Jev probe did not complete", file=sys.stderr)
        raise SystemExit(1)
