"""Immutable, read-only registry snapshots and conservative candidate retrieval."""
from datetime import datetime, timezone, timedelta, date
from contextlib import closing
import hashlib
import json
import re
import sqlite3
import unicodedata
from .contracts import Recipient


def normalize(value):
    value = str(value or "").casefold().replace("đ", "d")
    value = "".join(c for c in unicodedata.normalize("NFKD", value) if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9@._]+", " ", value).strip()


def words(value):
    return re.sub(r"[^a-z0-9]+", " ", normalize(value)).split()


def digest(value):
    return "sha256:" + hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


DEPARTMENTS = {"KGVX": "Phòng Khoa giáo Văn xã", "QTTV": "Phòng Quản trị Tài vụ", "XDCT": "Phòng Xây dựng và Công thương", "KTTH": "Phòng Kinh tế - Tổng hợp", "NNMT": "Phòng Nông nghiệp và Môi trường", "NC": "Phòng Nội chính", "HCTC": "Phòng Hành chính Tổ chức"}


def department_context(metadata):
    """Use an explicit department, or a verified numeric UBND sign-number suffix."""
    explicit = (metadata.department_code or "").strip()
    if explicit:
        return explicit, "metadata"
    match = re.fullmatch(r"[0-9]+/UBND-([A-Z]+)", (metadata.sign_number or "").strip(), re.I)
    if match and match.group(1).upper() in DEPARTMENTS:
        return match.group(1).upper(), "sign_number_suffix"
    return None, "unknown"


class Registry:
    def __init__(self, settings):
        self.settings = settings
        # Hash actual transactional rows instead of file bytes (WAL may contain live changes).
        with closing(sqlite3.connect(settings.lookup_db.resolve().as_uri() + "?mode=ro", uri=True)) as conn:
            conn.row_factory = sqlite3.Row
            conn.execute("BEGIN")
            rows = [dict(r) for r in conn.execute("SELECT * FROM recipients ORDER BY recipient_id")]
            conn.rollback()
        self.policy = json.loads(settings.policy_path.read_text(encoding="utf-8-sig"))
        self.policy_as_of = datetime.now(timezone(timedelta(hours=7))).date().isoformat()
        self.groups = {}
        self.selectable_groups = set()
        overlay = []
        if settings.runtime_db.exists():
            with closing(sqlite3.connect(settings.runtime_db.resolve().as_uri() + "?mode=ro", uri=True)) as conn:
                if conn.execute("SELECT 1 FROM sqlite_master WHERE name='registry_overlay'").fetchone():
                    for (body,) in conn.execute("SELECT body FROM registry_overlay ORDER BY overlay_id"):
                        record = json.loads(body)
                        if record.get("verification_status") != "verified":
                            continue
                        overlay.append(record)
                        if "recipient" in record:
                            rows = [r for r in rows if r["recipient_id"] != record["recipient"]["recipient_id"]]
                            rows.append(record["recipient"])
                        if "selector" in record:
                            self.groups[normalize(record["selector"])] = record.get("member_ids", [])
                        if record.get("selectable_group_id"):
                            self.selectable_groups.add(record["selectable_group_id"])
        self.registry_version = digest({"rows": sorted(rows, key=lambda r:r["recipient_id"]), "overlay": overlay})
        effective_aliases = [a for a in self.policy.get("aliases",[]) if self.alias_effective(a)]
        self.alias_policy_version = digest({"policy":self.policy,"effective_aliases":effective_aliases})
        self.resolution_as_of = datetime.now(timezone.utc).isoformat()
        self.by_id = {}
        for r in rows:
            self.by_id[r["recipient_id"]] = Recipient(
                recipient_id=r["recipient_id"], source_id=str(r["source_id"]), recipient_type=r["recipient_type"],
                name=(r.get("full_name") or r["name"]) if r["recipient_type"] == "INTERNAL_PERSON" else r["name"],
                role=r["name"] if r["recipient_type"] == "INTERNAL_PERSON" else None,
                display_name=r.get("display_name") or r["name"], sphere=r["sphere"], code=r.get("code") or "",
                parent_name=r.get("parent_name") or "")

    def alias_effective(self, alias):
        today=date.fromisoformat(self.policy_as_of)
        return not ((alias.get("valid_from") and date.fromisoformat(alias["valid_from"])>today)
                    or (alias.get("valid_to") and date.fromisoformat(alias["valid_to"])<today))

    def alias(self, raw, metadata=None):
        matches = []
        for a in self.policy.get("aliases", []):
            if normalize(a.get("raw_alias")) != normalize(raw):
                continue
            if not self.alias_effective(a):
                continue
            if a.get("department_context") and normalize(a["department_context"]) != normalize(getattr(metadata,"department_code",None)):
                continue
            if a.get("organization_scope") and normalize(a["organization_scope"]) != normalize(getattr(metadata,"issuer",None)):
                continue
            matches.append(a)
        if len(matches)>1:
            return {"verification_status":"conflicting","pending_reason":"ambiguous_alias_policy","conflicting_aliases":matches}
        return matches[0] if matches else None

    def exact_code(self, code):
        return [r for r in self.by_id.values() if r.code and normalize(r.code) == normalize(code)]

    def exact_name(self, name):
        q = normalize(name)
        return [r for r in self.by_id.values() if normalize(r.name) == q or normalize(r.display_name) == q]

    def exact_role(self, role):
        return [r for r in self.by_id.values() if r.recipient_type == "INTERNAL_PERSON" and normalize(r.role) == normalize(role)]

    def staff_code(self, code, department=None):
        if self.policy.get("staff_code", {}).get("verification_status") != "verified":
            return []
        token = code.upper().strip()
        if not re.fullmatch(r"[A-Z]{1,3}\d{1,3}", token):
            return []
        parent = DEPARTMENTS.get((department or "").upper(), department)
        # Department context is required; identical codes elsewhere never guessed.
        if not parent:
            return []
        return [r for r in self.by_id.values() if r.recipient_type == "INTERNAL_PERSON"
                and re.search(r"(?:^|\s)" + re.escape(token) + r"$", r.role or "", re.I)
                and normalize(r.parent_name) == normalize(parent)]

    def initials(self, query, role=None):
        # Every initial and full final token must match, in order, without fuzzy distance.
        parts = words(query)
        if len(parts) < 2:
            return []
        return [r for r in self.by_id.values() if r.recipient_type == "INTERNAL_PERSON"
                and (not role or normalize(r.role) == normalize(role))
                and len(words(r.name)) == len(parts)
                and all((p == w or (len(p) == 1 and w.startswith(p))) for p,w in zip(parts,words(r.name)))]

    def short_name(self, query, role):
        parts=words(query)
        if not parts or not role:
            return []
        return [r for r in self.exact_role(role) if len(parts)<=len(words(r.name)) and words(r.name)[-len(parts):] == parts]

    def local_unit_name(self, query, issuer):
        if "gia lai" not in normalize(issuer):
            return []
        q = normalize(query)
        matches = []
        for r in self.by_id.values():
            if r.recipient_type == "INTERNAL_PERSON":
                continue
            name = normalize(r.name)
            name = re.sub(r"\s+gia lai$", "", name)
            if name == q or re.sub(r"\s+tinh$", "", name) == q:
                matches.append(r)
        return matches

    def group_members(self, selector):
        ids = self.groups.get(normalize(selector))
        if ids is None or not ids or any(rid not in self.by_id for rid in ids):
            return None
        return [self.by_id[rid] for rid in ids]

    def search(self, query, limit=10):
        # Require meaningful lexical overlap. Missing Ngoại vụ never becomes Nội vụ.
        q = set(words(query))
        if not q:
            return []
        stops = {"so", "tinh", "gia", "lai", "ubnd", "uy", "ban", "nhan", "dan", "van", "phong", "va", "cac", "ong", "ba"}
        meaningful = q - stops
        exact = self.exact_code(query) or self.exact_name(query) or self.exact_role(query)
        if exact:
            return exact[:limit]
        ranked = []
        for r in self.by_id.values():
            tokens = set(words(" ".join([r.name,r.role or "",r.parent_name,r.code])))
            overlap = meaningful & tokens
            if not meaningful or not overlap:
                continue
            # Exclude partial match if a substantial distinguishing token is absent.
            substantial = {x for x in meaningful if len(x) > 2}
            if substantial and not substantial <= tokens:
                continue
            ranked.append((len(overlap) / len(meaningful), r))
        ranked.sort(key=lambda x:(-x[0],x[1].recipient_id))
        return [r for _,r in ranked[:limit]]

    def serialize(self):
        return {rid:r.model_dump(mode="json") for rid,r in self.by_id.items()}

    def snapshot(self):
        return {"registry_version":self.registry_version,"alias_policy_version":self.alias_policy_version,
                "resolution_as_of":self.resolution_as_of,"recipients":self.serialize(),"policy":self.policy,
                "groups":self.groups,"selectable_groups":sorted(self.selectable_groups),"policy_as_of":self.policy_as_of}

    @classmethod
    def from_snapshot(cls, settings, data):
        registry = cls.__new__(cls)
        registry.settings = settings
        for key in ("registry_version","alias_policy_version","resolution_as_of","policy","groups","policy_as_of"):
            setattr(registry,key,data[key])
        registry.selectable_groups = set(data["selectable_groups"])
        registry.by_id = {rid:Recipient.model_validate(r) for rid,r in data["recipients"].items()}
        return registry
