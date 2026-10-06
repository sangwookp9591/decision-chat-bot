"""OpenAI 3.24 Responses structured parse (official installed SDK source)."""
import re
import time

from pydantic import ValidationError

from ildongi.assist.prompts import validate_output, wrap_data
from ildongi.assist.providers import (
    LlmAuthError,
    LlmConnectionError,
    LlmInvalidOutput,
    LlmRateLimited,
    LlmRefused,
    LlmResult,
    LlmTimeout,
    ModelInfo,
    status_error,
)


class Provider:
    name = 'openai'

    def __init__(self, api_key, *, client=None, max_retries=1):
        import openai
        self.sdk = openai
        self.key, self.client, self.max_retries = api_key, client, max_retries

    async def generate(self, request, *, model, timeout):
        sdk = self.sdk
        client = self.client or sdk.AsyncOpenAI(api_key=self.key, max_retries=self.max_retries)
        started = time.monotonic()
        try:
            response = await client.responses.parse(
                model=model, instructions=request.system, input=wrap_data(request.data),
                text_format=request.output_type, max_output_tokens=request.max_output_tokens,
                timeout=timeout, store=False,
            )
            if any(getattr(part, 'type', '') == 'refusal' for item in response.output
                   for part in getattr(item, 'content', [])):
                raise LlmRefused()
            if response.status != 'completed' or response.output_parsed is None:
                raise LlmInvalidOutput()
            parsed = validate_output(request.output_type, response.output_parsed)
            return LlmResult(parsed, self.name, response.model, response.usage.input_tokens,
                             response.usage.output_tokens, round((time.monotonic()-started)*1000))
        except sdk.AuthenticationError:
            raise LlmAuthError() from None
        except sdk.RateLimitError:
            raise LlmRateLimited() from None
        except sdk.APIStatusError as exc:
            raise status_error(exc.status_code) from None
        except sdk.APITimeoutError:
            raise LlmTimeout() from None
        except sdk.APIConnectionError:
            raise LlmConnectionError() from None
        except (ValidationError, ValueError):
            raise LlmInvalidOutput() from None
        finally:
            if self.client is None:
                await client.close()

    async def list_models(self, *, timeout):
        sdk = self.sdk
        client = self.client or sdk.AsyncOpenAI(api_key=self.key, max_retries=0, timeout=timeout)
        try:
            # Text model families from https://developers.openai.com/api/docs/models;
            # models.list has no capability field, so exclude specialized audio/image/search IDs.
            return [ModelInfo(id=m.id, label=m.id) async for m in client.models.list()
                    if re.match(r'^(gpt-|o[1-9])', m.id)
                    and not any(word in m.id for word in ('audio', 'realtime', 'transcribe', 'tts', 'image', 'search', 'codex'))]
        except sdk.AuthenticationError:
            raise LlmAuthError() from None
        except sdk.RateLimitError:
            raise LlmRateLimited() from None
        except sdk.APIStatusError as exc:
            raise status_error(exc.status_code) from None
        except sdk.APITimeoutError:
            raise LlmTimeout() from None
        except sdk.APIConnectionError:
            raise LlmConnectionError() from None
        finally:
            if self.client is None:
                await client.close()
