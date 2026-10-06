"""google-genai 2.28: aio generate_content with a Pydantic response_schema."""
import json
import time

import httpx
from pydantic import ValidationError

from ildongi.assist.prompts import validate_output, wrap_data
from ildongi.assist.providers import (
    LlmConnectionError,
    LlmInvalidOutput,
    LlmRefused,
    LlmResult,
    LlmTimeout,
    ModelInfo,
    status_error,
)


class Provider:
    name = 'google'

    def __init__(self, api_key, *, client=None, max_retries=1):
        from google import genai
        from google.genai import errors, types
        self.sdk, self.errors, self.types = genai, errors, types
        self.key, self.client, self.max_retries = api_key, client, max_retries

    def _client(self, timeout, retries):
        return self.client or self.sdk.Client(api_key=self.key, http_options=self.types.HttpOptions(
            timeout=round(timeout*1000), retry_options=self.types.HttpRetryOptions(attempts=retries+1)))

    async def generate(self, request, *, model, timeout):
        client = self._client(timeout, self.max_retries)
        started = time.monotonic()
        try:
            response = await client.aio.models.generate_content(
                model=model, contents=wrap_data(request.data), config=self.types.GenerateContentConfig(
                    system_instruction=request.system, response_mime_type='application/json',
                    # response_schema rejects additionalProperties from extra="forbid" models (400).
                    response_json_schema=request.output_type.model_json_schema(),
                    max_output_tokens=request.max_output_tokens))
            feedback = response.prompt_feedback
            if feedback and feedback.block_reason and str(feedback.block_reason) not in ('BLOCK_REASON_UNSPECIFIED', 'BlockReason.BLOCK_REASON_UNSPECIFIED'):
                raise LlmRefused()
            reasons = {str(c.finish_reason).split('.')[-1] for c in response.candidates or []}
            if reasons & {'SAFETY', 'BLOCKLIST', 'PROHIBITED_CONTENT', 'SPII', 'RECITATION', 'IMAGE_SAFETY'}:
                raise LlmRefused()
            if not response.candidates or 'MAX_TOKENS' in reasons or not response.text:
                raise LlmInvalidOutput()
            parsed = validate_output(request.output_type, json.loads(response.text))
            usage = response.usage_metadata
            return LlmResult(parsed, self.name, response.model_version or model,
                             usage.prompt_token_count or 0,
                             (usage.candidates_token_count or 0) + (usage.thoughts_token_count or 0),
                             round((time.monotonic()-started)*1000))
        except self.errors.APIError as exc:
            raise status_error(exc.code) from None
        except (httpx.TimeoutException, TimeoutError):
            raise LlmTimeout() from None
        except httpx.TransportError:
            raise LlmConnectionError() from None
        except (ValidationError, ValueError):
            raise LlmInvalidOutput() from None
        finally:
            if self.client is None:
                await client.aio.aclose()
                client.close()

    async def list_models(self, *, timeout):
        client = self._client(timeout, 0)
        try:
            pager = await client.aio.models.list()
            return [ModelInfo(id=m.name.removeprefix('models/'), label=m.display_name or m.name)
                    async for m in pager if 'generateContent' in (m.supported_actions or [])]
        except self.errors.APIError as exc:
            raise status_error(exc.code) from None
        except (httpx.TimeoutException, TimeoutError):
            raise LlmTimeout() from None
        except httpx.TransportError:
            raise LlmConnectionError() from None
        finally:
            if self.client is None:
                await client.aio.aclose()
                client.close()
