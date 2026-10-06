"""Anthropic messages API adapter with validated structured output."""
import json
import time
from importlib import import_module

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
    name = 'anthropic'

    def __init__(self, api_key, *, client=None, max_retries=1):
        import anthropic
        self.sdk = anthropic
        self.key, self.client, self.max_retries = api_key, client, max_retries

    async def generate(self, request, *, model, timeout):
        sdk = self.sdk
        client = self.client or sdk.AsyncAnthropic(api_key=self.key, max_retries=self.max_retries)
        started = time.monotonic()
        try:
            # The SDK only exposes its API-compatible schema transform through this helper.
            transform_schema = import_module('anthropic.lib._parse._transform').transform_schema

            output_config = {'format': {'type': 'json_schema',
                                        'schema': transform_schema(request.output_type.model_json_schema())}}
            if model.startswith(('claude-opus-', 'claude-sonnet-5-', 'claude-fable-')):
                output_config['effort'] = 'low'
            response = await client.messages.create(
                model=model, max_tokens=request.max_output_tokens, system=request.system,
                messages=[{'role': 'user', 'content': wrap_data(request.data)}],
                output_config=output_config, timeout=timeout,
            )
            if response.stop_reason == 'refusal':
                raise LlmRefused()
            text = next((block.text for block in response.content if block.type == 'text'), None)
            if response.stop_reason == 'max_tokens' or text is None:
                raise LlmInvalidOutput()
            parsed = validate_output(request.output_type, json.loads(text))
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
        client = self.client or sdk.AsyncAnthropic(api_key=self.key, max_retries=0, timeout=timeout)
        try:
            return [ModelInfo(id=m.id, label=m.display_name) async for m in client.models.list()]
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
