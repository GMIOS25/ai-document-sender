"""Detect text lines locally, then recognize Vietnamese with VietOCR.

The detector is PP-OCRv4 with ONNX/OpenCV; recognition is exclusively
VietOCR vgg_seq2seq. Optional dependencies and model weights are loaded lazily.
"""
import base64
from functools import lru_cache
import io
import hashlib
import importlib.util
import math
import os
from pathlib import Path
import threading
import time
import unicodedata

from .mentions import HEADERS, SIGNATURE

VERSION = "vietocr-seq2seq-layout-v1"
WEIGHTS_URL = "https://vocr.vn/data/vietocr/vgg_seq2seq.pth"
DETECTOR_URL = "https://huggingface.co/SWHL/RapidOCR/resolve/main/PP-OCRv4/ch_PP-OCRv4_det_infer.onnx"
DETECTOR_SHA256 = "d2a7720d45a54257208b1e13e36a8479894cb74155a5efe29462512d42f49da9"
_LOCK = threading.Lock()

# Inference settings from the official base.yml and vgg-seq2seq.yml at
# https://github.com/pbcquoc/vietocr/tree/fe8c3a7fc714aec57ab81cec844eb3adf0c1636c/config
# Bundled here so processing a PDF never downloads configuration or weights.
_VOCAB = 'aAàÀảẢãÃáÁạẠăĂằẰẳẲẵẴắẮặẶâÂầẦẩẨẫẪấẤậẬbBcCdDđĐeEèÈẻẺẽẼéÉẹẸêÊềỀểỂễỄếẾệỆfFgGhHiIìÌỉỈĩĨíÍịỊjJkKlLmMnNoOòÒỏỎõÕóÓọỌôÔồỒổỔỗỖốỐộỘơƠờỜởỞỡỠớỚợỢpPqQrRsStTuUùÙủỦũŨúÚụỤưƯừỪửỬữỮứỨựỰvVwWxXyYỳỲỷỶỹỸýÝỵỴzZ0123456789!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~ '


class VietOCRReader:
    def __init__(self, weights, device):
        import torch
        import onnxruntime as ort
        from vietocr.tool.predictor import Predictor
        if not Path(weights).is_file():
            raise FileNotFoundError("Run prepare-ocr before processing scanned PDFs")
        self.device = "cuda:0" if device == "auto" and torch.cuda.is_available() else ("cpu" if device == "auto" else device)
        config = {
            "vocab": _VOCAB, "weights": weights, "device": self.device,
            "backbone": "vgg19_bn", "seq_modeling": "seq2seq",
            "cnn": {"ss": [[2, 2], [2, 2], [2, 1], [2, 1], [1, 1]],
                    "ks": [[2, 2], [2, 2], [2, 1], [2, 1], [1, 1]],
                    "hidden": 256, "pretrained": False},
            "transformer": {"encoder_hidden": 256, "decoder_hidden": 256,
                            "img_channel": 256, "decoder_embedded": 256, "dropout": 0.1},
            "dataset": {"image_height": 32, "image_min_width": 32, "image_max_width": 512},
            "predictor": {"beamsearch": False},
        }
        self.predictor = Predictor(config)
        options = ort.SessionOptions()
        options.intra_op_num_threads = 2
        options.inter_op_num_threads = 2
        detector_path = Path(weights).parent / "ppocr_det.onnx"
        if not detector_path.is_file():
            raise FileNotFoundError("Run prepare-ocr to download the text line detector")
        self.detector = ort.InferenceSession(str(detector_path), sess_options=options,
                                             providers=["CPUExecutionProvider"])

    def read(self, image, batch_size):
        import cv2
        import numpy as np
        from PIL import Image
        rgb = cv2.cvtColor(np.asarray(image.convert("RGB")), cv2.COLOR_RGB2BGR)
        boxes = _detect_lines(rgb, self.detector)
        if not boxes:
            return []
        crops = [_crop_line(rgb, box) for box in boxes]
        crops = [Image.fromarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)) for crop in crops]
        texts, scores = [], []
        for start in range(0, len(crops), batch_size):
            words, probabilities = self.predictor.predict_batch(crops[start:start + batch_size], return_prob=True)
            texts.extend(words)
            scores.extend(probabilities)
        return [{"text": ("- " if _has_bullet_prefix(rgb, box) and not text.lstrip().startswith(("-", "–", "—", "•")) else "")
                         + unicodedata.normalize("NFC", text).strip(),
                 "confidence": float(score) if math.isfinite(float(score)) else 0.0,
                 "bbox": [min(p[0] for p in box), min(p[1] for p in box),
                          max(p[0] for p in box), max(p[1] for p in box)]}
                for box, text, score in zip(boxes, texts, scores) if text.strip()]


def _has_bullet_prefix(image, box):
    """Keep a visible leading dash which the recognizer sometimes omits."""
    import cv2
    import numpy as np
    x, y = np.floor(box.min(axis=0)).astype(int)
    right, bottom = np.ceil(box.max(axis=0)).astype(int)
    height = bottom - y
    x, y = max(0, x), max(0, y)
    crop = image[y:min(image.shape[0], bottom), x:min(right, x + round(height * 1.2))]
    if not crop.size:
        return False
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, 140, 255, cv2.THRESH_BINARY_INV)
    _, _, components, _ = cv2.connectedComponentsWithStats(binary)
    return any(w >= 4 and w / max(1, h) >= 1.5 and h <= height * 0.25
               and height * 0.25 < cy + h / 2 < height * 0.85
               for _, cy, w, h, _ in components[1:])


def _detect_lines(image, detector):
    """PP-OCRv4 normalization and DB probability contours, without GEOS DLLs."""
    import cv2
    import numpy as np
    height, width = image.shape[:2]
    ratio = 960 / max(height, width)
    resized_w = max(32, round(width * ratio / 32) * 32)
    resized_h = max(32, round(height * ratio / 32) * 32)
    resized = cv2.resize(image, (resized_w, resized_h)).astype(np.float32)
    tensor = ((resized / 255 - 0.5) / 0.5).transpose(2, 0, 1)[None]
    probabilities = detector.run(None, {detector.get_inputs()[0].name: tensor})[0][0, 0]
    mask = (probabilities > 0.3).astype(np.uint8) * 255
    contours, _ = cv2.findContours(mask, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    boxes = []
    for contour in contours[:1000]:
        (cx, cy), (w, h), angle = cv2.minAreaRect(contour)
        if min(w, h) < 3:
            continue
        region = np.zeros_like(mask)
        cv2.drawContours(region, [contour], -1, 1, -1)
        if cv2.mean(probabilities, region)[0] < 0.5:
            continue
        # Expand the shrunken DB text contour to retain accents and punctuation.
        padding = w * h * 1.6 / (2 * (w + h))
        box = cv2.boxPoints(((cx, cy), (w + 2 * padding, h + 2 * padding), angle))
        box[:, 0] = np.clip(box[:, 0] * width / mask.shape[1], 0, width - 1)
        box[:, 1] = np.clip(box[:, 1] * height / mask.shape[0], 0, height - 1)
        # Order corners TL, TR, BR, BL for perspective correction.
        left, right = np.array_split(box[np.argsort(box[:, 0])], 2)
        left, right = left[np.argsort(left[:, 1])], right[np.argsort(right[:, 1])]
        boxes.append(np.asarray([left[0], right[0], right[1], left[1]], dtype=np.float32))
    return sorted(boxes, key=lambda b: (float(b[:, 1].min()), float(b[:, 0].min())))


def _crop_line(image, box):
    import cv2
    import numpy as np
    width = max(1, round(max(np.linalg.norm(box[0] - box[1]), np.linalg.norm(box[2] - box[3]))))
    height = max(1, round(max(np.linalg.norm(box[0] - box[3]), np.linalg.norm(box[1] - box[2]))))
    target = np.asarray([[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]], dtype=np.float32)
    transform = cv2.getPerspectiveTransform(box, target)
    return cv2.warpPerspective(image, transform, (width, height), borderMode=cv2.BORDER_REPLICATE)


@lru_cache(maxsize=2)
def _get_reader(weights, device, signature=None):
    return VietOCRReader(weights, device)


def model_signature(settings):
    signature = []
    for path in (settings.ocr_weights, settings.ocr_weights.parent / "ppocr_det.onnx"):
        try:
            info = path.stat()
            signature.append((info.st_size, info.st_mtime_ns))
        except OSError:
            signature.append(None)
    return tuple(signature)


def capabilities(settings):
    weights_ready = all(item is not None for item in model_signature(settings))
    dependencies_ready = all(importlib.util.find_spec(name) is not None
                             for name in ("vietocr", "torch", "torchvision", "cv2", "onnxruntime"))
    return {"backend": settings.ocr_backend, "model": "vgg_seq2seq", "device": settings.ocr_device,
            "weights_ready": weights_ready, "dependencies_ready": dependencies_ready,
            "configured": settings.ocr_backend == "vietocr" and weights_ready and dependencies_ready,
            "version": VERSION}


def _render_image(path, page_number, settings):
    # Reuse the same bounded Poppler renderer as the cloud vision path.
    from .extraction import _render_pages
    from PIL import Image
    image = _render_pages(path, [page_number], settings)[0]
    with Image.open(io.BytesIO(base64.b64decode(image["data_url"].split(",", 1)[1]))) as opened:
        return opened.convert("RGB")


def _layout_text(lines):
    rows = []
    for line in sorted(lines, key=lambda x: (sum(x["bbox"][1::2]) / 2, x["bbox"][0])):
        center = (line["bbox"][1] + line["bbox"][3]) / 2
        height = line["bbox"][3] - line["bbox"][1]
        if rows and abs(center - rows[-1][0]) < max(3, height * 0.5):
            rows[-1][1].append(line)
        else:
            rows.append((center, [line]))
    return "\n".join(" ".join(line["text"] for line in sorted(row, key=lambda x: x["bbox"][0]))
                     for _, row in rows)


def _apply_page_text(page, lines):
    text = _layout_text(lines)
    page.update(text=text, ocr_text=text, ocr_lines=lines, local_ocr_complete=True)
    header = next((line for line in lines if HEADERS["noi_nhan"].search(line["text"])), None)
    if header:
        top = header["bbox"][1] - 3
        signatures = [line["bbox"][0] for line in lines if line["bbox"][1] >= top
                      and line["bbox"][0] > page["width"] * 0.5 and SIGNATURE.match(line["text"])]
        right = max(page["width"] * 0.53, min(page["width"] * 0.58, min(signatures) - 6)) if signatures else page["width"] * 0.58
        page["recipient_bbox"] = [0, max(0, top), right, page["height"]]
        page["recipient_text"] = _layout_text([line for line in lines if line["bbox"][1] >= top
                                              and line["bbox"][0] < right
                                              and not (len(line["text"]) == 1 and line["confidence"] < 0.85)])


def ocr_missing_pages(path, pages, settings):
    started = time.monotonic()
    audit = {"backend": "vietocr", "version": VERSION, "model": "vgg_seq2seq", "pages": []}
    reasons = []
    # Serialize access to the cached GPU model; the async worker remains responsive.
    with _LOCK:
        try:
            reader = _get_reader(str(settings.ocr_weights.resolve()), settings.ocr_device, model_signature(settings))
            audit["device"] = reader.device
        except (ImportError, OSError) as error:
            audit["error_type"] = type(error).__name__
            reasons.append("local_ocr_unavailable")
        except Exception as error:
            audit["error_type"] = type(error).__name__
            reasons.append("local_ocr_failed")
        if not reasons:
            for page in pages:
                if page["text"].strip():
                    continue
                try:
                    image = _render_image(path, page["page"], settings)
                    lines = reader.read(image, settings.ocr_batch_size)
                    if not lines:
                        reasons.append("local_ocr_empty_page")
                        continue
                    # Convert renderer pixels to PDF points for layout/evidence.
                    for line in lines:
                        line["bbox"] = [float(v) * (page["width"] / image.width if i % 2 == 0 else page["height"] / image.height)
                                        for i, v in enumerate(line["bbox"])]
                    _apply_page_text(page, lines)
                    audit["pages"].append(page["page"])
                    if any(line["confidence"] < 0.85 for line in lines if len(line["text"]) > 2):
                        reasons.append("local_ocr_low_confidence")
                except Exception as error:
                    audit.setdefault("failed_pages", []).append({"page": page["page"], "error_type": type(error).__name__})
                    reasons.append("local_ocr_failed")
    audit["duration_ms"] = round((time.monotonic() - started) * 1000, 2)
    return audit, list(dict.fromkeys(reasons))


def _download_model(url, target, expected_sha256=None):
    import httpx
    if target.is_file():
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(".download")
    size = 0
    digest = hashlib.sha256()
    with httpx.stream("GET", url, follow_redirects=True, timeout=60) as response:
        response.raise_for_status()
        with temporary.open("wb") as stream:
            for chunk in response.iter_bytes():
                size += len(chunk)
                if size > 128 * 1024 * 1024:
                    raise ValueError("VietOCR model exceeds download limit")
                stream.write(chunk)
                digest.update(chunk)
    if size < 1024 * 1024:
        raise ValueError("VietOCR model download is incomplete")
    if expected_sha256 and digest.hexdigest() != expected_sha256:
        raise ValueError("OCR model checksum does not match the expected release")
    os.replace(temporary, target)
    return target


def prepare_weights(settings):
    """Explicit one-time downloads; no document data or credentials are sent."""
    _download_model(DETECTOR_URL, settings.ocr_weights.parent / "ppocr_det.onnx", DETECTOR_SHA256)
    return _download_model(WEIGHTS_URL, settings.ocr_weights)
