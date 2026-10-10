"""Resolve recipient article links using only responsible subjects and linked lists."""
import re
import unicodedata

from .contracts import Evidence
from .mentions import HEADERS, SIGNATURE, _split_recipient, make_mention, normalized, stable_id


ARTICLE = re.compile(r"(?im)^[ \t]*Điều[ \t]+(\d+)[ \t]*[.:]")
ARTICLE_REFERENCE = re.compile(r"^(?:Như\s+(?:tại\s+)?|(?:các\s+)?(?:cá nhân|đơn vị|cơ quan)\s+(?:nêu\s+)?(?:tại|ở)\s+)Điều\s+(\d+)$", re.I)
LIST_HEADING = re.compile(r"(?im)^[ \t]*(?:DANH SÁCH|PHỤ LỤC(?:[ \t]+\d+)?)\b")
ACTION = r"(?:chủ trì|phối hợp|chịu trách nhiệm|có trách nhiệm|theo dõi|đôn đốc|hướng dẫn|kiểm tra|tuyên truyền|xác định|tổ chức|thực hiện)"
UNIT_START = r"(?:Sở|UBND|Ủy ban nhân dân|Công an|Thanh tra|Thuế|Công ty|Cty|Ban Quản lý|Trung tâm|Cục|Chi cục)\b"


def article_number(entry):
    match = ARTICLE_REFERENCE.fullmatch(normalized(entry).strip(" ;."))
    return int(match[1]) if match else None


def _sections(pages):
    """Index exact article headings; retain page boundaries as source evidence."""
    chunks, ranges, offset = [], [], 0
    for page in pages:
        text = unicodedata.normalize("NFC", page.get("ocr_text") or page.get("text", ""))
        # A repeated page number is not part of a wrapped name.
        text = re.sub(r"(?m)^[ \t]*\d+[ \t]*$", "", text)
        chunks.append(text)
        ranges.append((offset, offset + len(text), page["page"]))
        offset += len(text) + 1
    document = "\n".join(chunks)

    def evidence(start, end):
        return [Evidence(page=page, section="body_reference", raw=document[max(start, left):min(end, right)].strip())
                for left, right, page in ranges
                if max(start, left) < min(end, right) and document[max(start, left):min(end, right)].strip()]

    stops = [m.start() for pattern in HEADERS.values() for m in pattern.finditer(document)]
    stops += [m.start() for m in re.finditer(r"(?m)^.*$", document) if SIGNATURE.match(m[0].strip())]
    lists = list(LIST_HEADING.finditer(document))
    stops += [m.start() for m in lists]
    headings = list(ARTICLE.finditer(document))
    articles = {}
    for index, heading in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(document)
        end = min([end] + [stop for stop in stops if heading.end() < stop < end])
        articles.setdefault(int(heading[1]), []).append(evidence(heading.end(), end))
    # An unnumbered list link is verifiable only with one attached list.
    attached = evidence(lists[0].end(), len(document)) if len(lists) == 1 else []
    return articles, attached


def _subjects(text):
    """Read responsibility selectors, excluding entities mentioned in the duties."""
    text = normalized(text)
    subjects = []
    for sentence in re.split(r"(?<=\.)\s+(?!\d)", text):
        sentence = re.sub(r"^\d+[.)]\s*", "", sentence)
        responsibility = re.search(r"^(.+?)\s+(?:chịu|có)\s+trách nhiệm\b", sentence, re.I)
        if responsibility and not sentence.casefold().startswith("giao "):
            subjects.append(responsibility[1])
        participants = re.match(r"^((?:các\s+)?(?:cá nhân|đơn vị|cơ quan)\s+(?:nêu\s+)?(?:tại|ở)\s+Điều\s+\d+)\s+(?:cùng\s+)?tham gia\b", sentence, re.I)
        if participants:
            subjects.append(participants[1])
        for match in re.finditer(r"\bGiao\s+(.+?)(?=\s+" + ACTION + r"\b)", sentence, re.I):
            subjects.append(match[1])
        for match in re.finditer(r"\bphối hợp với\s+(.+?)(?=\s+" + ACTION + r"\b)", sentence, re.I):
            subjects.append(match[1])
    return subjects


def _selectors(subject):
    # Commas inside a department name or a generic group do not split selectors.
    subject = re.sub(r"Văn hóa,\s*Thể thao và Du lịch|các cơ quan,\s*đơn vị liên quan|các sở,\s*ban,\s*ngành liên quan",
                     lambda m: m[0].replace(",", "\x00"), subject, flags=re.I)
    subject = re.sub(r"\s+và\s+(?=(?:Giám đốc|Chánh|Chủ tịch|Thủ trưởng|các cá nhân|các đơn vị|Công ty|Sở|UBND|Ông|Bà|Đồng chí)\b)", ";", subject, flags=re.I)
    # A named person's following title is context, not another recipient.
    subject = re.sub(r"\b((?:Ông|Bà|Đồng chí)\s+[^,;]+),\s*(?:Giám đốc|Phó Giám đốc|Chủ tịch|Chánh|Trưởng|Hiệu trưởng)\b[^,;]*",
                     r"\1", subject, flags=re.I)
    department = False
    for token in re.split(r"[,;]\s*", subject):
        token = token.replace("\x00", ",").strip()
        batch = re.match(r"^(?:Giám đốc\s+)?(?:các\s+)?Sở\s*:\s*(.+)", token, re.I)
        if batch:
            department = True
            yield batch[1], "Sở"
            continue
        if department and not re.match(r"^(?:Giám đốc|Trưởng|Chánh|Chủ tịch|Thủ trưởng|các|Sở|UBND|Ủy ban|Công ty)\b", token, re.I):
            yield token, "Sở"
            continue
        department = False
        # The directory represents these public bodies as units.
        token = re.sub(r"^(?:Giám đốc|Trưởng|Chánh|Chủ tịch)\s+(?=" + UNIT_START + r")", "", token, flags=re.I)
        if token:
            yield token, None


def expand_article_reference(entry, source_page, pages, scope=None):
    number = article_number(entry)
    if number is None:
        return None
    articles, attached = _sections(pages)
    source = Evidence(page=source_page, section="noi_nhan", raw=entry)

    def linked(mention, evidence, references):
        mention.evidence = evidence + [source]
        mention.references = list(dict.fromkeys([entry] + references))
        mention.mention_id = stable_id(mention.raw, mention.kind, mention.evidence, mention.references)
        return mention

    def unresolved(raw, evidence, references):
        return linked(make_mention(raw, "reference", evidence[0].page if evidence else source_page,
                                   "body_reference", organization_scope=scope), evidence, references)

    def read(target, trail=(), parent_evidence=(), selection=None):
        references = [f"Điều {n}" for n in (*trail, target)]
        if target in trail or len(trail) >= 16 or len(articles.get(target, [])) != 1:
            return [unresolved(f"Điều {target}" if trail else entry, list(parent_evidence), references)]
        evidence = list(parent_evidence) + articles[target][0]
        text = " ".join(e.raw for e in articles[target][0])
        mentions = []
        for subject in _subjects(text):
            for token, qualifier in _selectors(subject):
                nested = article_number(token)
                if nested is not None:
                    nested_selection = "person" if re.search(r"cá nhân", token, re.I) else "unit"
                    if selection and nested_selection != selection:
                        mentions.append(unresolved(token, evidence, references))
                        continue
                    mentions.extend(read(nested, (*trail, target), evidence,
                                         selection=nested_selection))
                    continue
                person = re.fullmatch(r"(?:Ông|Bà|Đồng chí)\s+(.+)", token, re.I)
                parsed = ([make_mention(person[1], "person", evidence[-1].page, "body_reference", organization_scope=scope)]
                          if person else _split_recipient(token, evidence[-1].page, "body_reference", scope))
                for mention in parsed:
                    if selection == "person" and mention.kind not in {"person", "role", "reference"}:
                        continue
                    if selection == "unit" and mention.kind in {"person", "role"}:
                        continue
                    mention.qualifier = qualifier or mention.qualifier
                    mentions.append(linked(mention, evidence, references))
        if re.search(r"(?:danh sách|phụ lục)\s+kèm theo", text, re.I):
            if not attached:
                mentions.append(unresolved("Danh sách kèm theo", evidence, references))
            else:
                list_evidence = evidence + attached
                list_mentions = []
                list_text = "\n".join(e.raw for e in attached)
                rows = list(re.finditer(r"(?m)^[ \t]*\d+[.)][ \t]*", list_text))
                if selection != "unit":
                    for index, row in enumerate(rows):
                        end = rows[index + 1].start() if index + 1 < len(rows) else len(list_text)
                        raw = normalized(list_text[row.end():end])
                        person = re.match(r"^(?:Ông|Bà|Đồng chí)\s+([^,;]+)", raw, re.I)
                        if person:
                            mention = make_mention(person[1], "person", attached[0].page, "body_reference", organization_scope=scope)
                            list_mentions.append(linked(mention, list_evidence, references + ["Danh sách kèm theo"]))
                        else:
                            list_mentions.append(unresolved(raw.strip(" ;.") or "Danh sách kèm theo", list_evidence,
                                                            references + ["Danh sách kèm theo"]))
                mentions.extend(list_mentions)
                if not list_mentions:
                    mentions.append(unresolved("Danh sách kèm theo", evidence, references))
        return mentions or [unresolved(f"Điều {target}", evidence, references)]

    return read(number)
