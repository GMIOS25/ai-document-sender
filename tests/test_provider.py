import asyncio
import json
import httpx
import pytest

from ai_document_sender.config import Settings
from ai_document_sender.provider import OpenRouterProvider, ProviderError


def provider(handler, sleep=None, **kwargs):
    settings = Settings(provider_mode="cloud", openrouter_api_key="test-secret", openrouter_text_model="configured/text:free", openrouter_vision_model="configured/vision:free", **kwargs)
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return OpenRouterProvider(settings, client=client, **({"sleep": sleep} if sleep else {}))


def response(content):
    return httpx.Response(200, json={"choices": [{"message": {"content": content}, "finish_reason": "stop"}]})


def valid():
    return {"mentions": [], "status": "partial", "review_reasons": ["recipient_sections_missing"], "ocr_pages": []}


def test_one_invalid_json_repair_and_no_model_fallback():
    calls = []
    def handler(request):
        calls.append(json.loads(request.content))
        return response("not-json" if len(calls) == 1 else json.dumps(valid()))
    p = provider(handler)
    result = asyncio.run(p.extract_mentions([{"page": 1, "text": "Nơi nhận: VT"}], {}))
    assert result["status"] == "partial"
    assert len(calls) == 2
    assert all(c["model"] == "configured/text:free" for c in calls)
    assert all("models" not in c for c in calls)
    assert all(c.get("plugins") == [{"id": "context-compression", "enabled": False}] for c in calls)
    assert calls[1]["response_format"]["type"] == "json_schema"


def test_schema_error_gets_one_repair_then_safe_failure():
    calls = []
    def handler(request):
        calls.append(request)
        return response('{"mentions":"wrong"}')
    p = provider(handler)
    with pytest.raises(ProviderError) as error:
        asyncio.run(p.extract_mentions([{"page": 1, "text": "Nơi nhận:"}], {}))
    assert error.value.code == "invalid_model_output"
    assert len(calls) == 2
    assert "test-secret" not in str(error.value)


def test_routing_parameter_rejection_uses_same_model_and_validates_fenced_json():
    calls = []

    def handler(request):
        body = json.loads(request.content)
        calls.append(body)
        if "response_format" in body:
            return httpx.Response(404, json={"error": {"message": "No endpoints found that support the requested parameters."}})
        return response("```json\n" + json.dumps(valid()) + "\n```")

    assert asyncio.run(provider(handler).extract_mentions([{"page": 1, "text": "Nơi nhận:"}], {})) == valid()
    assert len(calls) == 2
    assert calls[0]["model"] == calls[1]["model"]
    assert "review_reasons" in calls[1]["messages"][0]["content"]


def test_unrelated_provider_404_is_not_retried_or_echoed():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(404, json={"error": {"message": "Private detail test-secret"}})

    with pytest.raises(ProviderError, match="HTTP 404") as error:
        asyncio.run(provider(handler).extract_mentions([{"page": 1, "text": "Nơi nhận:"}], {}))
    assert len(calls) == 1
    assert "test-secret" not in str(error.value)


def test_vision_uses_only_configured_vision_model_and_data_url():
    calls = []
    def handler(request):
        calls.append(json.loads(request.content))
        return response(json.dumps(valid()))
    p = provider(handler)
    asyncio.run(p.extract_mentions([{"page": 1, "text": ""}], {}, images=[{"page": 1, "data_url": "data:image/png;base64,AA=="}]))
    assert calls[0]["model"] == "configured/vision:free"
    assert any(c["type"] == "image_url" for c in calls[0]["messages"][1]["content"])


def test_local_ocr_sends_text_without_duplicate_transcription_or_line_audit():
    calls = []
    def handler(request):
        calls.append(json.loads(request.content))
        return response(json.dumps(valid()))
    page = {"page": 1, "text": "Nơi nhận:\n- Sở Y tế;", "recipient_text": "Nơi nhận:\n- Sở Y tế;",
            "ocr_text": "Nơi nhận:\n- Sở Y tế;", "ocr_lines": [{"text": "Sở Y tế", "confidence": 0.99}],
            "local_ocr_complete": True}
    asyncio.run(provider(handler).extract_mentions([page], {}))
    content = calls[0]["messages"][1]["content"]
    sent = json.loads(content[0]["text"])["pages"][0]
    assert sent["text"] == page["text"] and sent["recipient_text"] == page["recipient_text"]
    assert not {"ocr_text", "ocr_lines", "local_ocr_complete"}.intersection(sent)
    assert len(content) == 1 and calls[0]["model"] == "configured/text:free"
    assert page["ocr_lines"][0]["confidence"] == 0.99


def test_429_retry_after_is_honored_with_bounded_attempts():
    attempts, sleeps = [], []
    async def sleep(seconds):
        sleeps.append(seconds)
    def handler(request):
        attempts.append(request)
        return httpx.Response(429, headers={"Retry-After": "2"}) if len(attempts) == 1 else response(json.dumps(valid()))
    p = provider(handler, sleep=sleep)
    asyncio.run(p.extract_mentions([{"page": 1, "text": "Nơi nhận:"}], {}))
    assert len(attempts) == 2 and sleeps == [2]


def test_timeout_fails_safely_without_leaking_key():
    def handler(request):
        raise httpx.ReadTimeout("test-secret must not be echoed", request=request)
    async def sleep(seconds):
        pass
    p = provider(handler, sleep=sleep, provider_max_retries=1)
    with pytest.raises(ProviderError) as error:
        asyncio.run(p.extract_mentions([{"page": 1, "text": "Nơi nhận:"}], {}))
    assert error.value.code == "provider_timeout"
    assert "test-secret" not in str(error.value)


def test_candidate_allowlist_rejects_invented_id():
    p = provider(lambda request: response('{"recipient_id":"invented-id"}'))
    with pytest.raises(ProviderError) as error:
        asyncio.run(p.choose_candidate({"raw": "Đ/c Lịch"}, [{"recipient_id": "internal_1", "name": "Nguyễn Thị Thanh Lịch"}], {}))
    assert error.value.code == "invalid_model_output"


def test_offline_mode_cannot_send_even_when_key_present():
    p = OpenRouterProvider(Settings(openrouter_api_key="test-secret", openrouter_text_model="some/model"))
    assert not p.available
    with pytest.raises(ProviderError) as error:
        asyncio.run(p.extract_mentions([], {}))
    assert error.value.code == "provider_unavailable"
