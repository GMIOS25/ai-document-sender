"""Resolve verified native groups and explicitly listed Gia Lai communes."""
import re
import unicodedata

from .contracts import GroupSelection
from .registry import normalize


COMMUNE_SELECTORS = {
    "ubnd cac xa phuong", "uy ban nhan dan cac xa phuong",
    "ubnd cac phuong xa", "uy ban nhan dan cac phuong xa",
    "cac xa phuong", "cac phuong xa",
    "ubnd xa phuong", "ubnd phuong xa",
    "toan bo ubnd cac xa phuong", "toan bo ubnd cac phuong xa",
    "tat ca cac xa phuong", "tat ca cac phuong xa",
    "chu tich ubnd cac xa phuong", "chu tich uy ban nhan dan cac xa phuong",
    "chu tich ubnd cac phuong xa", "chu tich uy ban nhan dan cac phuong xa",
}
PARTY_COMMUNE_SELECTORS = {
    "dang uy cac xa phuong", "dang uy cac phuong xa",
    "dang uy xa phuong", "dang uy phuong xa",
    "toan bo dang uy cac xa phuong", "toan bo dang uy cac phuong xa",
    "tat ca dang uy cac xa phuong", "tat ca dang uy cac phuong xa",
}
LIST_HEADS = {
    "ubnd cac xa": "xa", "uy ban nhan dan cac xa": "xa", "ubnd xa": "xa", "uy ban nhan dan xa": "xa", "cac xa": "xa",
    "ubnd cac phuong": "phuong", "uy ban nhan dan cac phuong": "phuong", "ubnd phuong": "phuong", "uy ban nhan dan phuong": "phuong", "cac phuong": "phuong",
}
COMBINED_PARTY_LIST_HEADS = {
    "dang uy ubnd cac xa phuong": None, "dang uy ubnd cac phuong xa": None,
    "dang uy ubnd cac xa": "xa", "dang uy ubnd cac phuong": "phuong",
    "dang uy ubnd xa": "xa", "dang uy ubnd phuong": "phuong",
    "bi thu chu tich ubnd cac xa phuong": None, "bi thu chu tich ubnd cac phuong xa": None,
    "bi thu chu tich ubnd cac xa": "xa", "bi thu chu tich ubnd cac phuong": "phuong",
    "bi thu chu tich ubnd xa": "xa", "bi thu chu tich ubnd phuong": "phuong",
    "bi thu dang uy chu tich ubnd cac xa phuong": None, "bi thu dang uy chu tich ubnd cac phuong xa": None,
    "bi thu dang uy chu tich ubnd cac xa": "xa", "bi thu dang uy chu tich ubnd cac phuong": "phuong",
    "bi thu dang uy chu tich ubnd xa": "xa", "bi thu dang uy chu tich ubnd phuong": "phuong",
}
COLONLESS_LIST_PREFIX = re.compile(
    r"^\s*(?P<head>(?:(?:Toàn\s+bộ|Tất\s+cả)\s+)?(?:(?:Ủy\s+ban\s+nhân\s+dân|UBND)\s+)?(?:các\s+)?"
    r"(?:xã\s*,?\s*phường|phường\s*,?\s*xã|xã|phường))\s+(?P<tail>.+)$",
    re.I,
)
COMBINED_COLONLESS_PREFIX = re.compile(
    r"^\s*(?P<head>(?:Đảng\s+ủy|Bí\s+thư(?:\s+Đảng\s+ủy)?)\s*,\s*(?:Chủ\s+tịch\s+)?(?:Ủy\s+ban\s+nhân\s+dân|UBND)\s+"
    r"(?:(?:các\s+)?(?:xã\s*,?\s*phường|phường\s*,?\s*xã|xã|phường)))\s+(?P<tail>.+)$",
    re.I,
)


def _combined_communes(tail, registry, commune_type=None):
    ubnd = _communes(tail, registry.by_id.values(), commune_type)
    party = _match_party_communes(tail, _party_commune_members(registry), commune_type)
    if not ubnd or not party:
        return []
    merged = {r.recipient_id: r for r in ubnd + party}
    return list(merged.values())


def local_commune_list(raw, registry):
    cleaned = re.sub(
        r"^(\s*(?:Ủy\s+ban\s+nhân\s+dân|UBND))\s+tỉnh\s+(?=(?:xã|phường|các\s+(?:xã|phường))\b)",
        r"\1 ",
        unicodedata.normalize("NFC", raw),
        flags=re.I,
    )
    head, sep, tail = cleaned.partition(":")
    selector = normalize(head)
    if sep:
        if selector in COMBINED_PARTY_LIST_HEADS:
            return _combined_communes(tail, registry, COMBINED_PARTY_LIST_HEADS[selector])
        if selector not in COMMUNE_SELECTORS and selector not in LIST_HEADS:
            return None
        return _communes(tail, registry.by_id.values(), LIST_HEADS.get(selector))
    comb_match = COMBINED_COLONLESS_PREFIX.match(cleaned)
    if comb_match:
        tail_clean = comb_match.group("tail").strip()
        if re.match(r"^(?:(?:ngoại\s+)?trừ|ven\s+biển|liên\s+quan|có\s+liên\s+quan|\d)\b", tail_clean, re.I):
            return None
        norm_head = normalize(comb_match.group("head"))
        if norm_head in COMBINED_PARTY_LIST_HEADS:
            matched = _combined_communes(tail_clean, registry, COMBINED_PARTY_LIST_HEADS[norm_head])
            return matched or None
    match = COLONLESS_LIST_PREFIX.match(cleaned)
    if not match:
        return None
    tail_clean = match.group("tail").strip()
    if re.match(r"^(?:ngoại\s+)?trừ\b", tail_clean, re.I):
        return None
    norm_head = normalize(match.group("head"))
    if norm_head not in COMMUNE_SELECTORS and norm_head not in LIST_HEADS:
        return None
    if "cac" not in norm_head.split() and not re.search(r"[,;]|\bvà\b", tail_clean, re.I):
        return None
    matched = _communes(tail_clean, registry.by_id.values(), LIST_HEADS.get(norm_head))
    return matched or None


def _lookup_commune_tokens(tail, candidates, strip_prefix_re):
    names = re.split(r"[,;\n]+|\s+và\s+", tail, flags=re.I)
    names = [name for name in names if name.strip(" .\t")]
    if not names:
        return []
    matched = {}
    for value in names:
        key = re.sub(strip_prefix_re, "", normalize(value).strip(".")).strip()
        hits = candidates.get(key, [])
        if len(hits) == 1:
            matched[hits[0].recipient_id] = hits[0]
            continue
        words_list = key.split()
        split_hits = None
        for idx in range(1, len(words_list)):
            k1 = re.sub(strip_prefix_re, "", " ".join(words_list[:idx])).strip()
            k2 = re.sub(strip_prefix_re, "", " ".join(words_list[idx:])).strip()
            h1, h2 = candidates.get(k1, []), candidates.get(k2, [])
            if len(h1) == 1 and len(h2) == 1:
                split_hits = (h1[0], h2[0])
                break
        if split_hits is None:
            return []
        for item in split_hits:
            matched[item.recipient_id] = item
    return list(matched.values())


def _communes(tail, recipients, commune_type=None):
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
    return _lookup_commune_tokens(tail, candidates, r"^ubnd\s+")


def _party_commune_members(registry):
    members = [
        r for r in registry.by_id.values()
        if r.sphere == "ext_province_comm"
        and re.fullmatch(r"A21\.\d+", r.code)
        and re.match(r"^dang uy (?:xa|phuong)\b", normalize(r.name))
    ]
    if len(members) != 135:
        return []
    return sorted(members, key=lambda r: tuple(int(p) if p.isdigit() else p for p in re.split(r"(\d+)", r.code)))


def _match_party_communes(tail, members, commune_type=None):
    candidates = {}
    for r in members:
        name = re.sub(r"^(?:dang uy )?", "", re.sub(r" (?:tinh )?gia lai$", "", normalize(r.name))).strip()
        if commune_type and not name.startswith(commune_type + " "):
            continue
        short = re.sub(r"^(?:xa|phuong) ", "", name)
        for key in {name, short}:
            candidates.setdefault(key, []).append(r)
    return _lookup_commune_tokens(tail, candidates, r"^dang uy\s+")


def native_group(raw, registry):
    terms = re.split(r"\s+(?:ngoại\s+trừ|trừ)\s+", raw, maxsplit=1, flags=re.I)
    selector = normalize(terms[0]).strip(".")
    if selector in PARTY_COMMUNE_SELECTORS:
        members = _party_commune_members(registry)
        if not members:
            return [], None
        if len(terms) == 2:
            excluded = {r.recipient_id for r in _match_party_communes(terms[1], members)}
            return ([r for r in members if r.recipient_id not in excluded], None) if excluded else ([], None)
        return members, None
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
