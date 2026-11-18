import asyncio
import tempfile
from dataclasses import replace
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


def test_vietocr_scan_supplies_grounded_text_without_cloud_images(settings):
    scan = pages("")
    scan[0]["images"] = [{"bbox": [0, 0, 595, 842]}]
    provider = FakeProvider({"mentions": [{"raw": "Chủ tịch UBND tỉnh", "kind": "role",
        "evidence": [{"page": 1, "section": "noi_nhan", "raw": "Chủ tịch UBND tỉnh"}]}],
        "status": "complete", "review_reasons": [], "ocr_pages": []})
    configured = replace(settings, ocr_backend="vietocr")
    def ocr(path, records, active_settings):
        records[0].update(text=TEXT, ocr_text=TEXT, recipient_text=TEXT, local_ocr_complete=True)
        return {"backend": "vietocr", "pages": [1], "device": "cpu", "duration_ms": 10}, []
    with patch("ai_document_sender.extraction._read_pages", return_value=scan), \
            patch("ai_document_sender.extraction.ocr_missing_pages", side_effect=ocr), \
            patch("ai_document_sender.extraction._render_pages") as renderer:
        result = asyncio.run(extract_document(Path("scan.pdf"), provider,
            DocumentMetadata(document_id="local-scan"), configured))
    renderer.assert_not_called()
    assert provider.calls == [None]
    assert result.status == "complete"
    assert result.audit["local_ocr"]["pages"] == [1]
    assert any(m.raw == "Chủ tịch UBND tỉnh" for m in result.mentions)


def test_vietocr_also_recovers_rules_offline_and_skips_text_pages(settings):
    configured = replace(settings, ocr_backend="vietocr")
    def ocr(path, records, active_settings):
        records[0].update(text=TEXT, ocr_text=TEXT, recipient_text=TEXT, local_ocr_complete=True)
        return {"backend": "vietocr", "pages": [1]}, []
    with patch("ai_document_sender.extraction._read_pages", return_value=pages("")), \
            patch("ai_document_sender.extraction.ocr_missing_pages", side_effect=ocr):
        result = asyncio.run(extract_document(Path("scan.pdf"), None,
            DocumentMetadata(document_id="offline-scan"), configured))
    assert any(m.raw == "V5" for m in result.mentions)
    assert "unreadable_region" not in result.review_reasons
    with patch("ai_document_sender.extraction._read_pages", return_value=pages()), \
            patch("ai_document_sender.extraction.ocr_missing_pages") as local:
        asyncio.run(extract_document(Path("text.pdf"), None,
            DocumentMetadata(document_id="text"), configured))
    local.assert_not_called()


def test_vietocr_failure_is_reviewable_and_does_not_use_cloud_ocr(settings):
    configured = replace(settings, ocr_backend="vietocr")
    provider = FakeProvider({"mentions": [], "status": "partial", "review_reasons": [], "ocr_pages": []})
    with patch("ai_document_sender.extraction._read_pages", return_value=pages("")), \
            patch("ai_document_sender.extraction.ocr_missing_pages",
                  return_value=({"backend": "vietocr", "pages": []}, ["local_ocr_unavailable"])), \
            patch("ai_document_sender.extraction._render_pages") as renderer:
        result = asyncio.run(extract_document(Path("scan.pdf"), provider,
            DocumentMetadata(document_id="bad-ocr"), configured))
    renderer.assert_not_called()
    assert "local_ocr_unavailable" in result.review_reasons
    assert "unreadable_region" in result.review_reasons
    assert result.status == "partial"


def test_real_pdf_signature_chanh_van_phong_and_signer_name_not_clipped():
    from reportlab.pdfgen import canvas
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    import pytest
    font = next((path for path in [Path("C:/Windows/Fonts/arial.ttf"), Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")] if path.exists()), None)
    if font is None:
        pytest.skip("Unicode test font is unavailable")
    pdfmetrics.registerFont(TTFont("RecipientTestSig", str(font)))
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "chanh.pdf"
        pdf = canvas.Canvas(str(path), pagesize=(595, 842))
        pdf.setFont("RecipientTestSig", 11)
        for y, line in [
            (770, "Kính gửi: Sở Xây dựng."),
            (720, "Nội dung công văn."),
            (320, "Nơi nhận:"),
            (300, "- Như trên;"),
            (280, "- PCT Nguyễn Tự Công Hoàng;"),
            (260, "- Lưu: VT, X5, T3."),
        ]:
            pdf.drawString(40, y, line)
        pdf.drawString(372, 315, "TL. CHỦ TỊCH")
        pdf.drawString(350, 298, "CHÁNH VĂN PHÒNG")
        pdf.drawString(362, 200, "Nguyễn Xuân Vĩnh")
        pdf.save()
        result = asyncio.run(extract_document(path, None, DocumentMetadata(document_id="chanh"), Settings(runtime_dir=Path(tmp))))
    rtext = result.pages[0]["recipient_text"]
    assert "CH" not in rtext.splitlines()
    assert not any(ln.strip() in {"CH", "N", "Ng"} for ln in rtext.splitlines())
    raws = {m.raw for m in result.mentions}
    assert {"Sở Xây dựng", "PCT Nguyễn Tự Công Hoàng", "VT", "X5", "T3"} <= raws


def test_kinh_gui_multiline_semicolons_and_missing_comma_so_split():
    text_13060 = (
        "Kính gửi:\n"
        "- Các Sở: Khoa học và Công nghệ; Giáo dục và Đào\n"
        "tạo; Công Thương; Nông nghiệp và Môi trường;\n"
        "Xây dựng; Tài chính; Văn hóa, Thể thao và Du lịch;\n"
        "- UBND các xã: Tuy Phước, Ia Le;\n"
        "- Văn phòng UBND tỉnh.\n"
        "Căn cứ Công văn số 603/2026/CV-VUNI."
    )
    mentions, _ = extract_rule_mentions(pages(text_13060))
    got = {(m.raw, m.qualifier) for m in mentions}
    assert {
        ("Khoa học và Công nghệ", "Sở"),
        ("Giáo dục và Đào tạo", "Sở"),
        ("Công Thương", "Sở"),
        ("Nông nghiệp và Môi trường", "Sở"),
        ("Xây dựng", "Sở"),
        ("Tài chính", "Sở"),
        ("Văn hóa, Thể thao và Du lịch", "Sở"),
        ("Tuy Phước", "UBND xã"),
        ("Ia Le", "UBND xã"),
        ("Văn phòng UBND tỉnh", None),
    } <= got

    text_12874 = (
        "Kính gửi:\n"
        "- Các Sở: Xây dựng, Tài chính\n"
        "Nông nghiệp và Môi trường;\n"
        "- Ban QLDA Giao thông và Dân dụng tỉnh;\n"
        "Xét đề nghị của Sở Xây dựng."
    )
    mentions_12874, _ = extract_rule_mentions(pages(text_12874))
    assert {
        ("Xây dựng", "Sở"),
        ("Tài chính", "Sở"),
        ("Nông nghiệp và Môi trường", "Sở"),
        ("Ban QLDA Giao thông và Dân dụng tỉnh", None),
    } <= {(m.raw, m.qualifier) for m in mentions_12874}

    text_12635 = (
        "Kính gửi:\n"
        "- Sở Ngoại vụ;\n"
        "- Sở Xây dựng;\n"
        "Công an tỉnh;\n"
        "- UBND xã Tuy Phước.\n"
        "Thực hiện Kế hoạch số 371/KH-UBND."
    )
    mentions_12635, _ = extract_rule_mentions(pages(text_12635))
    assert {"Sở Ngoại vụ", "Sở Xây dựng", "Công an tỉnh", "UBND xã Tuy Phước"} <= {m.raw for m in mentions_12635}


def test_blank_trailing_page_in_native_pdf_does_not_trigger_local_ocr_empty_page(settings):
    from reportlab.pdfgen import canvas
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    import pytest
    font = next((path for path in [Path("C:/Windows/Fonts/arial.ttf"), Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")] if path.exists()), None)
    if font is None:
        pytest.skip("Unicode test font is unavailable")
    pdfmetrics.registerFont(TTFont("RecipientTestBlank", str(font)))
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "trailing_blank.pdf"
        pdf = canvas.Canvas(str(path), pagesize=(595, 842))
        pdf.setFont("RecipientTestBlank", 11)
        pdf.drawString(40, 770, "Kính gửi: Sở Tài chính.")
        pdf.drawString(40, 250, "Nơi nhận:")
        pdf.drawString(40, 230, "- Như trên;")
        pdf.drawString(40, 210, "- Lưu: VT.")
        pdf.showPage()
        pdf.showPage()
        pdf.save()
        configured = replace(settings, ocr_backend="vietocr", runtime_dir=Path(tmp))
        with patch("ai_document_sender.ocr._get_reader"), \
                patch("ai_document_sender.ocr._render_image") as render_img:
            result = asyncio.run(extract_document(path, None, DocumentMetadata(document_id="blank-p2"), configured))
    render_img.assert_not_called()
    assert "local_ocr_empty_page" not in result.review_reasons
    assert "unreadable_region" not in result.review_reasons
    assert result.pages[1].get("blank") is True


def test_kinh_gui_without_colon_body_bleed_and_tm_signature():
    no_colon = (
        "Kính gửi\n"
        "- Sở Nông nghiệp và Môi trường;\n"
        "- Sở Công Thương.\n"
        "Thực hiện Văn bản số 12017/BNNMT.\n"
        "Nơi nhận: TM\n"
        "- Như trên;\n"
        "- Lưu: VT."
    )
    mentions_nc, _ = extract_rule_mentions(pages(no_colon))
    raws_nc = {m.raw for m in mentions_nc}
    assert {"Sở Nông nghiệp và Môi trường", "Sở Công Thương", "VT"} <= raws_nc
    assert "TM" not in raws_nc

    for bleed_doc in [
        "Kính gửi: Sở Giáo dục và Đào tạo\nSau khi xem xét Tờ trình số 6802/TTr-SGDĐT ngày 07/10/2026.\nNơi nh ận: T M\n- Như trên;\n- Lưu: VT.",
        "Kính gửi: Bộ Công Thương\nPhát triển năng lượng tái tạo là một trong những định hướng quan trọng.\nNơi nhận:\n- Như trên.",
        "Kính gửi:\n- Sở Tài chính\n- Căn cứ Quyết định số 3009/QĐ-UBND năm 2026.\nNơi nhận:\n- Như trên.",
        "Kính gửi:\nỦy ban nhân dân tỉnh Gia Lai trân trọng cảm ơn sự quan tâm.\nNơi nhận:\n- Lưu: VT.",
    ]:
        ms, _ = extract_rule_mentions(pages(bleed_doc))
        for m in ms:
            assert len(m.raw) <= 60, f"Unexpected body bleed mention: {m.raw!r}"
            assert m.raw not in {"TM", "T M"}


def test_extract_ban_qlda_batch_enumeration_stt353():
    mentions_out, _ = extract_rule_mentions(
        [
            {
                "page": 1,
                "text": (
                    "Kính gửi\n"
                    "- Các Ban QLDA: Giao thông và Dân dụng, Nông nghiệp và PTNT, Đầu tư xây dựng tỉnh.\n"
                    "Nơi nhận:\n"
                    "- Như trên;\n"
                    "- PCTTT UBND tỉnh;\n"
                    "- Lưu: VT."
                ),
            }
        ]
    )
    kinh_gui = [(m.raw, m.qualifier) for m in mentions_out if m.evidence[0].section == "kinh_gui"]
    assert kinh_gui == [
        ("Giao thông và Dân dụng", "Ban QLDA"),
        ("Nông nghiệp và PTNT", "Ban QLDA"),
        ("Đầu tư xây dựng tỉnh", "Ban QLDA"),
    ]
    noi_nhan = [m.raw for m in mentions_out if m.evidence[0].section == "noi_nhan"]
    assert "PCTTT UBND tỉnh" in noi_nhan


def test_extract_handles_wraps_semicolons_pvp_nfd_and_luu_subscripts():
    from reportlab.pdfgen import canvas
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    import pytest

    # 1. STT 422 / 490 lowercase continuation + STT 379 Các sở, ngành + STT 383 Như trên (thực hiện)
    # 2. STT 179 semicolon wrap & split in noi_nhan + STT 35/214 PVP: NN, XD + N1,4 shorthand + STT 466 NFD header
    text = (
        "Kính gửi:\n"
        "- Công ty cổ phần Đào tạo và Dịch vụ\n"
        "giao thông vận tải Bình Định.\n"
        "- Các sở, ngành: Văn hóa, Thể thao và Du lịch; Xây dựng.\n"
        "Nơi nh\u00e2\u0323n:\n"
        "- Như trên (thực hiện);\n"
        "- Sở Tư pháp; Sở Tài chính;\n"
        "Sở Nông nghiệp và Môi trường;\n"
        "- PVP: NN, XD;\n"
        "- Lưu: VT, N1, 4, X5\n"
        "Văn bản số 10139/STC-QLGCS ngày 06/10/2026"
    )
    mentions, reasons = extract_rule_mentions(pages(text))
    raws = {m.raw for m in mentions}
    assert "Công ty cổ phần Đào tạo và Dịch vụ giao thông vận tải Bình Định" in raws
    assert {"Sở Tư pháp", "Sở Tài chính", "Sở Nông nghiệp và Môi trường"} <= raws
    assert {"PVP NN", "PVP XD", "VT", "N1", "N4", "X5"} <= raws
    assert ("Văn hóa, Thể thao và Du lịch", "Sở") in {(m.raw, m.qualifier) for m in mentions}
    assert "unsupported_reference" not in reasons
    assert not any("10139" in m.raw or m.raw == "XD" for m in mentions)

    # 3. Reportlab PDF with lowered subscript digits on Lưu: line (-4.2pt)
    font = next((path for path in [Path("C:/Windows/Fonts/arial.ttf"), Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")] if path.exists()), None)
    if font is None:
        pytest.skip("Unicode test font is unavailable")
    pdfmetrics.registerFont(TTFont("SubscriptTestFont", str(font)))
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "subscript.pdf"
        pdf = canvas.Canvas(str(path), pagesize=(595, 842))
        pdf.setFont("SubscriptTestFont", 10)
        pdf.drawString(85, 760, "Kính gửi: Sở Công Thương.")
        pdf.drawString(85, 250, "Nơi nhận:")
        pdf.drawString(85, 235, "- Như trên;")
        pdf.drawString(85, 220, "- Lưu: VT, N")
        pdf.setFont("SubscriptTestFont", 6.5)
        pdf.drawString(148, 217.5, "1")
        pdf.setFont("SubscriptTestFont", 10)
        pdf.drawString(152, 220, ",    , X")
        pdf.setFont("SubscriptTestFont", 6.5)
        pdf.drawString(157, 217.5, "4")
        pdf.drawString(182, 217.5, "5.")
        pdf.save()
        res = asyncio.run(extract_document(path, None, DocumentMetadata(document_id="sub"), Settings(runtime_dir=Path(tmp))))
    luu_raws = {m.raw for m in res.mentions if m.evidence[0].section == "luu"}
    assert {"VT", "N1", "N4", "X5"} <= luu_raws


def test_vietocr_low_confidence_escalates_to_hybrid_vision_fallback(settings):
    scan = pages("")
    scan[0]["images"] = [{"bbox": [0, 0, 595, 842]}]
    configured = replace(settings, ocr_backend="vietocr")

    def noisy_ocr(path, records, active_settings):
        records[0].update(
            text="Kính gửi: UBND\nNơi nhận:\n- Lưu: VT, T475",
            ocr_text="Kính gửi: UBND\nNơi nhận:\n- Lưu: VT, T475",
            recipient_text="Nơi nhận:\n- Lưu: VT, T475",
            local_ocr_complete=True,
            local_ocr_low_confidence=True,
        )
        return {"backend": "vietocr", "pages": [1]}, ["local_ocr_low_confidence"]

    vision_text = "Kính gửi: Sở Tài chính.\nNơi nhận:\n- Như trên;\n- Lưu: VT, T4, T5."
    provider = FakeProvider({
        "mentions": [{"raw": "Sở Tài chính", "kind": "unit", "evidence": [{"page": 1, "section": "kinh_gui", "raw": "Sở Tài chính"}]}],
        "status": "complete",
        "review_reasons": [],
        "ocr_pages": [{"page": 1, "text": vision_text}],
    })
    with patch("ai_document_sender.extraction._read_pages", return_value=scan), \
            patch("ai_document_sender.extraction.ocr_missing_pages", side_effect=noisy_ocr), \
            patch("ai_document_sender.extraction._render_pages", return_value=[{"page": 1, "data_url": "data:image/png;base64,AA=="}]):
        result = asyncio.run(extract_document(Path("lowconf.pdf"), provider, DocumentMetadata(document_id="hybrid-lowconf"), configured))
    assert provider.calls[0]
    raws = {m.raw for m in result.mentions}
    assert {"Sở Tài chính", "VT", "T4", "T5"} <= raws
    assert "T475" not in raws


def test_numbered_body_task_headings_extracted_when_nhu_tren_present():
    p1 = (
        "Kính gửi:\n"
        "- Công an tỉnh;\n"
        "- Sở Ngoại vụ;\n"
        "- UBND phường Hội Phú.\n"
        "1. Công an tỉnh: Khẩn trương xác minh.\n"
        "2. Sở Giáo dục và Đào tạo chủ trì, phối hợp với Sở Ngoại vụ:\n"
        "3. Các Sở: Khẩn trương báo cáo.\n"
    )
    p2 = (
        "4. Sở Y tế: Chỉ đạo các cơ sở y tế phối hợp thực hiện.\n"
        "5. Sở Văn hóa, Thể thao và Du lịch: Định hướng thông tin.\n"
        "Nơi nhận:\n"
        "- Như trên;\n"
        "- Lưu: VT, V7.\n"
    )
    mentions, _ = extract_rule_mentions([
        {"page": 1, "text": p1, "width": 595, "height": 842, "images": []},
        {"page": 2, "text": p2, "width": 595, "height": 842, "images": []},
    ])
    body_raws = {m.raw for m in mentions if m.evidence[0].section == "body_reference"}
    assert body_raws == {"Sở Y tế", "Sở Văn hóa, Thể thao và Du lịch"}
    for m in mentions:
        if m.evidence[0].section == "body_reference":
            assert "Như trên" in m.references


def test_failed_provider_keeps_provider_used_false_and_retains_provider_audit(settings):
    from ai_document_sender.provider import ProviderError

    class FailingProvider:
        last_audit = {"provider": "openrouter", "duration_ms": 60000.0, "error_code": "provider_timeout"}

        async def extract_mentions(self, pages, metadata, images=None):
            raise ProviderError("provider_timeout", "timed out")

    with tempfile.TemporaryDirectory() as tmp, patch("ai_document_sender.extraction._read_pages", return_value=pages()):
        result = asyncio.run(extract_document(Path(tmp) / "main.pdf", FailingProvider(), DocumentMetadata(document_id="timeout"), settings))
    assert result.audit["provider_used"] is False
    assert result.audit["provider"]["error_code"] == "provider_timeout"
    assert result.audit["provider"]["duration_ms"] == 60000.0
    assert "provider_timeout" in result.review_reasons
