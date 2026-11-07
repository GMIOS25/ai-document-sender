"""Resolve verified native groups and explicitly listed Gia Lai communes."""
import re
import unicodedata

from .contracts import GroupSelection
from .registry import normalize


COMMUNE_SELECTORS = {
    "ubnd cac xa phuong", "uy ban nhan dan cac xa phuong",
    "cac xa phuong", "ubnd xa phuong", "toan bo ubnd cac xa phuong", "tat ca cac xa phuong",
}
LIST_HEADS = {"ubnd cac xa": "xa", "uy ban nhan dan cac xa": "xa", "cac xa": "xa",
              "ubnd cac phuong": "phuong", "uy ban nhan dan cac phuong": "phuong", "cac phuong": "phuong"}


def local_commune_list(raw, registry):
    head, sep, tail = raw.partition(":")
    selector = normalize(head)
    if not sep or (selector not in COMMUNE_SELECTORS and selector not in LIST_HEADS):
        return None
    return _communes(tail, registry.by_id.values(), LIST_HEADS.get(selector))


def _communes(tail, recipients, commune_type=None):
    names = re.split(r"[,;\n]+|\s+và\s+", tail, flags=re.I)
    names = [name for name in names if name.strip(" .\t")]
    if not names:
        return []
    candidates = {}
    for r in recipients:
        if r.sphere != "int_province_comm":
            continue
        name = normalize(r.name)
        if not re.match(r"^(?:ubnd )?(?:xa|phuong) ", name):
            continue
        name = re.sub(r" (?:tinh )?gia lai$", "", name)
        full = re.sub(r"^ubnd ", "", name)
        if commune_type and not full.startswith(commune_type + " "):
            continue
        short = re.sub(r"^(?:xa|phuong) ", "", full)
        for key in {full, short}:
            candidates.setdefault(key, []).append(r)
    matched = {}
    for value in names:
        key = re.sub(r"^ubnd ", "", normalize(value).strip("."))
        matches = candidates.get(key, [])
        if len(matches) != 1:
            return []
        matched[matches[0].recipient_id] = matches[0]
    return list(matched.values())


def native_group(raw, registry):
    terms = re.split(r"\s+(?:ngoại\s+trừ|trừ)\s+", raw, maxsplit=1, flags=re.I)
    selector = normalize(terms[0]).strip(".")
    whole_province = selector in COMMUNE_SELECTORS or selector == "135 xa phuong"
    if whole_province:
        selector = "135 xa phuong"
    groups = [g for g in registry.unit_groups if normalize(g["name"]) == selector]
    if not groups and not whole_province:
        return None
    if len(groups) != 1 or not groups[0]["complete"]:
        return [], None
    group = groups[0]
    codes = group["member_codes"]
    if not codes or (whole_province and len(codes) != 135) or len(codes) <= 1:
        return None
    members = []
    for code in codes:
        matches = [r for r in registry.exact_code(code) if r.sphere == group["sphere"]]
        if len(matches) != 1:
            return [], None
        members.append(matches[0])
    selection = GroupSelection(group_id=group["id"], sphere=group["sphere"],
                               member_codes=[r.code for r in members], registry_version=registry.registry_version)
    if len(terms) == 2:
        if not whole_province:
            return [], None
        excluded = {r.recipient_id for r in _communes(terms[1], members)}
        return ([r for r in members if r.recipient_id not in excluded], selection) if excluded else ([], None)
    return members, selection


def conflicting_group_scope(mention, combined, extraction):
    """Reject a shortened model mention when its recipient line narrows it."""
    from .extraction import _section_source

    def flatten(value):
        value = unicodedata.normalize("NFC", value).casefold()
        return re.sub(r"\s+", " ", value).strip()

    text = flatten(combined).rstrip(" .;")
    raw = flatten(mention.raw).rstrip(" .;")
    if not raw:
        return True
    locations = {(e.page, e.section) for e in mention.evidence}
    witnesses = [e.raw for e in mention.evidence]
    witnesses.extend(other.raw for other in extraction.mentions if other.mention_id != mention.mention_id
                     and locations.intersection((e.page, e.section) for e in other.evidence))
    pages = {page.get("page"): page for page in extraction.pages}
    for page, section in locations:
        if page in pages and section in {"kinh_gui", "noi_nhan"}:
            witnesses.extend(_section_source(pages[page], section).splitlines())
    phrases = {tuple(re.findall(r"\w+", phrase)) for phrase in (text, raw)}
    patterns = [re.compile(r"(?<!\w)" + r"[\W_]+".join(map(re.escape, phrase)) + r"(?!\w)")
                for phrase in phrases if phrase]
    for witness in map(flatten, witnesses):
        for pattern in patterns:
            for hit in pattern.finditer(witness):
                suffix = witness[hit.end():].lstrip()
                prefix = witness[:hit.start()].rstrip()
                if (re.search(r"^\s*\(?\s*(?:trừ|ngoại\s+trừ|ngoài\s+trừ|không\s+kể|không\s+gồm|không\s+bao\s+gồm|không\s+gửi|riêng)\b", suffix, re.I)
                        or re.search(r"\b(?:không\s+gửi|trừ|ngoại\s+lệ|loại\s+trừ)\s*$", prefix, re.I)):
                    return True
    return False
