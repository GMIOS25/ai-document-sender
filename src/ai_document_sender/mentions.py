"""Conservative, evidence-preserving recipient parsing for the offline path.

Rules recover obvious tokens; they do not certify that every recipient was read.
Business aliases, staff assignments and membership belong to the resolver.
"""
import hashlib
import re
import unicodedata
from .contracts import Evidence, Mention

HEADERS = {"kinh_gui": re.compile(r"K\s*í\s*n\s*h\s+g\s*ử\s*i\s*[:：]", re.I), "noi_nhan": re.compile(r"N\s*ơ\s*i\s+n\s*h\s*ậ\s*n\s*[:：]", re.I)}
SIGNATURE = re.compile(r"^(?:(?:KT|TL|TM|TUQ)\s*\.|CHỦ TỊCH\b|PHÓ CHỦ TỊCH\b|PHÓ CHÁNH\b|CHÁNH VĂN\b)")
CODE = re.compile(r"(?<![\w])[TVNCX]\d{1,2}(?![\w])", re.I)
ROLE_START = re.compile(r"^(?:CT\b|CVP\b|PCT\b|PCTTT\b|PCVP\b|PVP\w*\b|Chủ tịch\b|Chánh Văn phòng\b|Phó Chủ tịch\b)", re.I)
GROUP = re.compile(r"\b(?:các|toàn bộ|lãnh đạo\s+VP\s*\+|lãnh đạo.*chuyên viên)\b", re.I)


def normalized(value: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", value)).strip()


def compact(value: str) -> str:
    return re.sub(r"[^\w]", "", normalized(value).casefold())


def stable_id(raw, kind, evidence, references=()):
    parts = [raw, kind, "|".join(f"{e.page}:{e.section}:{e.raw}" for e in evidence), "|".join(references)]
    return "m_" + hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()[:20]


def make_mention(raw, kind, page, section, evidence_raw=None, references=(), qualifier=None, quantifier=None, organization_scope=None):
    raw = normalized(raw).strip(" ;.")
    evidence = [Evidence(page=page, section=section, raw=normalized(evidence_raw or raw))]
    return Mention(mention_id=stable_id(raw, kind, evidence, references), raw=raw, kind=kind, evidence=evidence,
                   references=list(references), qualifier=qualifier, quantifier=quantifier, organization_scope=organization_scope)


def _entries(tail: str, section: str):
    """Read bullets and wrapped continuations, stopping at prose/signature."""
    entries, current = [], ""
    for index, line in enumerate(tail.splitlines()):
        line = normalized(line)
        if not line:
            if section == "kinh_gui" and current:
                entries.append(current)
                current = ""
                break
            continue
        # A two-column text layer can interleave the signature with recipients.
        if SIGNATURE.match(line):
            if current:
                entries.append(current)
                current = ""
            if section == "kinh_gui":
                break
            continue
        if section == "kinh_gui" and current and re.match(r"^(?:Thực hiện|Xét\s|Căn cứ|Tiếp theo|Để\s|Thay mặt|Trên cơ sở|Giao\s|Yêu cầu|UBND tỉnh nhận)", line, re.I):
            entries.append(current)
            current = ""
            break
        bullet = re.match(r"^[-–—•]\s*(.*)", line)
        if bullet:
            if current:
                entries.append(current)
            current = bullet.group(1)
            continue
        if not current and not entries:
            # Same-line Kính gửi: đơn vị; this is not a paragraph of the body.
            current = line
            if section == "kinh_gui" and re.search(r"[.;]$", current):
                entries.append(current)
                current = ""
                break
            continue
        if current and not re.search(r"[.;]$", current):
            current += " " + line
        else:
            if current:
                entries.append(current)
                current = ""
            break
    if current:
        entries.append(current)
    return [normalized(entry).strip(" ;.") for entry in entries if entry.strip(" ;.")]


def _split_recipient(entry, page, section, scope):
    output = []
    if re.match(r"Lưu\s*(?::|VT)", entry, re.I):
        tail = re.sub(r"^Lưu\s*:?\s*", "", entry, flags=re.I)
        for match in re.finditer(r"(?<!\w)(?:VT|[TVNCX]\d{1,2})(?!\w)", tail, re.I):
            token = match.group(0)
            output.append(make_mention(token, "archive_reference" if token.upper() == "VT" else "staff_code", page, "luu", entry, organization_scope=scope))
        # Preserve unfamiliar archive/routing codes instead of silently dropping them.
        residual = re.sub(r"(?<!\w)(?:VT|[TVNCX]\d{1,2})(?!\w)", "", tail, flags=re.I)
        residual = re.sub(r"\([^)]*\)", "", residual).strip(" ,.;")
        if residual:
            output.append(make_mention(residual, "unknown", page, "luu", entry, organization_scope=scope))
        return output

    if re.search(r"\b(?:mục|điều|khoản)\s+\d", entry, re.I):
        return [make_mention(entry, "reference", page, section, references=[entry], organization_scope=scope)]

    # Expand explicit enumerations but retain the parent phrase as evidence/context.
    batch = re.match(r"^(Các\s+[Ss]ở|[Ss]ở|UBND các xã|UBND các phường)\s*:\s*(.+)$", entry, re.I)
    if batch:
        qualifier = "Sở" if "sở" in batch.group(1).lower() else ("UBND xã" if "xã" in batch.group(1) else "UBND phường")
        values = re.sub(r"Văn\s+hóa,\s*Thể\s+thao\s+và\s+Du\s+lịch", lambda m: m.group(0).replace(",", "\x00"), batch.group(2), flags=re.I)
        for token in re.split(r",\s*", values):
            token = token.replace("\x00", ",")
            if token.strip():
                output.append(make_mention(token, "unit", page, section, entry, references=[entry], qualifier=qualifier, organization_scope=scope))
        return output

    if GROUP.search(entry):
        # Chủ tịch, các PCT are two selectors, not one bare PCT.
        if re.match(r"^(?:CT|Chủ tịch)\s*,", entry, re.I):
            first, second = entry.split(",", 1)
            return [make_mention(first, "role", page, section, entry, organization_scope=scope), make_mention(second, "group", page, section, entry, quantifier="all", organization_scope=scope)]
        return [make_mention(entry, "group", page, section, quantifier="all", organization_scope=scope)]

    if ROLE_START.match(entry) and "," in entry:
        return [make_mention(token, "role", page, section, entry, organization_scope=scope) for token in entry.split(",") if token.strip()]

    if re.match(r"PCT\b", entry, re.I) and re.search(r"\s+và\s+", entry, re.I):
        chunks = re.split(r"\s+và\s+", entry, flags=re.I)
        return [make_mention(token, "person", page, section, entry, qualifier="PCT", organization_scope=scope) for token in chunks]

    kind = "role" if ROLE_START.match(entry) or re.match(r"(?:Đ/c|Đồng chí)\b", entry, re.I) else "unit"
    return [make_mention(entry, kind, page, section, organization_scope=scope)]


def extract_rule_mentions(pages, metadata=None):
    from .article_references import expand_article_reference

    metadata = metadata.model_dump(mode="json") if hasattr(metadata, "model_dump") else (metadata or {})
    scope = metadata.get("issuer")
    sections, mentions, reasons, reference_pages = [], [], [], []
    for page in pages:
        text = unicodedata.normalize("NFC", page.get("text", ""))
        for section, pattern in HEADERS.items():
            source = page.get("recipient_text", text) if section == "noi_nhan" else text
            match = pattern.search(source)
            if not match:
                continue
            tail = source[match.end():]
            other = HEADERS["noi_nhan"].search(tail) if section == "kinh_gui" else None
            if other:
                tail = tail[:other.start()]
            entries = _entries(tail, section)
            sections.append(section)
            for entry in entries:
                if re.fullmatch(r"Như\s+trên", entry, re.I):
                    reference_pages.append(page["page"])
                    continue
                expanded = expand_article_reference(entry, page["page"], pages, scope) if section == "noi_nhan" else None
                parsed = expanded if expanded is not None else _split_recipient(entry, page["page"], section, scope)
                if any(m.kind == "reference" for m in parsed):
                    reasons.append("unsupported_reference")
                mentions.extend(parsed)
    if reference_pages:
        kinh_gui = [m for m in mentions if m.evidence[0].section == "kinh_gui"]
        if kinh_gui:
            for mention in kinh_gui:
                mention.references.append("Như trên")
                mention.mention_id = stable_id(mention.raw, mention.kind, mention.evidence, mention.references)
        else:
            reasons.append("unsupported_reference")
            mentions.append(make_mention("Như trên", "reference", reference_pages[0], "noi_nhan", references=["Kính gửi"]))
    if "noi_nhan" not in sections:
        reasons.append("recipient_sections_missing")
    # No recipient may be lost by overwriting a duplicate: retain all evidence.
    unique = {}
    for mention in mentions:
        unique.setdefault(mention.mention_id, mention)
    return list(unique.values()), list(dict.fromkeys(reasons))
