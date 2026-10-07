"""Provider-neutral contracts and sanitized error codes."""
from dataclasses import dataclass
from importlib import import_module, util
from typing import Generic, Literal, Protocol, TypeVar

from pydantic import BaseModel

ProviderName = Literal["anthropic", "openai", "google", "chatgpt"]
Feature = Literal["summary", "task_description", "questions", "rule_explanation", "ping"]
T = TypeVar("T", bound=BaseModel)
KEY_FIELDS = {"anthropic": "anthropic_api_key", "openai": "openai_api_key", "google": "gemini_api_key"}
SDK_MODULES = {"anthropic": "anthropic", "openai": "openai", "google": "google.genai"}
# Official catalogs verified 2026-10-06: https://developers.openai.com/api/docs/models
# https://ai.google.dev/gemini-api/docs/models and LLM_ASSIST.md §6.1.
DEFAULT_MODELS = {
    "chatgpt": [],
    "anthropic": [("claude-opus-5-5", "Claude Opus 5.5"), ("claude-sonnet-5-5", "Claude Sonnet 5.5"), ("claude-haiku-4-5-20251001", "Claude Haiku 4.5")],
    "openai": [("gpt-6-astra", "GPT-6 Astra"), ("gpt-6.1-sol", "GPT-6.1 Sol"), ("gpt-6-luna", "GPT-6 Luna")],
    "google": [("gemini-3.8-flash", "Gemini 3.8 Flash"), ("gemini-3.7-flash", "Gemini 3.7 Flash"), ("gemini-3.5-flash-lite", "Gemini 3.5 Flash-Lite")],
}


@dataclass(frozen=True)
class LlmRequest(Generic[T]):
    feature: Feature
    system: str
    data: str
    output_type: type[T]
    max_output_tokens: int


@dataclass(frozen=True)
class LlmResult(Generic[T]):
    parsed: T
    provider: ProviderName
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: int


class ModelInfo(BaseModel):
    id: str
    label: str


class LlmProvider(Protocol):
    name: ProviderName

    async def generate(self, request: LlmRequest[T], *, model: str, timeout: float) -> LlmResult[T]: ...
    async def list_models(self, *, timeout: float) -> list[ModelInfo]: ...


class LlmError(Exception):
    code = "PROVIDER_ERROR"

    def __init__(self, code=None, *, status=None):
        self.code = code or type(self).code
        self.status = status
        super().__init__(self.code)


class LlmUnavailable(LlmError):
    code = "MODE_OFF"


class LlmAuthError(LlmError):
    code = "AUTH_FAILED"


class LlmRateLimited(LlmError):
    code = "RATE_LIMITED"


class LlmTimeout(LlmError):
    code = "TIMEOUT"


class LlmConnectionError(LlmError):
    code = "CONNECTION"


class LlmRefused(LlmError):
    code = "REFUSED"


class LlmInvalidOutput(LlmError):
    code = "INVALID_OUTPUT"


class LlmProviderError(LlmError):
    pass


def status_error(status):
    if status in (401, 403):
        return LlmAuthError()
    if status == 429:
        return LlmRateLimited()
    if status in (408, 504):
        return LlmTimeout()
    return LlmProviderError(status=status)


def sdk_available(name):
    try:
        return util.find_spec(SDK_MODULES[name]) is not None
    except (ImportError, ModuleNotFoundError):
        return False


def get_provider(name: ProviderName, settings, *, max_retries=1) -> LlmProvider:
    if settings.llm_mode == "off":
        raise LlmUnavailable("MODE_OFF")
    if name == "chatgpt":
        return import_module("ildongi.assist.adapters.chatgpt").Provider(settings)
    if settings.llm_mode == "fake":
        return import_module("ildongi.assist.fake").FakeProvider(name=name)
    key = getattr(settings, KEY_FIELDS[name]).get_secret_value()
    if not key:
        raise LlmUnavailable("KEY_MISSING")
    try:
        module = import_module("ildongi.assist.adapters." + {"google": "gemini"}.get(name, name))
        return module.Provider(key, max_retries=max_retries)
    except ImportError:
        raise LlmUnavailable("SDK_MISSING") from None
