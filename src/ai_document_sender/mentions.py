"""Conservative, evidence-preserving recipient parsing for the offline path.

Rules recover obvious tokens; they do not certify that every recipient was read.
Business aliases, staff assignments and membership belong to the resolver.
"""
import hashlib
import re
import unicodedata
from .contracts import Evidence, Mention

HEADERS = {
    "kinh_gui": re.compile(r"(?:K\s*í\s*n\s*h\s+g\s*[ửở]\s*i\s*[:：]|^\s*K\s*í\s*n\s*h\s+g\s*[ửở]\s*i\s*$)", re.I | re.M),
    "noi_nhan": re.compile(r"N\s*ơ\s*i\s+n\s*h\s*ậ\s*n\s*[:：]", re.I),
}
SIGNATURE = re.compile(r"^(?:(?:KT|TL|TM|T\s*M|TUQ)(?:\s*\.|\s*$)|CHỦ TỊCH\b|PHÓ CHỦ TỊCH\b|PHÓ CHÁNH\b|CHÁNH VĂN\b)")
KINH_GUI_PROSE = re.compile(
    r"^(?:Thực hiện|Xét\s|Căn cứ|Tiếp theo|Tiếp tục\s|Tiếp nối\s|Để\s|Thay mặt|Trên cơ sở|"
    r"Giao\s+(?!thông\b)|Yêu cầu|Tôi\s+tên\s*[:：]|Tôi\s+là\b|UBND tỉnh\s+(?:nhận|tiếp tục|trân trọng|kính|có\s|đã\s|đề nghị)|"
    r"Ủy ban nhân dân\s+(?:tỉnh|thành phố)\b.*\b(?:nhận|trân trọng|kính|báo cáo|có ý kiến|tiếp tục|đã|đang|đề nghị|phúc đáp|gửi|chỉ đạo|thống nhất)\b|"
    r"Theo\s|Nhằm\s|Về\s|Ngày\s|Kính\s|Nội dung|Sau khi\s|Phúc đáp\b|Thưa\s|Trong thời gian\b|"
    r"Thời gian\s+(?:qua|tới|gần đây)\b|Được sự\s|"
    r"Qua\s+(?:rà soát|nghiên cứu|kiểm tra|theo dõi|báo cáo)\b|Hiện nay\b|Triển khai\s|Vừa qua\b|Trân trọng\b|Nhận được\b|"
    r"(?:\d+|[IVXLCDM]+)\.\s)",
    re.I,
)
SENTENCE_BODY_CUES = re.compile(
    r"\b(?:là một|được sự|đã\s+\w+|đang\s+\w+|có ý kiến|trân trọng|nhận được|về việc\b.*\bngày\s+\d|"
    r"(?:công văn|văn bản|tờ trình|nghị định|quyết định|kế hoạch|thông báo|báo cáo)\s+số)\b",
    re.I,
)
CODE = re.compile(r"(?<![\w])[TVNCX]\d{1,2}(?![\w])", re.I)
ROLE_START = re.compile(r"^(?:CT\b|CVP\b|PCT\b|PCTTT\b|PCVP\b|PVP\w*\b|Chủ tịch\b|Chánh Văn phòng\b|Phó Chủ tịch\b)", re.I)
GROUP = re.compile(r"\b(?:các|toàn bộ|lãnh đạo\s+VP\s*\+|lãnh đạo.*chuyên viên)\b", re.I)
SINGLE_UNIT_CAC = re.compile(r"^(?:Ban\s+(?:Quản\s+lý|QL)(?:\s+dự\s+án)?|BQL)\s+(?:dự\s+án\s+)?các\b", re.I)
BODY_LIST_HEADING = re.compile(r"(?im)^[ \t]*(?:[-–—•][ \t]*)?(?:[A-ZĐ]{1,12}[ \t]+){0,2}(?:DANH SÁCH|PHỤ LỤC(?:[ \t]+\d+)?)\b")
BODY_TASK_HEAD = re.compile(r"(?m)^[ \t]*(\d+)\.[ \t]+([^\n:;]{2,120}(?::[ \t]+[^\n:;]{2,120})?):(?:\s|$)")
BODY_TASK_UNIT = re.compile(
    r"^(?:Đề nghị\s+)?(?:(?:Giám đốc|Thủ trưởng|Chủ tịch)\s+)?"
    r"(?:Sở|Bộ Chỉ huy|Công an|Thanh tra|Thuế|Ban Quản lý|Ban QLDA|Trung tâm|Cục|Chi cục|UBND|Ủy ban nhân dân|Bảo hiểm|Kho bạc)\b",
    re.I,
)
BODY_TASK_DISALLOWED = re.compile(r"\b(?:các|chủ trì|phối hợp|chịu trách nhiệm|địa chỉ|như sau|gồm|thực hiện|triển khai|về việc|tại|theo|ngày)\b", re.I)


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
    lines = tail.splitlines()
    for index, raw_line in enumerate(lines):
        line = normalized(raw_line)
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
        body_candidate = re.sub(r"^[-–—•]\s*", "", line)
        bullet = re.match(r"^[-–—•]\s*(.*)", line)
        in_open_paren = bool(current and current.count("(") > current.count(")") and not bullet)
        outside_open = (
            re.sub(r"^[^)]*\)", "", line) if (in_open_paren and ")" in line)
            else ("" if in_open_paren else line)
        )
        line_outside_parens = re.sub(r"\([^)]*(?:\)|$)", "", outside_open).strip()
        is_prose = bool(KINH_GUI_PROSE.match(body_candidate))
        if is_prose and section == "kinh_gui" and not bullet and current:
            if in_open_paren and not SENTENCE_BODY_CUES.search(line_outside_parens):
                is_prose = False
            elif (
                body_candidate[:1].islower()
                and not re.search(r"[.;]$", current)
                and not SENTENCE_BODY_CUES.search(body_candidate)
            ):
                is_prose = False
        if section == "kinh_gui" and is_prose:
            if current:
                entries.append(current)
                current = ""
            break
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
        if (
            section == "kinh_gui"
            and current
            and not current.endswith((":", ","))
            and SENTENCE_BODY_CUES.search(line_outside_parens)
        ):
            entries.append(current)
            current = ""
            break
        if current and re.match(r"Lưu\s*(?::|VT)", current, re.I):
            _luu_tok = r"(?:[TVNCX]{1,2}\d{0,2}|VT|BTCD|PVHCC|TT\.?PVHCC|KSTT|HSVV(?:-TD)?|HCTC|HCQT|QTTV|P\.?\s*QT-?TV|P\.?QTTV|XDCT|NNMT|KTTH|KGVX|NC|LĐVP|CVP|PVP\w*|\d{1,2})"
            if not (
                (current.rstrip().endswith(",") and not re.match(r"^\d+\s+\S", line) and not is_prose and len(line) <= 60)
                or re.fullmatch(
                    rf"[\s,.;()/\-]+|(?:[\s,.;()/\-]*{_luu_tok}(?:[\s,;().\-/]+{_luu_tok})*[\s,.;()]*)",
                    line,
                    re.I,
                )
            ):
                entries.append(current)
                current = ""
                break
        if current and (
            not re.search(r"[.;]$", current)
            or (
                section in {"kinh_gui", "noi_nhan"}
                and current.endswith(".")
                and re.search(r"(?:^|[\s.:,;-])[A-ZĐ]\.$", current)
                and not is_prose
            )
        ):
            current += " " + line
        elif section in {"kinh_gui", "noi_nhan"} and current and current.endswith(";") and not is_prose and not re.match(r"Lưu\s*(?::|VT)", current, re.I):
            next_is_bullet = index + 1 < len(lines) and bool(re.match(r"^[-–—•]\s*", normalized(lines[index + 1])))
            if ":" in current and (line.endswith((";", ".")) or len(line) <= 85 or next_is_bullet):
                current += " " + line
            elif line.endswith(";") or next_is_bullet:
                entries.append(current)
                current = line
            elif (
                line.endswith(".")
                and not line.endswith(":")
                and len(line) <= 85
                and not SENTENCE_BODY_CUES.search(line)
                and not re.search(r"\b(?:như\s+sau|kính\s+đề\s+nghị|trân\s+trọng|ý\s+kiến|chỉ\s+đạo|thực\s+hiện|triển\s+khai|về\s+việc)\b", line, re.I)
            ):
                entries.append(current)
                current = line
            else:
                entries.append(current)
                current = ""
                break
        else:
            if current:
                entries.append(current)
                current = ""
            break
    if current:
        entries.append(current)
    return [normalized(entry).strip(" ;.") for entry in entries if entry.strip(" ;.")]


_NON_SO_UNIT = re.compile(
    r"^(?:Công\s+an|Công\s+ty|Cty|Bộ\s+Chỉ\s+huy|Ban\s+|Trung\s+tâm|Chi\s+cục|Cục\s+|"
    r"Thuế\s+|Kho\s+bạc|Ngân\s+hàng|Trường\s+|Bệnh\s+viện|Báo\s+|Đài\s+|Viện\s+|"
    r"UBND\b|Ủy\s+ban|Tỉnh\s+đoàn|Hội\s+|Đảng\s+ủy|Văn\s+phòng|Thanh\s+tra\s+tỉnh)\b",
    re.I,
)


def _split_top_level_commas(value: str) -> list[str]:
    parts, buf, depth = [], [], 0
    for ch in value:
        if ch == "(":
            depth += 1
        elif ch == ")" and depth > 0:
            depth -= 1
        if ch == "," and depth == 0:
            tok = "".join(buf).strip()
            if tok:
                parts.append(tok)
            buf = []
        else:
            buf.append(ch)
    tail = "".join(buf).strip()
    if tail:
        parts.append(tail)
    return parts


def _split_recipient(entry, page, section, scope):
    output = []
    if re.match(r"Lưu\s*(?::|VT)", entry, re.I):
        tail = re.sub(r"^Lưu\s*:?\s*", "", entry, flags=re.I)
        expanded_tail = re.sub(r"(?<!\w)([TVNCX])\s+(\d{1,2})(?!\w)", r"\1\2", tail)
        while True:
            # Expand shared letter prefix lists like N1, 4 -> N1, N4.
            nxt = re.sub(r"(?<!\w)([TVNCX])(\d{1,2})\s*,\s*(\d{1,2})(?!\w)", r"\1\2, \1\3", expanded_tail)
            if nxt == expanded_tail:
                break
            expanded_tail = nxt
        for match in re.finditer(r"(?<!\w)(?:VT|[TVNCX]\d{1,2})(?!\w)", expanded_tail, re.I):
            token = match.group(0)
            output.append(make_mention(token, "archive_reference" if token.upper() == "VT" else "staff_code", page, "luu", entry, organization_scope=scope))
        # Preserve unfamiliar archive/routing codes instead of silently dropping them.
        residual = re.sub(r"(?<!\w)(?:VT|[TVNCX]\d{1,2})(?!\w)", "", expanded_tail, flags=re.I)
        residual = re.sub(r"\([^)]*\)", "", residual).strip(" ,.;")
        if residual:
            if "," in residual and not re.search(r"\b(?:HSVV|Long)\b", residual, re.I):
                parts = [p.strip(" .;") for p in residual.split(",") if p.strip(" .;")]
                if len(parts) >= 2 and all(len(p) >= 2 and not re.fullmatch(r"[IVX]{1,4}", p) for p in parts):
                    for part in parts:
                        output.append(make_mention(part, "unknown", page, "luu", entry, organization_scope=scope))
                    return output
            output.append(make_mention(residual, "unknown", page, "luu", entry, organization_scope=scope))
        return output

    if re.search(r"\b(?:mục|điều|khoản|điểm)\s+(?:\d+|[ivxlcdm]+\b|[a-zđ]\b)", entry, re.I):
        return [make_mention(entry, "reference", page, section, references=[entry], organization_scope=scope)]

    # Expand explicit enumerations but retain the parent phrase as evidence/context.
    batch = re.match(
        r"^(Các\s+Ban\s+QLDA|Các\s+[Ss]ở(?:\s*,\s*(?:ban\s*,\s*)?ngành)?|[Ss]ở"
        r"|Đảng\s+ủy\s+(?:các\s+)?(?:xã|phường)"
        r"|(?:UBND|Ủy\s+ban\s+nhân\s+dân)\s+(?:các\s+)?(?:xã|phường))\s*:\s*(.+)$",
        entry,
        re.I,
    )
    if batch:
        prefix = batch.group(1).lower()
        if "ban qlda" in prefix:
            qualifier = "Ban QLDA"
        elif "sở" in prefix:
            qualifier = "Sở"
        elif "đảng ủy" in prefix:
            qualifier = "Đảng ủy xã" if "xã" in prefix else "Đảng ủy phường"
        elif "xã" in prefix:
            qualifier = "UBND xã"
        else:
            qualifier = "UBND phường"
        values = re.sub(r"Văn\s+hóa,\s*Thể\s+thao\s+và\s+Du\s+lịch", lambda m: m.group(0).replace(",", "\x00"), batch.group(2), flags=re.I)
        if qualifier == "Sở":
            values = re.sub(
                r"(?<!\bvà)(?<!\bcủa)\s+(?=(?:Sở\s+)?(?:Nông nghiệp và Môi trường|Nông nghiệp và Phát triển nông thôn|Khoa học và Công nghệ|Giáo dục và Đào tạo|Văn hóa\x00\s*Thể thao và Du lịch|Dân tộc và Tôn giáo|Công Thương|Xây dựng|Tài chính|Nội vụ|Tư pháp|Ngoại vụ|Y tế|Thanh tra)\b)",
                ", ",
                values,
                flags=re.I,
            )
        splitter = r"[;,]\s*|\s+và\s+" if qualifier.startswith(("UBND ", "Đảng ủy ")) else r"[;,]\s*"
        for token in re.split(splitter, values, flags=re.I):
            token = token.replace("\x00", ",").strip()
            if qualifier.startswith(("UBND ", "Đảng ủy ")):
                token = re.sub(r"^(?:xã|phường)\s+", "", token, flags=re.I).strip()
            if token:
                item_qualifier = None if (qualifier == "Sở" and _NON_SO_UNIT.match(token)) else qualifier
                output.append(make_mention(token, "unit", page, section, entry, references=[entry], qualifier=item_qualifier, organization_scope=scope))
        return output

    if re.match(r"^Đảng\s+ủy\s+(?:xã|phường)\s+.+,\s*(?:xã|phường)\s+", entry, re.I):
        parts = [p.strip(" .;") for p in re.split(r"\s*,\s*", entry) if p.strip(" .;")]
        if len(parts) >= 2 and all(re.match(r"^(?:Đảng\s+ủy\s+)?(?:xã|phường)\s+\S", p, re.I) for p in parts):
            results = []
            for p in parts:
                val = p if re.match(r"^Đảng\s+ủy\b", p, re.I) else f"Đảng ủy {p}"
                results.append(make_mention(val, "unit", page, section, entry, references=[entry], organization_scope=scope))
            return results

    if ";" in entry and ":" not in entry:
        parts = [p.strip() for p in re.split(r"\s*;\s*", entry) if p.strip()]
        parts = [p for p in parts if not re.fullmatch(r"(?:để\s+)?(?:b/c|báo\s+cáo|biết|thực\s+hiện|phối\s+hợp)", p, re.I)]
        if len(parts) > 1 or (len(parts) == 1 and parts[0] != entry):
            results = []
            for part in parts:
                for item in _split_recipient(part, page, section, scope):
                    item.evidence[0].raw = normalized(entry)
                    item.mention_id = stable_id(item.raw, item.kind, item.evidence, item.references)
                    results.append(item)
            return results

    if GROUP.search(entry) and not SINGLE_UNIT_CAC.match(entry):
        # Chủ tịch, các PCT are two selectors, not one bare PCT.
        if re.match(r"^(?:CT|Chủ tịch)\s*,", entry, re.I):
            first, second = entry.split(",", 1)
            return [make_mention(first, "role", page, section, entry, organization_scope=scope), make_mention(second, "group", page, section, entry, quantifier="all", organization_scope=scope)]
        return [make_mention(entry, "group", page, section, quantifier="all", organization_scope=scope)]

    prefixed_roles = re.match(r"^(PVP|PCVP)\s*[:：]?\s+(.+)$", entry, re.I)
    if prefixed_roles and "," in prefixed_roles.group(2):
        role_prefix = prefixed_roles.group(1).upper()
        tokens = []
        for raw_tok in prefixed_roles.group(2).split(","):
            tok = normalized(raw_tok).strip(" ;.")
            if not tok:
                continue
            if not ROLE_START.match(tok):
                tok = f"{role_prefix} {tok}"
            tokens.append(make_mention(tok, "role", page, section, entry, organization_scope=scope))
        if tokens:
            return tokens

    if ROLE_START.match(entry) and "," in entry:
        top_parts = _split_top_level_commas(entry)
        if len(top_parts) > 1:
            return [make_mention(token, "role", page, section, entry, organization_scope=scope) for token in top_parts]

    if re.match(r"PCT\b", entry, re.I) and re.search(r"\s+và\s+", entry, re.I):
        chunks = re.split(r"\s+và\s+", entry, flags=re.I)
        return [make_mention(token, "person", page, section, entry, qualifier="PCT", organization_scope=scope) for token in chunks]

    kind = "role" if ROLE_START.match(entry) or re.match(r"(?:Đ/c|Đồng chí)\b", entry, re.I) else "unit"
    return [make_mention(entry, kind, page, section, organization_scope=scope)]


def _body_task_mentions(pages, source_page, existing_mentions, scope):
    chunks, ranges, offset = [], [], 0
    for page in pages:
        text = unicodedata.normalize("NFC", page.get("text", ""))
        chunks.append(text)
        ranges.append((offset, offset + len(text), page["page"]))
        offset += len(text) + 1
    doc_text = "\n".join(chunks)
    nn = HEADERS["noi_nhan"].search(doc_text)
    if not nn:
        return []
    kg = HEADERS["kinh_gui"].search(doc_text)
    start = kg.end() if kg and kg.end() < nn.start() else 0
    stops = [m.start() for pat in HEADERS.values() for m in pat.finditer(doc_text)]
    stops += [m.start() for m in re.finditer(r"(?m)^.*$", doc_text) if SIGNATURE.match(m[0].strip())]
    stops += [m.start() for m in BODY_LIST_HEADING.finditer(doc_text)]
    end_stops = [s for s in stops if s > start]
    end = min(end_stops) if end_stops else nn.start()
    if end <= start:
        return []

    def dedup_key(raw_val: str) -> str:
        collapsed = re.sub(r"\b(\w+)\s+\1\b", r"\1", normalized(raw_val).casefold())
        c = compact(collapsed)
        return re.sub(r"^(?:ubnd|ủybanhândân|ủybannhândân)", "", c)

    seen_keys = set()
    for m in existing_mentions:
        seen_keys.add(dedup_key(m.raw))
        if m.qualifier:
            seen_keys.add(dedup_key(f"{m.qualifier} {m.raw}"))

    nn_ev = Evidence(page=source_page, section="noi_nhan", raw="Như trên")
    results = []
    for match in BODY_TASK_HEAD.finditer(doc_text, start, end):
        actor = normalized(match.group(2))
        if not BODY_TASK_UNIT.match(actor) or BODY_TASK_DISALLOWED.search(actor):
            continue
        page_no = next((pg for left, right, pg in ranges if left <= match.start() < right), source_page)
        line_ev = Evidence(page=page_no, section="body_reference", raw=normalized(match.group(0).rstrip()))
        if re.match(r"^(?:Các\s+Ban\s+QLDA|Các\s+[Ss]ở(?:\s*,\s*(?:ban\s*,\s*)?ngành)?|[Ss]ở|Đảng\s+ủy\s+(?:các\s+)?(?:xã|phường)|(?:UBND|Ủy\s+ban\s+nhân\s+dân)\s+(?:các\s+)?(?:xã|phường))\s*:", actor, re.I):
            for item in _split_recipient(actor, page_no, "body_reference", scope):
                k = dedup_key(f"{item.qualifier} {item.raw}" if item.qualifier else item.raw)
                k_raw = dedup_key(item.raw)
                if not k or k in seen_keys or k_raw in seen_keys:
                    continue
                seen_keys.add(k)
                seen_keys.add(k_raw)
                item.evidence = [line_ev, nn_ev]
                item.references = ["Như trên"]
                item.mention_id = stable_id(item.raw, item.kind, item.evidence, item.references)
                results.append(item)
            continue
        protected = re.sub(r"Văn\s+hóa,\s*Thể\s+thao\s+và\s+Du\s+lịch", lambda m: m[0].replace(",", "\x00"), actor, flags=re.I)
        parts = re.split(
            r"\s*,\s*|\s+và\s+(?=(?:Sở|Ban|UBND|Ủy ban|Công an|Bộ Chỉ huy|Thanh tra|Trung tâm|Cục|Chi cục|xã|phường)\b)",
            protected,
            flags=re.I,
        )
        for part in parts:
            tok = part.replace("\x00", ",").strip()
            tok = re.sub(r"^Đề nghị\s+", "", tok, flags=re.I).strip()
            tok = re.sub(r"^(?:Giám đốc|Thủ trưởng|Chủ tịch)\s+(?=(?:Sở|Bộ Chỉ huy|Công an|Thanh tra|Thuế|Ban Quản lý|Ban QLDA|Trung tâm|Cục|Chi cục|UBND|Ủy ban nhân dân|Bảo hiểm|Kho bạc)\b)", "", tok, flags=re.I).strip()
            if not tok or BODY_TASK_DISALLOWED.search(tok):
                continue
            k = dedup_key(tok)
            if not k or k in seen_keys:
                continue
            seen_keys.add(k)
            for item in _split_recipient(tok, page_no, "body_reference", scope):
                item.evidence = [line_ev, nn_ev]
                item.references = ["Như trên"]
                item.mention_id = stable_id(item.raw, item.kind, item.evidence, item.references)
                results.append(item)
    return results


def extract_rule_mentions(pages, metadata=None):
    from .article_references import expand_article_reference

    metadata = metadata.model_dump(mode="json") if hasattr(metadata, "model_dump") else (metadata or {})
    scope = metadata.get("issuer")
    sections, mentions, reasons, reference_pages = [], [], [], []
    for page in pages:
        text = unicodedata.normalize("NFC", page.get("text", ""))
        for section, pattern in HEADERS.items():
            source = unicodedata.normalize("NFC", (page.get("recipient_text") or text) if section == "noi_nhan" else text)
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
                if re.fullmatch(r"Như\s+trên(?:\s*\([^)]*\))?", entry, re.I):
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
            mentions.extend(_body_task_mentions(pages, reference_pages[0], mentions, scope))
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
