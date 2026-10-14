"""Layout-aware PDF extraction with bounded vision and grounded mentions."""
import asyncio
import base64
import io
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time
import unicodedata
import pdfplumber
from pypdf import PdfReader
from pydantic import ValidationError
from .contracts import Extraction, Mention
from .mentions import HEADERS, _entries, compact, extract_rule_mentions, normalized, stable_id
from .article_references import reference_target
from .provider import GeneratedExtraction, ProviderError, PROMPT_VERSION
from .ocr import ocr_missing_pages

VERSION = "pdf-local-ocr-v6"
EXTRACTOR_VERSION = VERSION


class ExtractionError(RuntimeError):
    def __init__(self, code, message):
        self.code = code
        super().__init__(message)


def _read_pages(path, settings):
    filename = str(Path(path).resolve())
    if os.name == "nt" and not filename.startswith("\\\\?\\"):
        filename = "\\\\?\\" + filename
    try:
        with open(filename, "rb") as stream:
            data = stream.read(settings.max_file_bytes + 1)
        if len(data) > settings.max_file_bytes:
            raise ExtractionError("file_too_large", "PDF exceeds configured byte limit")
        if not data.startswith(b"%PDF-"):
            raise ExtractionError("invalid_pdf", "Uploaded document is not a PDF")
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            raise ExtractionError("encrypted_pdf", "Encrypted PDF cannot be extracted")
        if not 0 < len(reader.pages) <= settings.max_pages:
            raise ExtractionError("page_limit", "PDF page count exceeds configured limit")
        pages = []
        with pdfplumber.open(io.BytesIO(data)) as document:
            for index, page in enumerate(document.pages, 1):
                text = page.extract_text(x_tolerance=2, y_tolerance=3) or ""
                record = {"page": index, "text": text, "width": page.width, "height": page.height,
                          "images": [{"bbox": [image.get("x0", 0), image.get("top", 0), image.get("x1", page.width), image.get("bottom", page.height)]} for image in page.images]}
                # Extract the left recipient column without interleaved signature headings.
                words = page.extract_words(x_tolerance=2, y_tolerance=3)
                headers = [word for word in words if unicodedata.normalize("NFC", word["text"]).casefold() == "nơi"]
                for header in headers:
                    following = sorted((word for word in words if abs(word["top"]-header["top"]) < 5 and word["x0"] > header["x0"]), key=lambda word: word["x0"])
                    if not following or not HEADERS["noi_nhan"].search(header["text"]+" "+" ".join(word["text"] for word in following[:4])):
                        continue
                    top = max(0, header["top"]-3)
                    signature = [word["x0"] for word in words if word["top"] >= top and word["x0"] > page.width*0.5 and re.fullmatch(r"(?:TL\.|KT\.|TM\.|CHỦ|PHÓ)", word["text"])]
                    right = min(signature)-6 if signature else page.width
                    right = max(page.width*0.53, right)
                    bbox = [0, top, min(page.width, right), page.height]
                    record["recipient_bbox"] = bbox
                    record["recipient_text"] = page.crop(tuple(bbox)).extract_text(x_tolerance=2, y_tolerance=3) or ""
                    break
                pages.append(record)
        return pages
    except ExtractionError:
        raise
    except Exception:
        raise ExtractionError("invalid_pdf", "PDF could not be decoded") from None


def select_vision_pages(pages, limit=6):
    required = []
    reasons = []
    for page in pages:
        if page.get("local_ocr_complete"):
            continue
        text = unicodedata.normalize("NFC", page.get("text", ""))
        recipient = unicodedata.normalize("NFC", page.get("recipient_text", text))
        header = HEADERS["noi_nhan"].search(recipient)
        width, height = page.get("width", 595), page.get("height", 842)
        region_top = page.get("recipient_bbox", [0, height*0.55, width*0.65, height])[1]
        region_right = page.get("recipient_bbox", [0, region_top, width*0.65, height])[2]
        left_image = any(min(image.get("bbox", [0,0,0,0])[2], region_right)-max(image.get("bbox", [0,0,0,0])[0], 0) > width*0.20 and image.get("bbox", [0,0,0,0])[3] > region_top and image.get("bbox", [0,0,0,0])[3]-image.get("bbox", [0,0,0,0])[1] > 45 for image in page.get("images", []))
        broken = len(text.strip()) < 40 or text.count("\ufffd") > max(2, len(text)*0.02)
        empty_region = bool(header) and not _entries(recipient[header.end():], "noi_nhan")
        if broken or empty_region or left_image:
            required.append(page["page"])
    all_text = "\n".join(unicodedata.normalize("NFC", page.get("text", "")) for page in pages)
    if pages and not pages[-1].get("local_ocr_complete") and not HEADERS["noi_nhan"].search(all_text):
        required.append(pages[-1]["page"])
    if pages and not pages[0].get("local_ocr_complete") and re.search(r"Như\s+trên", all_text, re.I) and not HEADERS["kinh_gui"].search(all_text):
        required.append(pages[0]["page"])
    required = list(dict.fromkeys(required))
    if len(required) > limit:
        reasons.append("vision_page_limit")
    return required[:max(0, limit)], reasons


def _render_pages(path, page_numbers, settings):
    executable = settings.poppler_path
    if executable and Path(executable).is_dir():
        executable = str(Path(executable)/("pdftoppm.exe" if os.name == "nt" else "pdftoppm"))
    executable = executable or shutil.which("pdftoppm")
    if not executable:
        raise ExtractionError("renderer_unavailable", "Poppler pdftoppm is not configured")
    settings.runtime_dir.mkdir(parents=True, exist_ok=True)
    images = []
    with tempfile.TemporaryDirectory(prefix="vision-", dir=settings.runtime_dir) as tmp:
        for page in page_numbers:
            target = Path(tmp)/f"page-{page}"
            # Native subprocess arguments, no shell; documents cannot inject commands.
            subprocess.run([str(executable), "-f", str(page), "-l", str(page), "-singlefile", "-scale-to", "2000", "-png", str(Path(path).resolve()), str(target)], check=True, timeout=min(30, max(1, settings.provider_timeout_seconds)), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            content = target.with_suffix(".png").read_bytes()
            images.append({"page": page, "data_url": "data:image/png;base64,"+base64.b64encode(content).decode("ascii")})
    return images


def _section_source(page, section):
    text = unicodedata.normalize("NFC", page.get("recipient_text", page.get("text", "")) if section == "noi_nhan" else page.get("text", ""))
    if section == "luu":
        return "\n".join(line for line in text.splitlines() if re.search(r"Lưu\s*(?::|VT)", line, re.I))
    if section in HEADERS:
        match = HEADERS[section].search(text)
        if not match:
            return ""
        tail = text[match.end():]
        if section == "kinh_gui":
            other = HEADERS["noi_nhan"].search(tail)
            if other:
                tail = tail[:other.start()]
        return "\n".join(_entries(tail, section))
    # Body evidence is checked against verified article subjects in _ground_model.
    return ""


def _ground_model(payload, pages, images):
    output, reasons = [], []
    by_page = {page["page"]: page for page in pages}
    image_pages = {image["page"] for image in images}
    for transcription in payload.ocr_pages:
        if transcription.page not in image_pages or not transcription.text.strip():
            reasons.append("ungrounded_ocr_page")
            continue
        page = by_page[transcription.page]
        page["text"] += "\n" + transcription.text
        recipient = unicodedata.normalize("NFC", page.get("recipient_text", ""))
        header = HEADERS["noi_nhan"].search(recipient)
        clean_column = header and _entries(recipient[header.end():], "noi_nhan") and "\ufffd" not in recipient
        # Whole-page OCR supplies article/list bodies; retain a readable layout crop.
        if HEADERS["noi_nhan"].search(unicodedata.normalize("NFC", transcription.text)) and not clean_column:
            page["recipient_text"] = transcription.text
        page["ocr_text"] = transcription.text
    rules, _ = extract_rule_mentions(pages)
    linked = [m for m in rules if any(e.section == "body_reference" for e in m.evidence) and m.kind != "reference"]
    for item in payload.mentions:
        body_evidence = [e for e in item.evidence if e.section == "body_reference"]
        # The rules expand these routing links; they are never recipient names.
        if reference_target(normalized(item.raw).strip(" -–—•;.")) is not None:
            continue
        if not body_evidence and any(e.section == "noi_nhan" and reference_target(e.raw.strip(" -–—•")) is not None for e in item.evidence):
            continue
        if body_evidence:
            candidates = [m for m in linked if item.kind == m.kind
                          and compact(item.raw) in {compact(m.raw), compact(" ".join(filter(None, (m.qualifier, m.raw))))}
                          and any(compact(ref) == compact(m.references[0]) for ref in item.references)]
            verified = next((m for m in candidates if all(
                any(e.page == source.page and compact(e.raw) in compact(source.raw)
                    for source in m.evidence if source.section == "body_reference")
                for e in body_evidence)), None)
            other_valid = all(
                e.page in by_page and compact(e.raw) in compact(_section_source(by_page[e.page], e.section))
                for e in item.evidence if e.section != "body_reference"
            )
            if (verified is None or not other_valid
                    or compact(verified.raw) not in compact(" ".join(e.raw for e in body_evidence))):
                reasons.extend(["unsupported_reference", "ungrounded_model_mention"])
                continue
            # Preserve the complete verified chain, including the Nơi nhận link.
            output.append(verified.model_copy(deep=True))
            continue
        valid = True
        for evidence in item.evidence:
            page = by_page.get(evidence.page)
            source = _section_source(page, evidence.section) if page else ""
            if not source or compact(evidence.raw) not in compact(source) or compact(item.raw) not in compact(evidence.raw):
                valid = False
            # Model offsets are untrusted. Only retain exact source positions.
            if page and evidence.raw in page["text"]:
                start = page["text"].index(evidence.raw)
                evidence.span = [start, start+len(evidence.raw)]
            else:
                evidence.span = None
            evidence.bbox = None
        if not valid:
            reasons.append("ungrounded_model_mention")
            continue
        data = item.model_dump()
        output.append(Mention(mention_id=stable_id(item.raw, item.kind, item.evidence, item.references), **data))
    if image_pages - {item.page for item in payload.ocr_pages if item.text.strip() and item.page in image_pages}:
        reasons.append("unreadable_region")
    return output, list(dict.fromkeys(reasons))


async def extract_document(path, provider, metadata, settings):
    started = time.monotonic()
    pages = await asyncio.to_thread(_read_pages, path, settings)
    local_audit, local_reasons = None, []
    missing_text = {page["page"] for page in pages if not page["text"].strip()}
    if settings.ocr_backend == "vietocr" and missing_text:
        local_audit, local_reasons = await asyncio.to_thread(ocr_missing_pages, path, pages, settings)
    rules, rule_reasons = extract_rule_mentions(pages, metadata)
    chosen, vision_reasons = select_vision_pages(pages, settings.max_vision_pages)
    if settings.ocr_backend == "vietocr":
        # Explicit local OCR never silently falls back to slow cloud OCR on failure.
        if missing_text.intersection(chosen):
            local_reasons.append("unreadable_region")
        chosen = [page for page in chosen if page not in missing_text]
    audit = {"extractor_version": VERSION, "prompt_version": PROMPT_VERSION, "vision_pages_requested": chosen, "provider_used": False}
    if local_audit is not None:
        audit["local_ocr"] = local_audit
    if provider is None or getattr(provider, "available", True) is False:
        reasons = rule_reasons + vision_reasons + local_reasons + ["provider_unavailable"]
        if chosen:
            reasons.append("unreadable_region")
        audit["duration_ms"] = round((time.monotonic()-started)*1000, 2)
        return Extraction(mentions=rules, status="partial", review_reasons=list(dict.fromkeys(reasons)), pages=pages, audit=audit)
    images, reasons = [], list(vision_reasons) + local_reasons
    if chosen:
        try:
            images = await asyncio.to_thread(_render_pages, path, chosen, settings)
        except Exception:
            reasons.extend(["renderer_unavailable", "unreadable_region"])
    try:
        raw = await provider.extract_mentions(pages, metadata, images=images or None)
        payload = GeneratedExtraction.model_validate(raw)
        model_mentions, grounding_reasons = _ground_model(payload, pages, images)
        # Include clear rule tokens the model might omit; all retain source evidence.
        rules, rule_reasons = extract_rule_mentions(pages, metadata)
        unique = {mention.mention_id: mention for mention in model_mentions+rules}
        reasons += grounding_reasons + rule_reasons + payload.review_reasons
        if not model_mentions:
            reasons.append("invalid_model_output" if rules else "recipient_sections_missing")
        if payload.status != "complete":
            reasons.append("model_extraction_partial" if payload.status == "partial" else "model_extraction_failed")
        # A complete model cannot certify a recipient reference it never explained.
        audit.update({"provider_used": True, "provider": getattr(provider, "last_audit", {}), "vision_pages_rendered": [image["page"] for image in images]})
        mentions = list(unique.values())
    except ProviderError as error:
        mentions = rules
        reasons += rule_reasons + [error.code]
        if chosen:
            reasons.append("unreadable_region")
    except (ValidationError, ValueError, TypeError):
        mentions = rules
        reasons += rule_reasons + ["invalid_model_output"]
        if chosen:
            reasons.append("unreadable_region")
    # Missing structural sections need review even if a provider claims complete.
    reasons = list(dict.fromkeys(reasons))
    audit["duration_ms"] = round((time.monotonic()-started)*1000, 2)
    return Extraction(mentions=mentions, status="partial" if reasons else "complete", review_reasons=reasons, pages=pages, audit=audit)
