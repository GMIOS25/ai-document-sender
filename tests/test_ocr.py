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
