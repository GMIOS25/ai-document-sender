import asyncio
import tempfile
from pathlib import Path
from unittest.mock import patch

from ai_document_sender.config import Settings
from ai_document_sender.contracts import DocumentMetadata
from ai_document_sender.extraction import extract_document, select_vision_pages
from ai_document_sender.mentions import extract_rule_mentions


TEXT = '''ỦY BAN NHÂN DÂN TỈNH GIA LAI
Kính gửi:
- Sở Văn hóa, Thể thao và Du lịch;
- Hội Nhà báo tỉnh.

Đề nghị các đơn vị triển khai thực hiện.
Nơi nhận:
- Như trên;
- Chủ tịch UBND tỉnh;
- PCT N.T.T.Lịch và L.H. Giang;
- CVP, PVPQT;
- Lưu: VT, V1, V5, V8.
TL. CHỦ TỊCH
PHÓ CHÁNH VĂN PHÒNG
Người Ký Không Là Nơi Nhận
'''


def pages(text=TEXT):
    return [{"page": 1, "text": text, "width": 595, "height": 842, "images": []}]


class FakeProvider:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    async def extract_mentions(self, pages, metadata, images=None):
        self.calls.append(images)
        return self.payload


def test_rules_keep_recipient_tokens_references_luu_and_not_signer():
    mentions, reasons = extract_rule_mentions(pages())
    raw = {m.raw for m in mentions}
    assert {"Sở Văn hóa, Thể thao và Du lịch", "Hội Nhà báo tỉnh", "Chủ tịch UBND tỉnh", "CVP", "PVPQT", "VT", "V1", "V5", "V8"} <= raw
    assert any("L.H. Giang" in x for x in raw)
    assert not any("Người Ký" in x for x in raw)
    assert not reasons
    assert all(m.evidence for m in mentions)
    assert all("Như trên" in m.references for m in mentions if m.evidence[0].section == "kinh_gui")


def test_rules_keep_group_selector_and_unresolved_body_reference():
    mentions, reasons = extract_rule_mentions(pages('Nơi nhận:\n- Chủ tịch, các PCT UBND tỉnh;\n- Các đơn vị tại mục 2;\n- Lưu: VT, V1.'))
    assert any(m.kind == "group" and "các PCT" in m.raw for m in mentions)
    assert "unsupported_reference" in reasons


def test_offline_text_extraction_is_partial_not_fake_complete():
    with tempfile.TemporaryDirectory() as tmp, patch("ai_document_sender.extraction._read_pages", return_value=pages()):
        result = asyncio.run(extract_document(Path(tmp)/"main.pdf", None, DocumentMetadata(document_id="12355"), Settings(runtime_dir=Path(tmp))))
    assert result.status == "partial"
    assert "provider_unavailable" in result.review_reasons
    assert any(m.raw == "V5" for m in result.mentions)


def test_hybrid_detects_missing_recipient_region_despite_body_text():
    hybrid = pages('Kính gửi: Sở Y tế.\n' + ('Nội dung văn bản. ' * 100))
    hybrid[0]["images"] = [{"bbox": [40, 570, 330, 800]}]
    assert select_vision_pages(hybrid)[0] == [1]
    payload = {"mentions": [{"raw": "Chủ tịch UBND tỉnh", "kind": "role", "evidence": [{"page": 1, "section": "noi_nhan", "raw": "Chủ tịch UBND tỉnh"}]}], "status": "complete", "review_reasons": [], "ocr_pages": [{"page": 1, "text": "Nơi nhận:\n- Chủ tịch UBND tỉnh;"}]}
    provider = FakeProvider(payload)
    with tempfile.TemporaryDirectory() as tmp, patch("ai_document_sender.extraction._read_pages", return_value=hybrid), patch("ai_document_sender.extraction._render_pages", return_value=[{"page": 1, "data_url": "data:image/png;base64,AA=="}]):
        result = asyncio.run(extract_document(Path(tmp)/"hybrid.pdf", provider, DocumentMetadata(document_id="1"), Settings(runtime_dir=Path(tmp))))
    assert provider.calls[0]
    assert any(m.raw == "Chủ tịch UBND tỉnh" for m in result.mentions)


def test_text_model_cannot_add_ungrounded_name():
    provider = FakeProvider({"mentions": [{"raw": "Nguyễn Văn Bịa", "kind": "person", "evidence": [{"page": 1, "section": "noi_nhan", "raw": "Nguyễn Văn Bịa"}]}], "status": "complete", "review_reasons": [], "ocr_pages": []})
    with tempfile.TemporaryDirectory() as tmp, patch("ai_document_sender.extraction._read_pages", return_value=pages()):
        result = asyncio.run(extract_document(Path(tmp)/"main.pdf", provider, DocumentMetadata(document_id="1"), Settings(runtime_dir=Path(tmp))))
    assert result.status == "partial"
    assert "ungrounded_model_mention" in result.review_reasons
    assert not any(m.raw == "Nguyễn Văn Bịa" for m in result.mentions)
    assert any(m.raw == "V1" for m in result.mentions)


def test_model_cannot_promote_signer_with_invented_body_reference():
    provider = FakeProvider({"mentions": [{"raw": "Người Ký Không Là Nơi Nhận", "kind": "person", "evidence": [{"page": 1, "section": "body_reference", "raw": "Người Ký Không Là Nơi Nhận"}], "references": ["invented reference"]}], "status": "complete", "review_reasons": [], "ocr_pages": []})
    with tempfile.TemporaryDirectory() as tmp, patch("ai_document_sender.extraction._read_pages", return_value=pages()):
        result = asyncio.run(extract_document(Path(tmp)/"main.pdf", provider, DocumentMetadata(document_id="1"), Settings(runtime_dir=Path(tmp))))
    assert not any("Người Ký" in mention.raw for mention in result.mentions)
    assert result.status == "partial"
    assert "unsupported_reference" in result.review_reasons


def test_scan_without_renderer_remains_unreadable_and_does_not_fabricate():
    scan = pages("")
    with tempfile.TemporaryDirectory() as tmp, patch("ai_document_sender.extraction._read_pages", return_value=scan), patch("ai_document_sender.extraction._render_pages", side_effect=RuntimeError("Poppler unavailable")):
        result = asyncio.run(extract_document(Path(tmp)/"scan.pdf", FakeProvider({"mentions": [], "status": "complete", "review_reasons": [], "ocr_pages": []}), DocumentMetadata(document_id="1"), Settings(runtime_dir=Path(tmp))))
    assert result.status != "complete"
    assert "unreadable_region" in result.review_reasons


def test_vision_page_limit_does_not_hide_unread_pages():
    scan = [{"page": i, "text": "", "images": []} for i in range(1, 9)]
    chosen, reasons = select_vision_pages(scan, limit=2)
    assert len(chosen) == 2
    assert "vision_page_limit" in reasons


def test_digital_stamp_outside_recipient_column_does_not_require_vision():
    signed = pages()
    signed[0]["recipient_bbox"] = [0, 570, 320, 842]
    signed[0]["images"] = [{"bbox": [290, 580, 475, 800]}]
    assert select_vision_pages(signed)[0] == []


def test_empty_model_complete_cannot_certify_rule_only_recipient_list():
    with tempfile.TemporaryDirectory() as tmp, patch("ai_document_sender.extraction._read_pages", return_value=pages()):
        result = asyncio.run(extract_document(Path(tmp)/"main.pdf", FakeProvider({"mentions": [], "status": "complete", "review_reasons": [], "ocr_pages": []}), DocumentMetadata(document_id="1"), Settings(runtime_dir=Path(tmp))))
    assert result.status == "partial" and "invalid_model_output" in result.review_reasons


def test_real_pdf_text_layout_excludes_signature_name():
    from reportlab.pdfgen import canvas
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    import pytest
    font = next((path for path in [Path("C:/Windows/Fonts/arial.ttf"), Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")] if path.exists()), None)
    if font is None:
        pytest.skip("Unicode test font is unavailable")
    pdfmetrics.registerFont(TTFont("RecipientTest", str(font)))
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp)/"main.pdf"
        pdf = canvas.Canvas(str(path), pagesize=(595,842))
        pdf.setFont("RecipientTest", 11)
        for y, line in [(770,"Kính gửi: Sở Y tế."),(720,"Nội dung văn bản để phối hợp triển khai."),(250,"Nơi nhận:"),(230,"- Như trên;"),(210,"- Chủ tịch UBND tỉnh;"),(190,"- Lưu: VT, V1.")]:
            pdf.drawString(40,y,line)
        pdf.drawString(370,250,"KT. CHỦ TỊCH")
        pdf.drawString(370,160,"Người ký khác")
        pdf.save()
        result = asyncio.run(extract_document(path, None, DocumentMetadata(document_id="real"), Settings(runtime_dir=Path(tmp))))
    assert len(result.pages) == 1
    assert {"Sở Y tế", "Chủ tịch UBND tỉnh", "VT", "V1"} <= {m.raw for m in result.mentions}
    assert not any("Người ký" in m.raw for m in result.mentions)


def test_single_line_kinh_gui_without_punctuation_stops_before_body():
    mentions, _ = extract_rule_mentions(pages("Kính gửi: Sở Y tế\n\nNội dung dài không phải nơi nhận.\nNơi nhận:\n- Như trên;\n- Lưu: VT."))
    assert any(m.raw == "Sở Y tế" for m in mentions)
    assert not any("Nội dung" in m.raw for m in mentions)


def test_partial_word_header_spacing_and_inline_addressee_are_read():
    mentions, reasons = extract_rule_mentions(pages("Kính gửi: Sở Nông nghiệp và Môi trường\nThực hiện Nghị quyết số 90 của tỉnh.\nNơi nh ậ n:\n- Như trên;\n- Lưu: VT, V1."))
    assert "recipient_sections_missing" not in reasons
    assert {"Sở Nông nghiệp và Môi trường", "VT", "V1"} <= {m.raw for m in mentions}
    assert not any("Thực hiện" in m.raw for m in mentions)
