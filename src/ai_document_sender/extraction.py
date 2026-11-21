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
from .contracts import Evidence, Extraction, Mention
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


def _format_merged_row(row_words, sub_word_ids=()):
    ordered = sorted(row_words, key=lambda w: w["x0"])
    parts = []
    prev_x1 = None
    for w in ordered:
        txt = w["text"]
        if prev_x1 is not None:
            gap = w["x0"] - prev_x1
            is_sub_digit = id(w) in sub_word_ids and bool(re.fullmatch(r"\d{1,2}[.,;]?", txt))
            prev_prefix = bool(parts and re.search(r"(?:^|[\s,(/])[TVNCX]$", parts[-1]))
            # Glue subscript tokens tightly onto preceding token (e.g., N + 1 -> N1) or punctuation.
            if gap <= 1.2 or txt in {",", ".", ";", ":"} or (is_sub_digit and prev_prefix and gap <= 12.0):
                parts.append(txt)
            else:
                parts.append(" " + txt)
        else:
            parts.append(txt)
        prev_x1 = w["x1"]
    return "".join(parts)


def _merge_luu_subscripts(raw_text, words, max_x=None):
    """Merge PDF subscript tokens (e.g. N_1,4, X_5) dropped by y_tolerance onto the Lưu line."""
    if not raw_text or "Lưu" not in unicodedata.normalize("NFC", raw_text) or not words:
        return raw_text
    filtered = [w for w in words if max_x is None or w["x0"] < max_x]
    rows = []
    for w in sorted(filtered, key=lambda item: (round(item["top"], 1), item["x0"])):
        if rows and abs(w["top"] - rows[-1]["top"]) <= 3.0:
            rows[-1]["words"].append(w)
            rows[-1]["bottom"] = max(rows[-1]["bottom"], w["bottom"])
        else:
            rows.append({"top": w["top"], "bottom": w["bottom"], "height": w["bottom"] - w["top"], "words": [w]})
    merged_luu = []
    for idx, row in enumerate(rows):
        row_text = _format_merged_row(row["words"])
        if not re.search(r"Lưu\s*(?::|VT)", unicodedata.normalize("NFC", row_text), re.I):
            continue
        base_top = row["top"]
        base_bottom = row["bottom"]
        base_h = max(1.0, row["height"])
        sub_words = []
        sub_texts = set()
        for cand in rows[idx + 1:]:
            if cand["top"] - base_top > 8.0:
                break
            all_tiny = all(
                0.5 < w["top"] - base_top <= 8.0
                and abs(w["bottom"] - base_bottom) <= 2.6
                and (w["bottom"] - w["top"]) <= base_h * 0.88
                and not re.search(r"[a-zA-ZÀ-ỹ]{2,}", w["text"])
                for w in cand["words"]
            )
            if all_tiny:
                sub_words.extend(cand["words"])
                for w in cand["words"]:
                    sub_texts.add(w["text"].strip())
        if sub_words:
            merged_luu.append((_format_merged_row(row["words"] + sub_words, {id(w) for w in sub_words}), sub_texts))
    if not merged_luu:
        return raw_text
    lines = raw_text.splitlines()
    for merged_line, sub_texts in merged_luu:
        out_lines = []
        i = 0
        replaced = False
        while i < len(lines):
            cur = lines[i]
            cur_nfc = unicodedata.normalize("NFC", cur).strip()
            if not replaced and re.search(r"Lưu\s*(?::|VT)", cur_nfc, re.I):
                j = i + 1
                # Consume any adjacent lines made solely of split subscript/punctuation fragments.
                while j < len(lines):
                    nxt = unicodedata.normalize("NFC", lines[j]).strip()
                    if not nxt or len(nxt) > 25:
                        break
                    if re.search(r"[a-zA-ZÀ-ỹ]{2,}", nxt):
                        break
                    if re.fullmatch(r"[\d,.;\sTVNCX]+", nxt):
                        j += 1
                    else:
                        break
                if j > i + 1 or any(tok in cur for tok in sub_texts):
                    out_lines.append(merged_line)
                    i = j
                    replaced = True
                    continue
            out_lines.append(cur)
            i += 1
        lines = out_lines
    return "\n".join(lines)


def _has_interleaved_lines(raw_text: str) -> bool:
    return sum(
        1 for ln in raw_text.splitlines()
        if len(ln.strip()) == 1 and not ln.strip().isdigit() and ln.strip() not in {"-", "–", "—", "•"}
    ) >= 4


def _colon_compact(value: str) -> str:
    return re.sub(r"[^\w:]", "", normalized(value).replace("：", ":").casefold())


_PURPOSE_QUAL_RE = re.compile(
    r"\s*\((?:để\s+)?(?:b/c|báo\s+cáo|thay\s+(?:b/c|báo\s+cáo)|biết|thực\s+hiện|phối\s+hợp|p/h|t/h|để\s+biết|kèm\s+theo[^)]*)\)\s*$",
    re.I,
)
_LUU_LINE_RE = re.compile(r"Lưu\s*(?::|VT)", re.I)
_LUU_TOK = r"(?:[TVNCX]{1,2}\d{0,2}|VT|BTCD|PVHCC|TT\.?PVHCC|KSTT|HSVV(?:-TD)?|HCTC|HCQT|QTTV|P\.?\s*QT-?TV|P\.?QTTV|XDCT|NNMT|KTTH|KGVX|NC|LĐVP|CVP|PVP\w*|\d{1,2})"
_LUU_CONT_RE = re.compile(
    rf"[\s,.;()/\-]+|(?:[\s,.;()/\-]*{_LUU_TOK}(?:[\s,;().\-/]+{_LUU_TOK})*[\s,.;()]*)",
    re.I,
)


def _deduplicate_mentions(model_mentions: list[Mention], rules: list[Mention]) -> list[Mention]:
    def _keys(mention: Mention) -> set[str]:
        stripped_luu = re.sub(r"^Lưu\s*[:：]?\s*", "", mention.raw, flags=re.I)
        stripped_qual = _PURPOSE_QUAL_RE.sub("", mention.raw).strip()
        full_prefix = " ".join(filter(None, (mention.qualifier, mention.raw)))
        full_suffix = " ".join(filter(None, (mention.raw, mention.qualifier)))
        return {
            compact(mention.raw),
            compact(stripped_luu),
            compact(stripped_qual),
            compact(full_prefix),
            compact(full_suffix),
        } - {""}

    has_resolved_nhu_tren = any(compact(ref) == "nhưtrên" for r in rules for ref in r.references)
    filtered_model: list[Mention] = []
    for item in model_mentions:
        if has_resolved_nhu_tren and compact(item.raw) == "nhưtrên":
            continue
        sections = {e.section for e in item.evidence}
        item_keys = _keys(item)
        same_section_rules = [r for r in rules if sections & {e.section for e in r.evidence}]
        if any(item_keys & _keys(r) for r in same_section_rules):
            continue
        item_compact = compact(item.raw)
        if ("," in item.raw or ";" in item.raw) and sum(
            1 for r in same_section_rules
            if compact(r.raw) and compact(r.raw) != item_compact and compact(r.raw) in item_compact
        ) >= 2:
            continue
        filtered_model.append(item)
    unique = {mention.mention_id: mention for mention in filtered_model + rules}
    return list(unique.values())


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
                words = page.extract_words(x_tolerance=2, y_tolerance=3)
                raw_page = page.extract_text(x_tolerance=2, y_tolerance=3) or ""
                if _has_interleaved_lines(raw_page):
                    words = page.extract_words(x_tolerance=2, y_tolerance=1)
                    raw_page = page.extract_text(x_tolerance=2, y_tolerance=1) or ""
                text = _merge_luu_subscripts(raw_page, words, max_x=page.width * 0.55)
                record = {"page": index, "text": text, "width": page.width, "height": page.height,
                          "images": [{"bbox": [image.get("x0", 0), image.get("top", 0), image.get("x1", page.width), image.get("bottom", page.height)]} for image in page.images]}
                # Extract the left recipient column without interleaved signature headings.
                headers = [word for word in words if unicodedata.normalize("NFC", word["text"]).casefold() == "nơi"]
                for header in headers:
                    following = sorted((word for word in words if abs(word["top"]-header["top"]) < 5 and word["x0"] > header["x0"]), key=lambda word: word["x0"])
                    header_probe = unicodedata.normalize("NFC", header["text"]+" "+" ".join(word["text"] for word in following[:4]))
                    if not following or not HEADERS["noi_nhan"].search(header_probe):
                        continue
                    top = max(0, header["top"]-3)
                    sig_words = [word for word in words if word["top"] >= top and word["x0"] > page.width*0.5 and re.fullmatch(r"(?:TL\.|KT\.|TM\.|TUQ\.|CHỦ|PHÓ|CHÁNH|Q\.)", word["text"])]
                    if sig_words:
                        sig_top = min(word["top"] for word in sig_words)
                        sig_left = min(word["x0"] for word in sig_words)
                        # Include indented signer names under the right signature column while skipping wide left-to-right footnotes.
                        sig_block = [
                            word["x0"] for word in words
                            if sig_top <= word["top"] <= sig_top + 160
                            and sig_left - 45 <= word["x0"] and word["x0"] > page.width * 0.53
                            and not any(abs(other["top"] - word["top"]) < 5 and word["x0"] - 60 <= other["x1"] < word["x0"] for other in words)
                        ]
                        right = min(sig_block or [sig_left]) - 6
                    else:
                        right = page.width
                    right = max(page.width*0.53, right)
                    bbox = [0, top, min(page.width, right), page.height]
                    record["recipient_bbox"] = bbox
                    cropped = page.crop(tuple(bbox))
                    cropped_words = cropped.extract_words(x_tolerance=2, y_tolerance=3)
                    raw_cropped = cropped.extract_text(x_tolerance=2, y_tolerance=3) or ""
                    if _has_interleaved_lines(raw_cropped):
                        cropped_words = cropped.extract_words(x_tolerance=2, y_tolerance=1)
                        raw_cropped = cropped.extract_text(x_tolerance=2, y_tolerance=1) or ""
                    record["recipient_text"] = _merge_luu_subscripts(raw_cropped, cropped_words)
                    break
                if not text.strip() and not page.images and not page.curves and not page.rects and len(page.lines) < 3:
                    record["blank"] = True
                pages.append(record)
            if pages and all(item.get("blank") for item in pages):
                pages[0].pop("blank", None)
        return pages
    except ExtractionError:
        raise
    except Exception:
        raise ExtractionError("invalid_pdf", "PDF could not be decoded") from None


def select_vision_pages(pages, limit=6):
    required = []
    low_conf_secondary = []
    reasons = []
    last_page_num = pages[-1]["page"] if pages else 0
    for idx, page in enumerate(pages):
        if page.get("blank"):
            continue
        low_conf = bool(page.get("local_ocr_low_confidence"))
        if page.get("local_ocr_complete") and not low_conf:
            continue
        text = unicodedata.normalize("NFC", page.get("text", ""))
        recipient = unicodedata.normalize("NFC", page.get("recipient_text") or text)
        header = HEADERS["noi_nhan"].search(recipient)
        width, height = page.get("width", 595), page.get("height", 842)
        region_top = page.get("recipient_bbox", [0, height*0.55, width*0.65, height])[1]
        region_right = page.get("recipient_bbox", [0, region_top, width*0.65, height])[2]
        left_image = any(min(image.get("bbox", [0,0,0,0])[2], region_right)-max(image.get("bbox", [0,0,0,0])[0], 0) > width*0.20 and image.get("bbox", [0,0,0,0])[3] > region_top and image.get("bbox", [0,0,0,0])[3]-image.get("bbox", [0,0,0,0])[1] > 45 for image in page.get("images", []))
        broken = len(text.strip()) < 40 or text.count("\ufffd") > max(2, len(text)*0.02)
        empty_region = bool(header) and not _entries(recipient[header.end():], "noi_nhan")
        is_recipient_or_boundary = bool(header or HEADERS["kinh_gui"].search(text) or idx == 0 or page["page"] == last_page_num)
        if broken or empty_region or left_image or (low_conf and is_recipient_or_boundary):
            required.append(page["page"])
        elif low_conf:
            low_conf_secondary.append(page["page"])
    all_text = "\n".join(unicodedata.normalize("NFC", page.get("text", "")) for page in pages)
    if pages and (not pages[-1].get("local_ocr_complete") or pages[-1].get("local_ocr_low_confidence")) and not HEADERS["noi_nhan"].search(all_text):
        required.append(pages[-1]["page"])
    if pages and (not pages[0].get("local_ocr_complete") or pages[0].get("local_ocr_low_confidence")) and re.search(r"Như\s+trên", all_text, re.I) and not HEADERS["kinh_gui"].search(all_text):
        required.append(pages[0]["page"])
    required.extend(low_conf_secondary)
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


def _luu_lines(text):
    from .mentions import SIGNATURE

    blocks, current = [], ""
    for raw_line in unicodedata.normalize("NFC", text or "").splitlines():
        line = normalized(raw_line)
        if not line:
            if current:
                blocks.append(current)
                current = ""
            continue
        if _LUU_LINE_RE.search(line):
            if current:
                blocks.append(current)
            current = line
            continue
        if current:
            if SIGNATURE.match(line) or re.match(r"^\d+\s+\S", line):
                blocks.append(current)
                current = ""
                continue
            if current.rstrip().endswith((",", ";", "/")) or _LUU_CONT_RE.fullmatch(line):
                current += " " + line
                continue
            blocks.append(current)
            current = ""
    if current:
        blocks.append(current)
    return blocks


def _has_signature_bleed(tail: str) -> bool:
    from .mentions import SIGNATURE

    for line in unicodedata.normalize("NFC", tail or "").splitlines():
        s = normalized(line)
        if not s:
            continue
        if SIGNATURE.match(s) or re.search(
            r";\s*(?:[-–—•]\s*)?(?:KT|TL|TM|T\s*M|TUQ|PH[OÓ]\s+CH[ỦU]\s+T[ỊI]CH|CH[ỦU]\s+T[ỊI]CH|CH[ÁA]NH\s+V[ĂA]N)\b",
            s,
            re.I,
        ):
            return True
    return False


def _extract_clean_noi_nhan_tail(trans_nfc: str) -> str:
    from .mentions import SIGNATURE

    match = HEADERS["noi_nhan"].search(trans_nfc)
    if not match:
        return ""
    lines = []
    for raw_line in trans_nfc[match.start():].splitlines():
        s = normalized(raw_line)
        if lines and s and SIGNATURE.match(s):
            break
        lines.append(raw_line)
    return "\n".join(lines).strip()


def _recipient_crop_is_clean(page) -> bool:
    recipient = unicodedata.normalize("NFC", page.get("recipient_text") or "")
    header = HEADERS["noi_nhan"].search(recipient)
    if not header or not _entries(recipient[header.end():], "noi_nhan") or "\ufffd" in recipient:
        return False
    if _has_signature_bleed(recipient[header.end():]):
        return False
    ocr_lines = page.get("ocr_lines")
    rbbox = page.get("recipient_bbox")
    if isinstance(ocr_lines, list) and rbbox and len(rbbox) == 4:
        in_crop = [
            ln for ln in ocr_lines
            if isinstance(ln, dict) and ln.get("bbox") and ln.get("confidence") is not None
            and len(ln.get("text", "").strip()) > 2
            and ln["bbox"][1] >= rbbox[1] - 2 and ln["bbox"][0] < rbbox[2] + 2
        ]
        if not in_crop or any(float(ln["confidence"]) < 0.80 for ln in in_crop):
            return False
        return True
    return not page.get("local_ocr_low_confidence")


def _section_source(page, section):
    if section == "luu":
        parts = []
        for src in (page.get("recipient_text"), page.get("text")):
            if src:
                parts.extend(_luu_lines(src))
        return "\n".join(dict.fromkeys(parts))
    text = unicodedata.normalize("NFC", (page.get("recipient_text") or page.get("text", "")) if section == "noi_nhan" else page.get("text", ""))
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
    accepted_ocr_pages = set()
    for transcription in payload.ocr_pages:
        if (
            transcription.page not in image_pages
            or not transcription.text.strip()
            or re.search(r"[\u4e00-\u9fff]|\bUnauthorized\b", transcription.text)
        ):
            reasons.append("ungrounded_ocr_page")
            continue
        accepted_ocr_pages.add(transcription.page)
        page = by_page[transcription.page]
        trans_nfc = unicodedata.normalize("NFC", transcription.text)
        clean_crop = _recipient_crop_is_clean(page)
        trans_nn_clean = _extract_clean_noi_nhan_tail(trans_nfc)
        trans_has_bleed = bool((m := HEADERS["noi_nhan"].search(trans_nfc)) and _has_signature_bleed(trans_nfc[m.end():]))
        if page.get("local_ocr_low_confidence"):
            orig_nfc = unicodedata.normalize("NFC", page.get("text", ""))
            body_match = re.search(r"(?m)^\s*(?:Điều\s+\d+|DANH\s+SÁCH|PHỤ\s+LỤC|\d+\.\s+\S+.*:)", orig_nfc, re.I)
            trans_has_body = bool(re.search(r"(?m)^\s*(?:Điều\s+\d+|DANH\s+SÁCH|PHỤ\s+LỤC|\d+\.\s+\S+.*:)", trans_nfc, re.I))
            if (HEADERS["kinh_gui"].search(trans_nfc) or not HEADERS["kinh_gui"].search(orig_nfc)) and (not body_match or trans_has_body):
                page["text"] = transcription.text
            elif HEADERS["kinh_gui"].search(trans_nfc) and body_match:
                page["text"] = transcription.text + "\n" + orig_nfc[body_match.start():]
            else:
                page["text"] += "\n" + transcription.text
            if trans_nn_clean and not clean_crop and not trans_has_bleed:
                page["recipient_text"] = trans_nn_clean
            elif HEADERS["noi_nhan"].search(trans_nfc) and not clean_crop and not trans_has_bleed:
                page["recipient_text"] = trans_nn_clean or transcription.text
        else:
            page["text"] += "\n" + transcription.text
            if HEADERS["noi_nhan"].search(trans_nfc) and not clean_crop and not trans_has_bleed:
                page["recipient_text"] = trans_nn_clean or transcription.text
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
        grounded_evidence = []
        for evidence in item.evidence:
            page = by_page.get(evidence.page)
            source = _section_source(page, evidence.section) if page else ""
            ev_body = re.sub(r"^\s*(?:Kính\s+gửi|Nơi\s+nhận)\s*[:：.]?\s*", "", normalized(evidence.raw), flags=re.I)
            if (
                not source
                or compact(ev_body) not in compact(source)
                or compact(item.raw) not in compact(ev_body)
                or (
                    ":" not in item.raw
                    and "：" not in item.raw
                    and (
                        compact(item.raw) not in _colon_compact(ev_body)
                        or compact(item.raw) not in _colon_compact(source)
                    )
                )
            ):
                valid = False
            # Model offsets are untrusted. Only retain exact source positions.
            if page and evidence.raw in page["text"]:
                start = page["text"].index(evidence.raw)
                span = [start, start+len(evidence.raw)]
            else:
                span = None
            grounded_evidence.append(Evidence(page=evidence.page, section=evidence.section, raw=evidence.raw, span=span, bbox=None))
        if not valid:
            reasons.append("ungrounded_model_mention")
            continue
        data = item.model_dump(exclude={"evidence"})
        output.append(Mention(mention_id=stable_id(item.raw, item.kind, grounded_evidence, item.references), evidence=grounded_evidence, **data))
    if image_pages - accepted_ocr_pages:
        reasons.append("unreadable_region")
    return output, list(dict.fromkeys(reasons))


async def extract_document(path, provider, metadata, settings):
    started = time.monotonic()
    pages = await asyncio.to_thread(_read_pages, path, settings)
    local_audit, local_reasons = None, []
    missing_text = {page["page"] for page in pages if not page["text"].strip() and not page.get("blank")}
    if settings.ocr_backend == "vietocr" and missing_text:
        local_audit, local_reasons = await asyncio.to_thread(ocr_missing_pages, path, pages, settings)
    rules, rule_reasons = extract_rule_mentions(pages, metadata)
    chosen, vision_reasons = select_vision_pages(pages, settings.max_vision_pages)
    if settings.ocr_backend == "vietocr":
        low_conf_pages = {page["page"] for page in pages if page.get("local_ocr_low_confidence")}
        # Explicit local OCR never silently falls back to cloud OCR on engine failure,
        # but low-confidence scanned pages escalate to Vision LLM (hybrid mode).
        blocked = missing_text - low_conf_pages
        if blocked.intersection(chosen):
            local_reasons.append("unreadable_region")
        chosen = [page for page in chosen if page not in blocked]
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
        reasons += grounding_reasons + rule_reasons + payload.review_reasons
        if not model_mentions:
            reasons.append("invalid_model_output" if rules else "recipient_sections_missing")
        if payload.status != "complete":
            reasons.append("model_extraction_partial" if payload.status == "partial" else "model_extraction_failed")
        # A complete model cannot certify a recipient reference it never explained.
        audit.update({"provider_used": True, "provider": getattr(provider, "last_audit", {}), "vision_pages_rendered": [image["page"] for image in images]})
        mentions = _deduplicate_mentions(model_mentions, rules)
    except ProviderError as error:
        mentions = rules
        reasons += rule_reasons + [error.code]
        if chosen:
            reasons.append("unreadable_region")
        if getattr(provider, "last_audit", None):
            audit["provider"] = provider.last_audit
    except (ValidationError, ValueError, TypeError):
        mentions = rules
        reasons += rule_reasons + ["invalid_model_output"]
        if chosen:
            reasons.append("unreadable_region")
        if getattr(provider, "last_audit", None):
            audit["provider"] = provider.last_audit
    # Missing structural sections need review even if a provider claims complete.
    reasons = list(dict.fromkeys(reasons))
    audit["duration_ms"] = round((time.monotonic()-started)*1000, 2)
    return Extraction(mentions=mentions, status="partial" if reasons else "complete", review_reasons=reasons, pages=pages, audit=audit)
