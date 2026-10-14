"""Follow recipient references through document sections and attached lists."""
from dataclasses import dataclass, field
import re
import unicodedata

from .contracts import Evidence
from .mentions import HEADERS, SIGNATURE, _split_recipient, make_mention, normalized, stable_id


LOCATOR = r"(Điều|Mục|Khoản|Điểm)\s+(\d+[a-zđ]?|[ivxlcdm]+|[a-zđ])"
SUBJECT_REFERENCE = (r"(?:các\s+)?(?:cá nhân|đơn vị|cơ quan)\s+"
                     r"(?:(?:được\s+)?(?:nêu|quy định|liệt kê|ghi|đề cập)\s+)?"
                     r"(?:tại|ở|theo)\s+")
LOCATOR_PATH = LOCATOR + r"(?:\s+" + LOCATOR + r")*"
REFERENCE = re.compile(r"^(?:Như\s+(?:tại\s+)?|" + SUBJECT_REFERENCE + r")?(?P<path>" + LOCATOR_PATH + r")$", re.I)
SECTION_HEADING = re.compile(r"(?im)^[ \t]*(?:[-–—•][ \t]*)?" + LOCATOR + r"[ \t]*[.:)]")
CLAUSE_HEADING = re.compile(r"(?m)^[ \t]*(?:[-–—•][ \t]*)?(?:(\d+)[.)]|([a-zđ])\))[ \t]*")
# OCR can merge a short uppercase stamp fragment with a centered list title.
LIST_HEADING = re.compile(r"(?m)^[ \t]*(?:[-–—•][ \t]*)?(?:[A-ZĐ]{1,12}[ \t]+){0,2}"
                          r"(?i:DANH SÁCH|PHỤ LỤC(?:[ \t]+\d+)?)\b")
ACTION = r"(?:chủ trì|phối hợp|chịu trách nhiệm|có trách nhiệm|theo dõi|đôn đốc|hướng dẫn|kiểm tra|tuyên truyền|xác định|tổ chức|thực hiện)"
UNIT_START = r"(?:Sở|UBND|Ủy ban nhân dân|Công an|Thanh tra|Thuế|Công ty|Cty|Ban Quản lý|Trung tâm|Cục|Chi cục)\b"
LEVEL = {"mục": 0, "điều": 1, "khoản": 2, "điểm": 3}


@dataclass
class _Section:
    target: tuple[str, str]
    start: int
    parents: tuple[tuple[str, str], ...]
    evidence: list[Evidence]
    text: str
    children: list["_Section"] = field(default_factory=list)


def _reference_path(entry):
    match = REFERENCE.fullmatch(normalized(entry).strip(" ;."))
    if not match:
        return None
    return tuple((m[1].casefold(), m[2].casefold()) for m in re.finditer(LOCATOR, match["path"], re.I))


def reference_target(entry):
    path = _reference_path(entry)
    return path[0] if path else None


def article_number(entry):
    target = reference_target(entry)
    return int(target[1]) if target and target[0] == "điều" and target[1].isdigit() else None


def _label(target):
    kind, value = target
    return f"{kind.capitalize()} {value.upper() if kind == 'mục' else value}"


def _sections(pages):
    """Index section headings, tolerating OCR bullets and retaining page evidence."""
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
    body_ends = [m.start() for m in HEADERS["noi_nhan"].finditer(document)] + [m.start() for m in lists]
    headings = list(SECTION_HEADING.finditer(document))
    records = []
    for index, heading in enumerate(headings):
        # Recipient/annex sections do not define clauses in the decision body.
        if any(stop < heading.start() for stop in body_ends):
            continue
        end = headings[index + 1].start() if index + 1 < len(headings) else len(document)
        end = min([end] + [stop for stop in stops if heading.end() < stop < end])
        target = (heading[1].casefold(), heading[2].casefold())
        records.append((target, heading.start(), heading.end()))
        if target[0] not in {"điều", "khoản"}:
            continue
        # Ordinary legal documents write clauses as "1." and points as "a)".
        markers = list(CLAUSE_HEADING.finditer(document, heading.end(), end))
        for marker in markers:
            child = ("khoản", marker[1]) if marker[1] else ("điểm", marker[2])
            if child[0] != "khoản" or target[0] != "khoản":
                records.append((child, marker.start(), marker.end()))
    records.sort(key=lambda record: record[1])
    sections, stack = {}, []
    for index, (target, start, body_start) in enumerate(records):
        own_end = records[index + 1][1] if index + 1 < len(records) else len(document)
        end = next((other_start for other, other_start, _ in records[index + 1:]
                    if LEVEL[other[0]] <= LEVEL[target[0]]), len(document))
        end = min([end] + [stop for stop in stops if body_start <= stop < end])
        own_end = min(own_end, end)
        while stack and LEVEL[stack[-1].target[0]] >= LEVEL[target[0]]:
            stack.pop()
        parents = tuple(parent.target for parent in reversed(stack))
        section = _Section(target, start, parents, evidence(body_start, end), document[body_start:own_end])
        sections.setdefault(target, []).append(section)
        if stack:
            stack[-1].children.append(section)
        stack.append(section)
    # An unnumbered list link is verifiable only with one attached list.
    attached = evidence(lists[0].end(), len(document)) if len(lists) == 1 else []
    return sections, attached


def _subjects(text):
    """Read responsibility selectors, excluding entities mentioned in the duties."""
    text = normalized(text)
    subjects = []
    for sentence in re.split(r"(?<=\.)\s+(?!\d)", text):
        sentence = re.sub(r"^(?:\d+|[a-zđ])[.)]\s*", "", sentence)
        responsibility = re.search(r"^(.+?)\s+(?:chịu|có)\s+trách nhiệm\b", sentence, re.I)
        if responsibility and not sentence.casefold().startswith("giao "):
            subjects.append(responsibility[1])
        participants = re.match(r"^(" + SUBJECT_REFERENCE + LOCATOR_PATH + r")\s+(?:cùng\s+)?tham gia\b", sentence, re.I)
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


def _attached_rows(attached):
    """Keep OCR-prefixed numbered rows and the page containing each member."""
    text = "\n".join(e.raw for e in attached)
    ranges, offset = [], 0
    for source in attached:
        ranges.append((offset, offset + len(source.raw), source.page))
        offset += len(source.raw) + 1
    rows = list(re.finditer(r"(?m)^[ \t]*(?:[-–—•][ \t]*)?\d+[.)][ \t]*", text))
    for index, row in enumerate(rows):
        start = row.end()
        end = rows[index + 1].start() if index + 1 < len(rows) else len(text)
        evidence = [Evidence(page=page, section="body_reference", raw=text[max(start, left):min(end, right)].strip())
                    for left, right, page in ranges
                    if max(start, left) < min(end, right) and text[max(start, left):min(end, right)].strip()]
        yield normalized(text[start:end]), evidence


def expand_article_reference(entry, source_page, pages, scope=None):
    path = _reference_path(entry)
    if path is None:
        return None
    sections, attached = _sections(pages)
    source = Evidence(page=source_page, section="noi_nhan", raw=entry)

    def linked(mention, evidence, references):
        mention.evidence = evidence + [source]
        mention.references = list(dict.fromkeys([entry] + references))
        mention.mention_id = stable_id(mention.raw, mention.kind, mention.evidence, mention.references)
        return mention

    def unresolved(raw, evidence, references):
        return linked(make_mention(raw, "reference", evidence[0].page if evidence else source_page,
                                   "body_reference", organization_scope=scope), evidence, references)

    def read(path, trail=(), parent_evidence=(), selection=None, context=None, references=()):
        target = path[0]
        label = " ".join(_label(part) for part in path)
        references = [*references, label]
        candidates = [section for section in sections.get(target, [])
                      if all(parent in section.parents for parent in path[1:])]
        if (context and target[0] in {"khoản", "điểm"}
                and not any(part[0] in {"điều", "mục"} for part in path)):
            lineage = (context.target,) + context.parents
            outer_level = min(LEVEL[part[0]] for part in path)
            for index, parent in enumerate(lineage):
                if LEVEL[parent[0]] < outer_level:
                    # A bare point/clause is relative to its nearest container;
                    # a missing local label must not pick an unrelated section.
                    candidates = [section for section in candidates
                                  if all(ancestor in section.parents for ancestor in lineage[index:])]
                    break
        if len(candidates) != 1:
            return [unresolved(label if trail else entry, list(parent_evidence), references)]
        return visit(candidates[0], trail, parent_evidence, selection, references)

    def visit(section, trail, parent_evidence, selection, references, required=True):
        if len(trail) >= 16 or section.start in trail:
            return [unresolved(references[-1], list(parent_evidence), references)]
        evidence = list(parent_evidence) + section.evidence
        text = section.text
        mentions = []
        for subject in _subjects(text):
            for token, qualifier in _selectors(subject):
                nested = _reference_path(token)
                if nested is not None:
                    nested_selection = ("person" if re.search(r"cá nhân", token, re.I) else
                                        "unit" if re.search(r"đơn vị|cơ quan", token, re.I) else selection)
                    if selection and nested_selection != selection:
                        mentions.append(unresolved(token, evidence, references))
                        continue
                    mentions.extend(read(nested, (*trail, section.start), evidence,
                                         selection=nested_selection, context=section, references=references))
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
        for child in section.children:
            mentions.extend(visit(child, (*trail, section.start), evidence, selection,
                                  [*references, _label(child.target)], required=False))
        if re.search(r"(?:danh sách|phụ lục)\s+kèm theo", text, re.I):
            if not attached:
                mentions.append(unresolved("Danh sách kèm theo", evidence, references))
            else:
                list_mentions = []
                if selection != "unit":
                    for raw, row_evidence in _attached_rows(attached):
                        list_evidence = evidence + row_evidence
                        # A common OCR accent error affects the honorific, not the name.
                        person = re.match(r"^(?:Ông|Ống|Bà|Đồng chí)\s+([^,;]+)", raw, re.I)
                        if person:
                            mention = make_mention(person[1], "person", row_evidence[0].page, "body_reference", organization_scope=scope)
                            list_mentions.append(linked(mention, list_evidence, references + ["Danh sách kèm theo"]))
                        else:
                            list_mentions.append(unresolved(raw.strip(" ;.") or "Danh sách kèm theo", list_evidence,
                                                            references + ["Danh sách kèm theo"]))
                mentions.extend(list_mentions)
                if not list_mentions:
                    mentions.append(unresolved("Danh sách kèm theo", evidence, references))
        return mentions or ([unresolved(references[-1], evidence, references)] if required else [])

    return read(path)
