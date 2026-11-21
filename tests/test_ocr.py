from dataclasses import replace
from unittest.mock import patch
import pytest

from PIL import Image

from ai_document_sender import ocr


def line(text, x, y, width=260, score=0.99):
    return {"text": text, "bbox": [x, y, x + width, y + 20], "confidence": score}


def test_local_ocr_keeps_table_rows_and_separates_recipient_signature_columns():
    page = {"page": 2, "text": "", "width": 600, "height": 850}
    lines = [line("Điều 3. Chịu trách nhiệm thi hành.", 80, 80, 440),
             line("Nơi nhận:", 60, 300, 100), line("KT. CHỦ TỊCH", 360, 301, 200),
             line("- Chủ tịch UBND tỉnh;", 60, 330), line("PHÓ CHỦ TỊCH", 360, 332, 200),
             line("- Sở Y tế;", 60, 360), line("Người ký khác", 360, 400, 200),
             line("- Lưu: VT, V1.", 60, 420),
             line("1", 30, 500, 10), line("Nguyễn Văn A", 100, 501, 160),
             line("Giám đốc", 350, 499, 150)]
    ocr._apply_page_text(page, lines)
    assert "1 Nguyễn Văn A Giám đốc" in page["text"]
    assert "Người ký khác" in page["text"]
    assert "Người ký khác" not in page["recipient_text"]
    assert "PHÓ CHỦ TỊCH" not in page["recipient_text"]
    assert "- Chủ tịch UBND tỉnh;\n- Sở Y tế;\n- Lưu: VT, V1." in page["recipient_text"]
    assert page["ocr_text"] == page["text"]
    assert page["local_ocr_complete"] is True


def test_local_ocr_processes_only_scan_pages_without_cloud_page_limit(settings):
    records = [{"page": i, "text": "", "width": 600, "height": 850} for i in range(1, 8)]
    native = {"page": 8, "text": "Nơi nhận:\n- Sở Y tế;", "width": 600, "height": 850}
    records.append(native.copy())
    configured = replace(settings, ocr_backend="vietocr", max_vision_pages=1)
    class Reader:
        device = "cpu"
        def read(self, image, batch_size):
            return [line("Nơi nhận:", 40, 300), line("- Sở Y tế;", 40, 330)]
    with patch.object(ocr, "_get_reader", return_value=Reader()), \
            patch.object(ocr, "_render_image", return_value=Image.new("RGB", (600, 850))) as render:
        audit, reasons = ocr.ocr_missing_pages("scan.pdf", records, configured)
    assert not reasons
    assert audit["pages"] == list(range(1, 8))
    assert render.call_count == 7
    assert records[-1] == native
    assert all(record["local_ocr_complete"] for record in records[:-1])


def test_local_ocr_does_not_discard_low_confidence_text(settings):
    records = [{"page": 1, "text": "", "width": 600, "height": 850}]
    class Reader:
        device = "cpu"
        def read(self, image, batch_size):
            return [line("Nơi nhận:", 40, 300), line("- Nguyễn Văn A;", 40, 330, score=0.6)]
    with patch.object(ocr, "_get_reader", return_value=Reader()), \
            patch.object(ocr, "_render_image", return_value=Image.new("RGB", (600, 850))):
        audit, reasons = ocr.ocr_missing_pages("scan.pdf", records, settings)
    assert "local_ocr_low_confidence" in reasons
    assert "Nguyễn Văn A" in records[0]["text"]
    assert audit["pages"] == [1]


def test_local_ocr_missing_dependencies_remain_reviewable(settings):
    with patch.object(ocr, "_get_reader", side_effect=ImportError("missing optional package")):
        audit, reasons = ocr.ocr_missing_pages("scan.pdf", [{"page": 1, "text": ""}], settings)
    assert audit["pages"] == []
    assert reasons == ["local_ocr_unavailable"]


def test_local_ocr_keeps_successful_page_when_another_page_fails(settings):
    records = [{"page": i, "text": "", "width": 600, "height": 850} for i in (1, 2)]
    class Reader:
        device = "cpu"
        def read(self, image, batch_size):
            return [line("Nơi nhận:", 40, 300), line("- Sở Y tế;", 40, 330)]
    with patch.object(ocr, "_get_reader", return_value=Reader()), \
            patch.object(ocr, "_render_image", side_effect=[Image.new("RGB", (600, 850)), RuntimeError("bad page")]):
        audit, reasons = ocr.ocr_missing_pages("scan.pdf", records, settings)
    assert audit["pages"] == [1]
    assert "local_ocr_failed" in reasons
    assert records[0]["local_ocr_complete"]
    assert not records[1]["text"]


def test_detector_scales_text_boxes_and_ignores_weak_regions():
    pytest.importorskip("cv2")
    np = pytest.importorskip("numpy")
    class Input:
        name = "image"
    class Detector:
        def get_inputs(self):
            return [Input()]
        def run(self, outputs, inputs):
            assert inputs["image"].shape[1] == 3
            mask = np.zeros((1, 1, 96, 96), dtype=np.float32)
            mask[0, 0, 30:35, 10:50] = 0.9
            mask[0, 0, 50:55, 10:50] = 0.4
            return [mask]
    image = np.full((960, 480, 3), 255, dtype=np.uint8)
    boxes = ocr._detect_lines(image, Detector())
    assert len(boxes) == 1
    assert 250 < boxes[0][:, 1].min() < 300
    assert boxes[0][:, 0].max() < 480
    crop = ocr._crop_line(image, boxes[0])
    assert crop.shape[1] > crop.shape[0]


def test_visible_bullet_is_detected_without_inventing_one_on_plain_text():
    cv2 = pytest.importorskip("cv2")
    np = pytest.importorskip("numpy")
    image = np.full((100, 400, 3), 255, dtype=np.uint8)
    box = np.asarray([[0, 20], [399, 20], [399, 70], [0, 70]], dtype=np.float32)
    cv2.putText(image, "Example", (30, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
    assert not ocr._has_bullet_prefix(image, box)
    cv2.rectangle(image, (10, 48), (19, 50), (0, 0, 0), -1)
    assert ocr._has_bullet_prefix(image, box)


def test_layout_text_separates_overlapping_tall_box_and_filters_low_conf_stamp():
    lines = [
        {"text": "Nơi nhận:", "confidence": 0.92, "bbox": [95.0, 675.0, 145.0, 690.0]},
        {"text": "- CVP, PVPXD;", "confidence": 0.81, "bbox": [95.0, 731.9, 170.6, 745.1]},
        {"text": "- Lưu: VT, T3, X", "confidence": 0.81, "bbox": [91.3, 735.5, 201.9, 770.9]},
        {"text": "20", "confidence": 0.39, "bbox": [334.7, 736.1, 356.2, 747.4]},
        {"text": "KT. CHỦ TỊCH", "confidence": 0.90, "bbox": [380.0, 675.0, 460.0, 690.0]},
    ]
    page = {"width": 605.0, "height": 844.0}
    ocr._apply_page_text(page, lines)
    assert page["recipient_text"].splitlines() == [
        "Nơi nhận:",
        "- CVP, PVPXD;",
        "- Lưu: VT, T3, X",
    ]


def test_low_confidence_left_dash_artifact_becomes_bullet_prefix():
    lines = [
        {"text": "Kính gửi:", "confidence": 0.90, "bbox": [210.0, 175.0, 264.0, 194.0]},
        {"text": "- Sở Ngoại vụ;", "confidence": 0.86, "bbox": [271.0, 191.6, 358.1, 210.8]},
        {"text": "Sở Văn hóa, Thể thao và Du lịch;", "confidence": 0.89, "bbox": [283.4, 208.0, 464.6, 226.4]},
        {"text": "Part", "confidence": 0.14, "bbox": [275.1, 212.8, 289.0, 220.5]},
        {"text": "Sở Xây dựng;", "confidence": 0.88, "bbox": [283.5, 224.1, 361.5, 243.3]},
        {"text": "STATES", "confidence": 0.23, "bbox": [274.2, 229.4, 289.1, 237.2]},
        {"text": "- UBND xã Tuy Phước.", "confidence": 0.84, "bbox": [268.9, 258.4, 406.3, 274.0]},
    ]
    page = {"width": 597.0, "height": 842.0}
    ocr._apply_page_text(page, lines)
    assert page["text"].splitlines() == [
        "Kính gửi:",
        "- Sở Ngoại vụ;",
        "- Sở Văn hóa, Thể thao và Du lịch;",
        "- Sở Xây dựng;",
        "- UBND xã Tuy Phước.",
    ]


def test_apply_page_text_normalizes_colonless_left_noi_nhan_and_ignores_right_column():
    from ai_document_sender.mentions import extract_rule_mentions

    page_no_colon = {"page": 1, "text": "", "width": 600.0, "height": 850.0}
    ocr._apply_page_text(
        page_no_colon,
        [
            line("Nơi nhận", 60.0, 300.0, 90.0),
            line("KT. CHỦ TỊCH", 360.0, 301.0, 180.0),
            line("- Sở Y tế;", 60.0, 330.0),
            line("Người ký", 360.0, 360.0, 140.0),
            line("- Lưu: VT.", 60.0, 390.0),
        ],
    )
    assert page_no_colon["recipient_text"].splitlines() == [
        "Nơi nhận:",
        "- Sở Y tế;",
        "- Lưu: VT.",
    ]
    assert "recipient_bbox" in page_no_colon
    mentions, reasons = extract_rule_mentions([page_no_colon])
    assert "recipient_sections_missing" not in reasons
    assert {"Sở Y tế", "VT"} <= {m.raw for m in mentions}

    page_nfd_dot = {"page": 1, "text": "", "width": 600.0, "height": 850.0}
    ocr._apply_page_text(
        page_nfd_dot,
        [
            line("Nơi nhâ\u0323n.", 50.0, 300.0, 95.0),
            line("- Sở Nội vụ;", 50.0, 330.0),
        ],
    )
    assert page_nfd_dot["recipient_text"].splitlines()[0] == "Nơi nhận:"

    page_right_col = {"page": 1, "text": "", "width": 600.0, "height": 850.0}
    ocr._apply_page_text(
        page_right_col,
        [
            line("Nơi nhận", 300.0, 300.0, 90.0),
            line("- Sở Y tế;", 60.0, 330.0),
        ],
    )
    assert "recipient_text" not in page_right_col
    assert "recipient_bbox" not in page_right_col


def test_apply_page_text_updates_page_text_for_body_task_and_prefers_explicit_header():
    from ai_document_sender.mentions import extract_rule_mentions
    from ai_document_sender.provider import compact_pages_for_llm

    page_body = {"page": 1, "text": "", "width": 600.0, "height": 850.0}
    ocr._apply_page_text(
        page_body,
        [
            line("Kính gửi: Sở Tài chính.", 60.0, 100.0),
            line("1. Sở Xây dựng: Thực hiện.", 60.0, 160.0),
            line("Nơi nhận", 60.0, 300.0, 90.0),
            line("KT. CHỦ TỊCH", 360.0, 301.0, 180.0),
            line("- Như trên;", 60.0, 330.0),
            line("Nguyễn Văn Ký", 360.0, 360.0, 140.0),
            line("- Lưu: VT.", 60.0, 390.0),
        ],
    )
    assert "Nơi nhận:" in page_body["text"]
    assert page_body["ocr_text"] == page_body["text"]
    mentions, _ = extract_rule_mentions([page_body])
    assert {"Sở Tài chính", "Sở Xây dựng", "VT"} <= {m.raw for m in mentions}

    # Verify compact_pages_for_llm with nn_has_ref strips signature bleed when colonless header is normalized.
    page_ref = {"page": 1, "text": "", "width": 600.0, "height": 850.0}
    ocr._apply_page_text(
        page_ref,
        [
            line("Điều 1. Sở Xây dựng thực hiện.", 60.0, 160.0),
            line("Nơi nhận", 60.0, 300.0, 90.0),
            line("KT. CHỦ TỊCH", 360.0, 301.0, 180.0),
            line("- Như Điều 1;", 60.0, 330.0),
            line("Nguyễn Văn Ký", 360.0, 360.0, 140.0),
            line("- Lưu: VT.", 60.0, 390.0),
        ],
    )
    compacted = compact_pages_for_llm([page_ref])
    assert "Nguyễn Văn Ký" not in compacted[0]["text"]
    assert "- Như Điều 1;" in compacted[0]["text"]

    # Explicit "Nơi nhận:" footer must win over an earlier colonless body/table "Nơi nhận".
    page_explicit_wins = {"page": 1, "text": "", "width": 600.0, "height": 850.0}
    ocr._apply_page_text(
        page_explicit_wins,
        [
            line("Nơi nhận", 60.0, 150.0, 90.0),
            line("Nội dung bảng biểu", 60.0, 180.0, 200.0),
            line("Nơi nhâ\u0323n:", 280.0, 400.0, 100.0),
            line("KT. CHỦ TI\u0323CH", 360.0, 401.0, 180.0),
            line("- Sở Nội vụ;", 60.0, 430.0),
        ],
    )
    assert page_explicit_wins["recipient_text"].splitlines() == ["Nơi nhận:", "- Sở Nội vụ;"]
    assert "Nội dung bảng biểu" not in page_explicit_wins["recipient_text"]


def test_ocr_missing_pages_low_confidence_ignores_dropped_speckles(settings):
    records = [{"page": 1, "text": "", "width": 600.0, "height": 850.0}]

    class SpeckleReader:
        device = "cpu"

        def read(self, image, batch_size):
            return [
                {"text": "Nơi nhận:", "bbox": [60.0, 300.0, 160.0, 320.0], "confidence": 0.96},
                {"text": " x ", "bbox": [310.0, 300.0, 318.0, 315.0], "confidence": 0.20},
                {"text": "- Sở Y tế;", "bbox": [60.0, 330.0, 200.0, 350.0], "confidence": 0.94},
            ]

    with patch.object(ocr, "_get_reader", return_value=SpeckleReader()), \
            patch.object(ocr, "_render_image", return_value=Image.new("RGB", (600, 850))):
        audit, reasons = ocr.ocr_missing_pages("clean.pdf", records, settings)
    assert audit["pages"] == [1]
    assert "local_ocr_low_confidence" not in reasons
    assert records[0]["local_ocr_low_confidence"] is False


def test_suppress_colored_ink_removes_blue_handwriting_and_red_seal_keeps_black_print():
    import numpy as np

    canvas = np.full((60, 120, 3), 255, dtype=np.uint8)
    # Dark black printed glyphs (plain and overlapping a red seal)
    canvas[15:30, 10:20] = (15, 15, 15)
    canvas[15:30, 40:55] = (45, 45, 210)  # bright red seal background (BGR)
    canvas[20:26, 44:51] = (10, 10, 10)   # dark print on top of red seal (BGR)
    # Blue handwritten initials (BGR: high B, low R)
    canvas[32:50, 75:100] = (210, 70, 20)

    cleaned = ocr._suppress_colored_ink(canvas)
    assert np.all(cleaned[15:30, 10:20] == (15, 15, 15))
    assert np.all(cleaned[20:26, 44:51] == (10, 10, 10))
    assert np.all(cleaned[15:19, 40:55] == (255, 255, 255))
    assert np.all(cleaned[32:50, 75:100] == (255, 255, 255))

    bw_only = np.full((20, 20, 3), 255, dtype=np.uint8)
    bw_only[5:10, 5:10] = (20, 20, 20)
    assert ocr._suppress_colored_ink(bw_only) is bw_only
