"""call_llm: schema validation, one retry on invalid JSON, 429 backoff, provider fallback."""
import json
import urllib.error

import pytest

from ai import llm
from ai.schemas import JDExtraction

GOOD = json.dumps({"title": "T", "criteria": [{"name": "Java", "is_must_have": True}]})


@pytest.fixture
def gemini(settings):
    settings.LLM_PROVIDER, settings.GEMINI_API_KEY, settings.GROQ_API_KEY = "gemini", "k", ""


def _http(code):
    return urllib.error.HTTPError("http://x", code, "err", {}, None)


def test_valid_output_is_parsed_through_the_schema(gemini, monkeypatch):
    monkeypatch.setattr(llm, "_post", lambda provider, prompt: GOOD)
    result = llm.call_llm("p", JDExtraction)
    assert isinstance(result.data, JDExtraction) and result.model.startswith("gemini:")


def test_fenced_json_is_accepted(gemini, monkeypatch):
    monkeypatch.setattr(llm, "_post", lambda provider, prompt: f"```json\n{GOOD}\n```")
    assert llm.call_llm("p", JDExtraction).data.title == "T"


def test_invalid_json_retries_once_then_succeeds(gemini, monkeypatch):
    replies = iter(["not json at all", GOOD])
    calls = []
    monkeypatch.setattr(llm, "_post", lambda provider, prompt: (calls.append(prompt), next(replies))[1])
    assert llm.call_llm("p", JDExtraction).data.title == "T"
    assert len(calls) == 2 and "valid JSON" in calls[1]


def test_invalid_twice_raises(gemini, monkeypatch):
    calls = []
    monkeypatch.setattr(llm, "_post", lambda provider, prompt: (calls.append(1), '{"criteria": []}')[1])
    with pytest.raises(llm.LLMInvalidOutput):
        llm.call_llm("p", JDExtraction)
    assert len(calls) == 2  # exactly one retry


def test_429_backs_off_exponentially_then_succeeds(gemini, monkeypatch):
    sleeps, attempts = [], []

    def post(provider, prompt):
        attempts.append(1)
        if len(attempts) < 3:
            raise _http(429)
        return GOOD

    monkeypatch.setattr(llm, "_post", post)
    monkeypatch.setattr(llm.time, "sleep", sleeps.append)
    assert llm.call_llm("p", JDExtraction).data.title == "T"
    assert sleeps == [1.0, 2.0]


def test_persistent_429_raises_rate_limited(gemini, monkeypatch):
    monkeypatch.setattr(llm, "_post", lambda provider, prompt: (_ for _ in ()).throw(_http(429)))
    monkeypatch.setattr(llm.time, "sleep", lambda s: None)
    with pytest.raises(llm.LLMRateLimited):
        llm.call_llm("p", JDExtraction)


def test_falls_back_to_groq_when_gemini_fails(settings, monkeypatch):
    settings.LLM_PROVIDER, settings.GEMINI_API_KEY, settings.GROQ_API_KEY = "gemini", "k", "g"
    seen = []

    def post(provider, prompt):
        seen.append(provider)
        if provider == "gemini":
            raise _http(500)
        return GOOD

    monkeypatch.setattr(llm, "_post", post)
    result = llm.call_llm("p", JDExtraction)
    assert seen == ["gemini", "groq"] and result.model.startswith("groq:")


def test_no_provider_configured(settings):
    settings.LLM_PROVIDER, settings.GEMINI_API_KEY, settings.GROQ_API_KEY = "gemini", "", ""
    settings.FALLBACK_TO_OFFLINE = False
    with pytest.raises(llm.LLMUnavailable):
        llm.call_llm("p", JDExtraction)


def test_no_key_falls_back_to_labelled_offline_scorer(settings):
    settings.LLM_PROVIDER, settings.GEMINI_API_KEY, settings.GROQ_API_KEY = "gemini", "", ""
    result = llm.call_llm("p", JDExtraction, context={"jd_text": "Senior Java Developer. Spring Boot. 5-8 years."})
    assert result.model.startswith("offline")


def test_configured_key_that_fails_is_not_hidden_by_offline_fallback(settings, monkeypatch):
    """A real provider erroring must still surface as a failure (rule 9), not silently become offline scores."""
    settings.LLM_PROVIDER, settings.GEMINI_API_KEY, settings.GROQ_API_KEY = "gemini", "k", ""
    def boom(provider, prompt):
        raise llm.urllib.error.URLError("down")
    monkeypatch.setattr(llm, "_post", boom)
    with pytest.raises(llm.LLMError):
        llm.call_llm("p", JDExtraction)
