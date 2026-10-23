import asyncio
import json
import re
from typing import Type, TypeVar, Optional, Any, Dict, List
from pydantic import BaseModel, ValidationError

# Initialize Windows native certificate store for SSL
try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

from google import genai
from google.genai import types
from google.genai.errors import APIError, ClientError, ServerError

from app.config import settings
from app.core.logging import logger
from app.core.errors import HackMateException

T = TypeVar("T", bound=BaseModel)


class GeminiQuotaError(HackMateException):
    def __init__(self, message: str = "Gemini API rate limit or quota exceeded."):
        super().__init__(message, status_code=429)


class GeminiServiceError(HackMateException):
    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message, status_code=status_code)


class GeminiOutputValidationError(HackMateException):
    def __init__(self, detail: str):
        super().__init__(f"Gemini output validation failed: {detail}", status_code=502)


class GeminiClient:
    def __init__(self):
        self._client: Optional[genai.Client] = None
        self._model_name = settings.GEMINI_MODEL or "gemini-3-flash-preview"

    def get_client(self) -> genai.Client:
        if not self._client:
            if not settings.GEMINI_API_KEY:
                raise GeminiServiceError(
                    "GEMINI_API_KEY is not configured. Please configure it in your backend environment.",
                    status_code=503
                )
            self._client = genai.Client(api_key=settings.GEMINI_API_KEY)
        return self._client

    async def generate_structured(
        self,
        prompt: str,
        system_instruction: str,
        schema: Type[T],
        temperature: float = 0.2,
        timeout_seconds: float = 60.0,
        max_retries: int = 3,
    ) -> T:
        """
        Sends a structured request to Gemini with retry logic, rate limit handling,
        and strict Pydantic schema validation.
        """
        client = self.get_client()

        # Build schema instructions to enforce valid JSON
        schema_json = json.dumps(schema.model_json_schema(), indent=2)
        full_system = (
            f"{system_instruction}\n\n"
            f"CRITICAL: You MUST respond ONLY with a single valid JSON object strictly matching this JSON schema:\n"
            f"{schema_json}\n"
            f"Do not include markdown code fences (like ```json ... ```), preamble, or postscript. Return pure JSON only."
        )

        config = types.GenerateContentConfig(
            system_instruction=full_system,
            temperature=temperature,
            response_mime_type="application/json",
        )

        # Model fallback candidates for high availability
        model_candidates = [self._model_name]
        for fallback in ["gemini-flash-latest", "gemini-3.5-flash", "gemini-3.1-flash-lite-preview"]:
            if fallback not in model_candidates:
                model_candidates.append(fallback)

        # Retry loop for rate limits and transient server errors
        last_error = None
        for attempt in range(1, max_retries + 1):
            curr_model = model_candidates[(attempt - 1) % len(model_candidates)]
            try:
                # Wrap synchronous SDK call in an async executor with timeout
                def _call():
                    return client.models.generate_content(
                        model=curr_model,
                        contents=prompt,
                        config=config,
                    )

                response = await asyncio.wait_for(
                    asyncio.to_thread(_call),
                    timeout=timeout_seconds,
                )

                raw_text = response.text or ""
                return self._parse_and_validate(raw_text, schema)

            except asyncio.TimeoutError:
                last_error = GeminiServiceError(f"Gemini API request timed out after {timeout_seconds}s.")
                logger.warning(f"Gemini call timed out (attempt {attempt}/{max_retries})")
            except ClientError as e:
                err_str = str(e)
                if "RESOURCE_EXHAUSTED" in err_str or "429" in err_str:
                    logger.warning(f"Gemini quota exhausted (attempt {attempt}/{max_retries}): {err_str[:120]}")
                    last_error = GeminiQuotaError(f"Gemini rate limit exceeded: {err_str[:120]}")
                    if attempt < max_retries:
                        backoff = 12 * attempt
                        logger.info(f"Rate limited by Gemini API. Backing off for {backoff}s before retry...")
                        await asyncio.sleep(backoff)
                        continue
                    raise last_error
                elif "503" in err_str or "UNAVAILABLE" in err_str:
                    logger.warning(f"Gemini temporarily unavailable (attempt {attempt}): {err_str[:100]}")
                    last_error = e
                else:
                    raise GeminiServiceError(f"Gemini client error: {err_str[:200]}")
            except ServerError as e:
                logger.warning(f"Gemini server error (attempt {attempt}): {str(e)[:100]}")
                last_error = e
            except GeminiOutputValidationError:
                raise
            except Exception as e:
                logger.error(f"Unexpected error calling Gemini: {str(e)}")
                last_error = e

            # Exponential backoff before retry
            if attempt < max_retries:
                backoff = 2 ** attempt
                logger.info(f"Retrying Gemini request in {backoff} seconds...")
                await asyncio.sleep(backoff)

        raise GeminiServiceError(
            f"Gemini request failed after {max_retries} attempts. Last error: {str(last_error)}"
        )

    def _parse_and_validate(self, raw_text: str, schema: Type[T]) -> T:
        """Cleans, parses, and validates the raw LLM response against Pydantic schema."""
        cleaned = raw_text.strip()

        # Remove markdown code blocks if the model wrapped output
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
            cleaned = cleaned.strip()

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from Gemini response: {raw_text[:300]}")
            raise GeminiOutputValidationError(f"Invalid JSON response: {str(e)}")

        try:
            return schema.model_validate(data)
        except ValidationError as e:
            logger.error(f"Gemini output failed schema validation: {e.json()}")
            raise GeminiOutputValidationError(f"Schema mismatch: {str(e)}")


gemini_client = GeminiClient()
