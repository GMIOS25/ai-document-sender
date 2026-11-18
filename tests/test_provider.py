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
            "width": 595, "height": 842, "images": [{"bbox": [0, 0, 10, 10]}], "recipient_bbox": [0, 10, 300, 800],
            "ocr_text": "Nơi nhận:\n- Sở Y tế;", "ocr_lines": [{"text": "Sở Y tế", "confidence": 0.99}],
            "local_ocr_complete": True}
    asyncio.run(provider(handler).extract_mentions([page], {}))
    content = calls[0]["messages"][1]["content"]
    sent = json.loads(content[0]["text"])["pages"][0]
    assert sent["text"] == page["text"]
    assert "recipient_text" not in sent
    assert not {"ocr_text", "ocr_lines", "local_ocr_complete", "width", "height", "images", "recipient_bbox"}.intersection(sent)
    assert len(content) == 1 and calls[0]["model"] == "configured/text:free"
    assert page["ocr_lines"][0]["confidence"] == 0.99

    calls.clear()
    asyncio.run(provider(handler, provider_compact_input=False).extract_mentions([page], {}))
    legacy_sent = json.loads(calls[0]["messages"][1]["content"][0]["text"])["pages"][0]
    assert legacy_sent["recipient_text"] == page["recipient_text"]
    assert not {"ocr_text", "ocr_lines", "local_ocr_complete"}.intersection(legacy_sent)


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


def test_usage_and_error_audit_recorded_across_repairs():
    calls = []

    def handler(request):
        calls.append(json.loads(request.content))
        if len(calls) == 1:
            return httpx.Response(200, json={
                "choices": [{"message": {"content": "not-json", "reasoning": "thinking..."}, "finish_reason": "stop"}],
                "usage": {
                    "prompt_tokens": 300,
                    "completion_tokens": 50,
                    "total_tokens": 350,
                    "completion_tokens_details": {"reasoning_tokens": 40},
                    "prompt_tokens_details": {"cached_tokens": 200},
                    "cost": 0.001,
                },
            })
        return httpx.Response(200, json={
            "choices": [{"message": {"content": json.dumps(valid())}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 360, "completion_tokens": 25, "total_tokens": 385},
        })

    p = provider(handler)
    asyncio.run(p.extract_mentions([{"page": 1, "text": "Nơi nhận: VT"}], {}))
    assert p.last_audit["repair_count"] == 1
    assert p.last_audit["usage"] == {
        "prompt_tokens": 660,
        "completion_tokens": 75,
        "total_tokens": 735,
        "reasoning_tokens": 40,
        "cached_tokens": 200,
        "cost": 0.001,
    }
    assert p.last_audit["reasoning_chars"] == len("thinking...")
    assert p.last_audit["input_chars"] > 0

    failing = provider(lambda req: httpx.Response(404, json={"error": {"message": "Not found"}}))
    with pytest.raises(ProviderError):
        asyncio.run(failing.extract_mentions([{"page": 1, "text": "Nơi nhận: VT"}], {}))
    assert failing.last_audit["error_code"] == "provider_http_error"
    assert failing.last_audit["request_attempts"] == 1


def test_reasoning_control_and_mandatory_reasoning_fallback():
    calls = []

    def handler(request):
        body = json.loads(request.content)
        calls.append(body)
        if "reasoning" in body:
            return httpx.Response(400, json={"error": {"message": "Reasoning is mandatory for this endpoint and cannot be disabled."}})
        return response(json.dumps(valid()))

    p = provider(handler, provider_reasoning="off", provider_max_tokens=1500)
    asyncio.run(p.extract_mentions([{"page": 1, "text": "Nơi nhận:\n- Sở Y tế;"}], {}))
    assert calls[0]["reasoning"] == {"enabled": False}
    assert calls[0]["max_tokens"] == 1500
    assert "reasoning" not in calls[1]
    assert calls[1]["response_format"]["type"] == "json_schema"
    assert p.last_audit["reasoning_mode"] == "unsupported_fallback"

    calls.clear()
    asyncio.run(p.extract_mentions([{"page": 1, "text": "Nơi nhận:\n- Sở Y tế;"}], {}))
    assert len(calls) == 1 and "reasoning" not in calls[0]

    effort_calls = []
    p_low = provider(lambda req: (effort_calls.append(json.loads(req.content)), response(json.dumps(valid())))[1], provider_reasoning="low")
    asyncio.run(p_low.extract_mentions([{"page": 1, "text": "Nơi nhận:\n- Sở Y tế;"}], {}))
    assert effort_calls[0]["reasoning"] == {"effort": "low"}

    auto_calls = []
    p_auto = provider(lambda req: (auto_calls.append(json.loads(req.content)), response(json.dumps(valid())))[1], provider_reasoning="auto")
    asyncio.run(p_auto.extract_mentions([{"page": 1, "text": "Nơi nhận:\n- Sở Y tế;"}], {}))
    assert "reasoning" not in auto_calls[0]


def test_prompt_schema_mode_skips_probe_and_drops_unused_fields():
    calls = []

    def handler(request):
        calls.append(json.loads(request.content))
        return response(json.dumps(valid()))

    p = provider(handler, provider_schema_mode="prompt")
    asyncio.run(p.extract_mentions([{"page": 1, "text": "Nơi nhận:\n- Sở Y tế;"}], {}))
    assert len(calls) == 1
    assert "response_format" not in calls[0]
    sys_prompt = calls[0]["messages"][0]["content"]
    assert "review_reasons" in sys_prompt
    assert '"bbox"' not in sys_prompt and '"span"' not in sys_prompt
    assert p.last_audit["schema_mode"] == "prompt"

    # Strict response_format mode must not silently downgrade on 404.
    strict_p = provider(lambda req: httpx.Response(404, json={"error": {"message": "No endpoints found that support the requested parameters."}}),
                        provider_schema_mode="response_format", provider_reasoning="auto")
    with pytest.raises(ProviderError) as error:
        asyncio.run(strict_p.extract_mentions([{"page": 1, "text": "Nơi nhận:"}], {}))
    assert error.value.code == "provider_http_error"

    # Strict schema on normal mode also omits bbox/span/department_context.
    rf_calls = []
    p_rf = provider(lambda req: (rf_calls.append(json.loads(req.content)), response(json.dumps(valid())))[1])
    asyncio.run(p_rf.extract_mentions([{"page": 1, "text": "Nơi nhận:"}], {}))
    defs = rf_calls[0]["response_format"]["json_schema"]["schema"]["$defs"]
    assert not {"bbox", "span"}.intersection(defs["GeneratedEvidence"]["properties"])
    assert "department_context" not in defs["GeneratedMention"]["properties"]


def test_choose_candidate_caps_tokens_and_compacts_payload():
    calls = []

    def handler(request):
        calls.append(json.loads(request.content))
        return response('{"recipient_id":"internal_1"}')

    p = provider(handler, provider_max_tokens=2048)
    chosen = asyncio.run(p.choose_candidate(
        {"raw": "Sở Văn hóa"},
        [{"recipient_id": "internal_1", "name": "Sở Văn hóa", "evidence": [], "mention_ids": [], "match_method": ""}],
        {"document_id": "1", "attachment_content_uid": "secret-uid", "subject": None},
    ))
    assert chosen == "internal_1"
    assert calls[0]["max_tokens"] == 256
    sent = json.loads(calls[0]["messages"][1]["content"])
    assert "evidence" not in sent["candidates"][0]
    assert "attachment_content_uid" not in sent["context"]
    assert "subject" not in sent["context"]


def test_compact_pages_trims_middle_body_and_preserves_sections_and_articles():
    from ai_document_sender.provider import compact_pages_for_llm

    # 1. Standard multi-page doc: keep Kính gửi + body task head (Như trên) + clean Nơi nhận, drop middle prose & signature bleed.
    standard = [
        {"page": 1, "width": 595, "height": 842, "images": [],
         "text": "UBND TỈNH GIA LAI\nKính gửi:\n- Sở Xây dựng;\n- Sở Văn hóa, Thể thao\nvà Du lịch.\nThực hiện Kế hoạch số 01.\n1. Sở Tài chính: Báo cáo."},
        {"page": 2, "width": 595, "height": 842, "text": "Nội dung diễn giải dài dòng trang 2.\n" * 20},
        {"page": 3, "width": 595, "height": 842,
         "text": "Tiếp theo trang 3.\nNơi nhận: KT. CHỦ TỊCH\n- Như trên; PHÓ CHỦ TỊCH\n- Lưu: VT, X5. Nguyễn Văn Ký",
         "recipient_text": "Nơi nhận:\n- Như trên;\n- Lưu: VT, X5."},
    ]
    comp = compact_pages_for_llm(standard)
    assert [p["page"] for p in comp] == [1, 3]
    assert "Sở Xây dựng" in comp[0]["text"] and "và Du lịch" in comp[0]["text"]
    assert "1. Sở Tài chính:" in comp[0]["text"]
    assert "Thực hiện Kế hoạch" not in comp[0]["text"]
    assert "Nguyễn Văn Ký" not in comp[1]["text"]
    assert "- Lưu: VT, X5." in comp[1]["text"]

    # 2. Article reference doc: keep Điều and Danh sách across pages while stripping Căn cứ recitals.
    article_doc = [
        {"page": 1, "text": "QUYẾT ĐỊNH\nCăn cứ Luật số 1;\nCăn cứ Nghị định số 2;\n" + ("Căn cứ khác;\n" * 40) + "Điều 1. Thành lập đoàn.\nĐiều 3. Sở Nội vụ chịu trách nhiệm."},
        {"page": 2, "text": "DANH SÁCH\n1. Ông Nguyễn Văn An.\nNơi nhận:\n- Như Điều 3;\n- Lưu: VT."},
    ]
    comp_art = compact_pages_for_llm(article_doc)
    assert [p["page"] for p in comp_art] == [1, 2]
    assert "Căn cứ Luật số 1" not in comp_art[0]["text"]
    assert "Điều 3. Sở Nội vụ chịu trách nhiệm." in comp_art[0]["text"]
    assert "Ông Nguyễn Văn An" in comp_art[1]["text"]

    # 3. Missing Nơi nhận header (e.g. OCR typo): preserve text fallback so LLM can still rescue.
    typo_doc = [{"page": 1, "text": "Noi nhan:\n- Sở Y tế;\n- Lưu: VT."}]
    comp_typo = compact_pages_for_llm(typo_doc)
    assert comp_typo == [{"page": 1, "text": "Noi nhan:\n- Sở Y tế;\n- Lưu: VT."}]
