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
            tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            self.unit_groups = [{"sphere": sphere, "id": gid, "name": name, "member_codes": json.loads(codes),
                                 "complete": bool(complete)}
                                for sphere, gid, name, codes, complete in conn.execute(
                                    "SELECT sphere,group_id,name,member_codes_json,complete FROM unit_groups ORDER BY sphere,group_id")
                                ] if "unit_groups" in tables else []
            internal_edges = list(conn.execute("SELECT id,parent_id FROM internal_nodes ORDER BY id")) if "internal_nodes" in tables else []
            conn.rollback()
        self.policy = json.loads(settings.policy_path.read_text(encoding="utf-8-sig"))
        from .learning import read_learning
        learning = read_learning(settings.lookup_db)
        if learning:
            self.policy['learning'] = learning
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
        self.registry_version = digest({"rows": sorted(rows, key=lambda r:r["recipient_id"]), "overlay": overlay,
                                        "unit_groups": self.unit_groups, "internal_edges": [tuple(e) for e in internal_edges]})
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
        self._build_indexes()
        children = {}
        for node, parent in internal_edges:
            children.setdefault(str(parent), []).append(str(node))
        people = {r.source_id: r.recipient_id for r in self.by_id.values() if r.recipient_type == "INTERNAL_PERSON"}
        self.recipient_expansions = {}
        for r in self.by_id.values():
            if r.recipient_type == "INTERNAL_GROUP" and r.recipient_id in self.selectable_groups:
                member_ids = self.groups.get(normalize(r.name), [])
                if member_ids and all(rid in self.by_id and self.by_id[rid].recipient_type == "INTERNAL_PERSON" for rid in member_ids):
                    self.recipient_expansions[r.recipient_id] = sorted(set(member_ids))
                continue
            if r.recipient_type not in {"INTERNAL_DEPT", "INTERNAL_UNIT"}:
                continue
            seen, members = {r.source_id}, set()
            stack = list(children.get(r.source_id, []))
            while stack:
                node = stack.pop()
                if node in seen:
                    continue
                seen.add(node)
                if node in people:
                    members.add(people[node])
                stack.extend(children.get(node, []))
            if members:
                self.recipient_expansions[r.recipient_id] = sorted(members)

    def _build_indexes(self):
        from .learning import index_learning
        self._names, self._codes, self._roles, self._local_names = {}, {}, {}, {}
        self._search_tokens = {}
        for r in self.by_id.values():
            for name in {normalize(r.name), normalize(r.display_name)}:
                self._names.setdefault(name, []).append(r)
            if r.code:
                self._codes.setdefault(normalize(r.code), []).append(r)
            if r.recipient_type == 'INTERNAL_PERSON':
                self._roles.setdefault(normalize(r.role), []).append(r)
            else:
                local_name = re.sub(r'\s+gia lai$', '', normalize(r.name))
                for name in {local_name, re.sub(r'\s+tinh$', '', local_name)}:
                    self._local_names.setdefault(name, []).append(r)
            self._search_tokens[r.recipient_id] = set(words(' '.join([r.name, r.role or '', r.parent_name, r.code])))
        index_learning(self)

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
        return list(self._codes.get(normalize(code), []))

    def exact_name(self, name):
        return list(self._names.get(normalize(name), []))

    def internal_node_candidates(self, query):
        # iDesk expands a selected dept/unit itself. Keep competing identities
        # so a name shared with another node/sphere still requires review.
        query = re.sub(r"^(?:toan bo|tat ca)\s+", "", normalize(query))
        matches = self.exact_code(query) or self.exact_name(query)
        return matches if any(r.recipient_type in {"INTERNAL_DEPT", "INTERNAL_UNIT"} for r in matches) else []

    def exact_role(self, role):
        return list(self._roles.get(normalize(role), []))

    def staff_code(self, code):
        if self.policy.get("staff_code", {}).get("verification_status") != "verified":
            return []
        token = code.upper().strip()
        if not re.fullmatch(r"[A-Z]{1,3}\d{1,3}", token):
            return []
        # Search every department; duplicate codes remain ambiguous in the resolver.
        return [r for r in self.by_id.values() if r.recipient_type == "INTERNAL_PERSON"
                and re.search(r"(?:^|\s)" + re.escape(token) + r"$", r.role or "", re.I)]

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
        return list(self._local_names.get(normalize(query), []))

    def group_members(self, selector):
        ids = self.groups.get(normalize(selector))
        if ids is None or not ids or any(rid not in self.by_id for rid in ids):
            return None
        return [self.by_id[rid] for rid in ids]

    def search(self, query, limit=10, *, include_learning=True):
        # Require meaningful lexical overlap. Missing Ngoại vụ never becomes Nội vụ.
        q = set(words(query))
        if not q:
            return []
        stops = {"so", "tinh", "gia", "lai", "ubnd", "uy", "ban", "nhan", "dan", "van", "phong", "va", "cac", "ong", "ba"}
        meaningful = q - stops
        exact = self.exact_code(query) or self.exact_name(query) or self.exact_role(query) or self.internal_node_candidates(query)
        if exact:
            return exact[:limit]
        from .learning import bind_targets
        learned = {}
        for rule in self._learned_aliases.get(normalize(query), []) if include_learning else []:
            members, reason = bind_targets(rule, self)
            if not reason:
                learned.update((r.recipient_id, r) for r in members)
        if learned:
            return list(learned.values())[:limit]
        ranked = []
        for r in self.by_id.values():
            tokens = self._search_tokens[r.recipient_id]
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
                "unit_groups": self.unit_groups, "recipient_expansions": self.recipient_expansions,
                "groups":self.groups,"selectable_groups":sorted(self.selectable_groups),"policy_as_of":self.policy_as_of}

    @classmethod
    def from_snapshot(cls, settings, data):
        registry = cls.__new__(cls)
        registry.settings = settings
        for key in ("registry_version","alias_policy_version","resolution_as_of","policy","groups","policy_as_of"):
            setattr(registry,key,data[key])
        registry.selectable_groups = set(data["selectable_groups"])
        registry.unit_groups = data.get("unit_groups", [])
        registry.recipient_expansions = data.get("recipient_expansions", {})
        registry.by_id = {rid:Recipient.model_validate(r) for rid,r in data["recipients"].items()}
        registry._build_indexes()
        return registry
