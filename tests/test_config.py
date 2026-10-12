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
