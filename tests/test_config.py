import os
from dataclasses import replace
import pytest
from ai_document_sender.config import Settings


def test_env_process_precedence_and_no_interpolation(tmp_path,monkeypatch):
    path=tmp_path/"local.env"
    path.write_text('SENDER_PORT=8100 # inline comment\nexport SENDER_PROVIDER_MODE=offline\nOPENROUTER_API_KEY="literal$HOME" # not part of key\n',encoding="utf-8")
    monkeypatch.setenv("SENDER_PORT","8200")
    monkeypatch.delenv("OPENROUTER_API_KEY",raising=False)
    settings=Settings.from_env(path)
    assert settings.port == 8200
    assert settings.openrouter_api_key == "literal$HOME"
    assert "literal" not in repr(settings)


def test_nonloopback_auth_required(settings):
    with pytest.raises(ValueError): replace(settings,host="0.0.0.0").validate()
    assert replace(settings,host="0.0.0.0",api_key="x").validate()


def test_local_ocr_env_and_validation(tmp_path, monkeypatch):
    path = tmp_path / "ocr.env"
    path.write_text("SENDER_OCR_BACKEND=vietocr\nSENDER_OCR_DEVICE=auto\n"
                    "SENDER_OCR_BATCH_SIZE=16\nSENDER_OCR_WEIGHTS=var/models/vgg_seq2seq.pth\n",
                    encoding="utf-8")
    for key in ("SENDER_OCR_BACKEND", "SENDER_OCR_DEVICE", "SENDER_OCR_BATCH_SIZE", "SENDER_OCR_WEIGHTS"):
        monkeypatch.delenv(key, raising=False)
    configured = Settings.from_env(path)
    assert configured.ocr_backend == "vietocr"
    assert configured.ocr_device == "auto"
    assert configured.ocr_batch_size == 16
    assert configured.ocr_weights.is_absolute()
    with pytest.raises(ValueError):
        replace(configured, ocr_backend="unknown").validate()
    with pytest.raises(ValueError):
        replace(configured, ocr_batch_size=0).validate()


def test_provider_optimization_env_and_validation(tmp_path, monkeypatch):
    path = tmp_path / "provider.env"
    path.write_text(
        "SENDER_PROVIDER_SCHEMA_MODE=PROMPT\n"
        "SENDER_PROVIDER_REASONING=low\n"
        "SENDER_PROVIDER_MAX_TOKENS=1024\n"
        "SENDER_PROVIDER_COMPACT_INPUT=false\n",
        encoding="utf-8",
    )
    for key in (
        "SENDER_PROVIDER_SCHEMA_MODE",
        "SENDER_PROVIDER_REASONING",
        "SENDER_PROVIDER_MAX_TOKENS",
        "SENDER_PROVIDER_COMPACT_INPUT",
    ):
        monkeypatch.delenv(key, raising=False)
    configured = Settings.from_env(path)
    assert configured.provider_schema_mode == "prompt"
    assert configured.provider_reasoning == "low"
    assert configured.provider_max_tokens == 1024
    assert configured.provider_compact_input is False
    with pytest.raises(ValueError):
        replace(configured, provider_schema_mode="invalid").validate()
    with pytest.raises(ValueError):
        replace(configured, provider_reasoning="turbo").validate()
    with pytest.raises(ValueError):
        replace(configured, provider_max_tokens=64).validate()
    path.write_text("SENDER_PROVIDER_COMPACT_INPUT=maybe\n", encoding="utf-8")
    with pytest.raises(ValueError):
        Settings.from_env(path)


def test_groq_env_auto_routing_and_qwen_model_normalization(tmp_path, monkeypatch):
    for key in (
        "OPENROUTER_API_KEY",
        "OPENROUTER_TEXT_MODEL",
        "OPENROUTER_VISION_MODEL",
        "OPENROUTER_URL",
        "GROQ_API_KEY",
        "GROQ_TEXT_MODEL",
        "GROQ_VISION_MODEL",
        "GROQ_URL",
    ):
        monkeypatch.delenv(key, raising=False)
    path = tmp_path / "groq.env"
    path.write_text(
        "OPENROUTER_API_KEY=gsk_test_groq_key_123\n"
        "OPENROUTER_TEXT_MODEL=Qwen 3.8 27B\n",
        encoding="utf-8",
    )
    configured = Settings.from_env(path)
    assert configured.openrouter_url == "https://api.groq.com/openai/v1"
    assert configured.openrouter_text_model == "qwen/qwen3.8-27b"


def test_groq_prompt_mode_and_three_vision_pages_from_env(tmp_path, monkeypatch):
    for key in (
        "SENDER_PROVIDER_MODE",
        "OPENROUTER_API_KEY",
        "OPENROUTER_TEXT_MODEL",
        "OPENROUTER_VISION_MODEL",
        "OPENROUTER_URL",
        "SENDER_PROVIDER_SCHEMA_MODE",
        "SENDER_PROVIDER_REASONING",
        "SENDER_MAX_VISION_PAGES",
    ):
        monkeypatch.delenv(key, raising=False)
    path = tmp_path / "groq_qwen.env"
    path.write_text(
        "SENDER_PROVIDER_MODE=cloud\n"
        "OPENROUTER_API_KEY=gsk_test_groq_key_123\n"
        "OPENROUTER_TEXT_MODEL=qwen/qwen3.8-27b\n"
        "OPENROUTER_VISION_MODEL=qwen/qwen3.8-27b\n"
        "OPENROUTER_URL=https://api.groq.com/openai/v1\n"
        "SENDER_PROVIDER_SCHEMA_MODE=prompt\n"
        "SENDER_MAX_VISION_PAGES=3\n",
        encoding="utf-8",
    )
    configured = Settings.from_env(path)
    assert configured.provider_mode == "cloud"
    assert configured.openrouter_url == "https://api.groq.com/openai/v1"
    assert configured.openrouter_text_model == "qwen/qwen3.8-27b"
    assert configured.openrouter_vision_model == "qwen/qwen3.8-27b"
    assert configured.provider_schema_mode == "prompt"
    assert configured.provider_reasoning == "off"
    assert configured.max_vision_pages == 3


def test_custom_ollama_endpoint_does_not_rewrite_model_or_route_to_groq(tmp_path, monkeypatch):
    for key in (
        "SENDER_PROVIDER_MODE",
        "OPENROUTER_API_KEY",
        "OPENROUTER_TEXT_MODEL",
        "OPENROUTER_VISION_MODEL",
        "OPENROUTER_URL",
        "GROQ_API_KEY",
        "GROQ_URL",
    ):
        monkeypatch.delenv(key, raising=False)
    path = tmp_path / "ollama.env"
    path.write_text(
        "SENDER_PROVIDER_MODE=cloud\n"
        "OPENROUTER_API_KEY=gsk_leftover_key\n"
        "OPENROUTER_TEXT_MODEL=qwen3.8:27b\n"
        "OPENROUTER_VISION_MODEL=qwen3.8:27b\n"
        "OPENROUTER_URL=http://127.0.0.1:11434/v1\n",
        encoding="utf-8",
    )
    configured = Settings.from_env(path)
    assert configured.openrouter_url == "http://127.0.0.1:11434/v1"
    assert configured.openrouter_text_model == "qwen3.8:27b"
    assert configured.openrouter_vision_model == "qwen3.8:27b"
