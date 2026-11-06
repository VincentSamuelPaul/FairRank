"""The single entry point for every LLM call: `call_llm(prompt, schema)`.

- Provider chosen by env (LLM_PROVIDER = gemini | groq | offline); the other hosted provider is
  the fallback when its key is set.
- Output is always parsed through a Pydantic schema. Invalid JSON gets ONE retry, then fails
  with LLMInvalidOutput (callers turn that into an honest "Scoring failed, retry").
- HTTP 429 backs off exponentially, then moves on to the fallback provider.
"""
import json
import logging
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import TypeVar

from django.conf import settings
from pydantic import BaseModel, ValidationError

from ai import offline

log = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)

TIMEOUT_SECONDS = 45
MAX_429_RETRIES = 3
BACKOFF_BASE_SECONDS = 1.0


class LLMError(Exception):
    """Base class: nothing usable came back."""


class LLMUnavailable(LLMError):
    """No provider is configured."""


class LLMRateLimited(LLMError):
    """Still rate-limited after backoff; the job queue may retry later."""


class LLMInvalidOutput(LLMError):
    """Output failed schema validation twice."""


@dataclass
class LLMResult:
    data: BaseModel
    model: str


def call_llm(prompt: str, schema: type[T], *, context: dict | None = None) -> LLMResult:
    """Run `prompt`, return an instance of `schema` plus the model name used.

    `context` carries the structured inputs the offline provider needs (it cannot parse prompts).
    """
    providers = _provider_chain()
    if not providers:
        raise LLMUnavailable("No LLM provider is configured (set LLM_PROVIDER and an API key).")
    last: Exception = LLMUnavailable("no provider tried")
    for provider in providers:
        try:
            return _run_provider(provider, prompt, schema, context or {})
        except LLMError as exc:
            log.warning("LLM provider %s failed: %s", provider, exc)
            last = exc
    raise last


def _provider_chain() -> list[str]:
    primary = (settings.LLM_PROVIDER or "").lower()
    if primary == "offline":
        return ["offline"]
    keys = {"gemini": settings.GEMINI_API_KEY, "groq": settings.GROQ_API_KEY}
    order = [primary] + [p for p in ("gemini", "groq") if p != primary]
    return [p for p in order if keys.get(p)]


def _run_provider(provider: str, prompt: str, schema: type[T], context: dict) -> LLMResult:
    if provider == "offline":
        return LLMResult(data=_offline(schema, context), model=offline.MODEL_NAME)
    model = settings.GEMINI_MODEL if provider == "gemini" else settings.GROQ_MODEL
    attempt_prompt = prompt
    for attempt in (1, 2):  # one retry on invalid output
        raw = _complete(provider, attempt_prompt)
        try:
            return LLMResult(data=schema.model_validate(_extract_json(raw)), model=f"{provider}:{model}")
        except (ValueError, ValidationError) as exc:
            log.warning("Invalid %s output (attempt %s): %s", provider, attempt, str(exc)[:200])
            attempt_prompt = prompt + "\n\nYour previous reply was not valid JSON for the schema. Reply with valid JSON only."
    raise LLMInvalidOutput(f"{provider} returned invalid JSON twice")


def _offline(schema: type[T], context: dict) -> BaseModel:
    from ai.schemas import CVScoring, JDExtraction

    if schema is JDExtraction:
        return offline.extract_jd(context["jd_text"])
    if schema is CVScoring:
        return offline.score_cv(context["cv_text"], context["criteria"])
    raise LLMUnavailable(f"Offline provider cannot produce {schema.__name__}")


def _extract_json(raw: str) -> object:
    text = raw.strip()
    fenced = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.S)
    return json.loads(fenced.group(1) if fenced else text)


def _complete(provider: str, prompt: str) -> str:
    """One completion with exponential backoff on 429."""
    for retry in range(MAX_429_RETRIES + 1):
        try:
            return _post(provider, prompt)
        except urllib.error.HTTPError as exc:
            if exc.code == 429:
                if retry == MAX_429_RETRIES:
                    raise LLMRateLimited(f"{provider} rate limit persisted") from exc
                time.sleep(BACKOFF_BASE_SECONDS * (2**retry))
                continue
            raise LLMError(f"{provider} HTTP {exc.code}") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise LLMError(f"{provider} unreachable: {exc}") from exc
    raise LLMRateLimited(provider)  # pragma: no cover


def _post(provider: str, prompt: str) -> str:
    """The only network call. Tests replace this function."""
    if provider == "gemini":
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.GEMINI_MODEL}:generateContent"
        headers = {"Content-Type": "application/json", "x-goog-api-key": settings.GEMINI_API_KEY}
        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseMimeType": "application/json", "temperature": 0.1},
        }
    else:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {settings.GROQ_API_KEY}"}
        body = {
            "model": settings.GROQ_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
        }
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:  # noqa: S310 (fixed https hosts)
        payload = json.loads(resp.read())
    try:
        if provider == "gemini":
            return payload["candidates"][0]["content"]["parts"][0]["text"]
        return payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMError(f"{provider} returned an unexpected response shape") from exc
