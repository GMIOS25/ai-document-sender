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
