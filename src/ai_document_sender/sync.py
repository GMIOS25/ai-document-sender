"""Smart Sync Diff Engine for updating tenant lookup databases and FTS5 indices."""
from datetime import datetime, timezone
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sqlite3
import re
from typing import Any, Dict, Optional, Tuple
import unicodedata

from .config import Settings
from .tenants import TenantManager, normalize_tenant_id


def remove_accents(input_str: str) -> str:
    """Normalize Vietnamese accented characters to plain unaccented characters."""
    if not input_str:
        return ""
    s = str(input_str).replace("đ", "d").replace("Đ", "D")
    nfkd = unicodedata.normalize("NFKD", s)
    return "".join([c for c in nfkd if not unicodedata.combining(c)])


ABBREVIATIONS = {
    "UBND": ["Ủy ban nhân dân", "Uy ban nhan dan"],
    "HĐND": ["Hội đồng nhân dân", "Hoi dong nhan dan"],
    "ĐBQH": ["Đại biểu Quốc hội", "Dai bieu Quoc hoi"],
    "VP": ["Văn phòng", "Van phong"],
    "VPUB": ["Văn phòng UBND", "Van phong Uy ban nhan dan"],
    "VPUBND": ["Văn phòng Ủy ban nhân dân", "Van phong Uy ban nhan dan"],
    "PVHCC": ["Trung tâm Phục vụ hành chính công", "Phuc vu hanh chinh cong"],
    "TTPVHCC": ["Trung tâm Phục vụ hành chính công", "Phuc vu hanh chinh cong"],
    "ĐC&KS": ["Địa chất và Khoáng sản", "Dia chat va Khoang san"],
    "ĐCKS": ["Địa chất và Khoáng sản", "Dia chat va Khoang san"],
    "TNMT": ["Tài nguyên và Môi trường", "Tai nguyen va Moi truong"],
    "NNMT": ["Nông nghiệp và Môi trường", "Nong nghiep va Moi truong"],
    "KTTH": ["Kinh tế - Tổng hợp", "Kinh te Tong hop"],
    "BoNNMT": ["Bộ Nông nghiệp và Môi trường", "Bo Nong nghiep va Moi truong"],
    "BTCD": ["Ban Tiếp công dân", "Ban Tiep cong dan"],
    "VHTTDL": ["Văn hóa, Thể thao và Du lịch"],
    "GDĐT": ["Giáo dục và Đào tạo"],
    "KH&CN": ["Khoa học và Công nghệ"],
    "QLDA": ["Quản lý dự án"],
    "BCHQS": ["Bộ Chỉ huy Quân sự"],
    "MTTQ": ["Mặt trận Tổ quốc"],
    "KSND": ["Kiểm sát nhân dân"],
    "TTCP": ["Thanh tra Chính phủ"],
    "CVP": ["Chánh Văn phòng"],
    "PCVP": ["Phó Chánh Văn phòng"],
}


def _padded_search_words(text: str) -> str:
    return ' ' + ' '.join(re.findall(r'\w+', remove_accents(text).casefold())) + ' '


_ABBREVIATION_PATTERNS = [
    (tuple(map(_padded_search_words, (abbr, *forms))), (abbr, *forms, *map(remove_accents, forms)))
    for abbr, forms in ABBREVIATIONS.items()
]


def build_search_tokens(*args) -> str:
    """Construct searchable token string with accents, no-accents, and acronyms."""
    tokens = []
    for arg in args:
        if arg:
            val = str(arg).strip()
            if val:
                tokens.append(val)
                no_acc = remove_accents(val)
                if no_acc != val:
                    tokens.append(no_acc)
                padded = _padded_search_words(val)
                for patterns, expansions in _ABBREVIATION_PATTERNS:
                    if any(pattern in padded for pattern in patterns):
                        tokens.extend(expansions)
    return " ".join(dict.fromkeys(tokens))


def refresh_search_index(conn, registry):
    """Rebuild derived text and FTS together; identity rows stay intact."""
    from .learning import bind_targets
    aliases = {}
    for rule in registry.policy.get('learning', {}).get('rules', []):
        # Group names belong to the resolver, not every individual member's FTS row.
        if len(rule.get('targets', [])) != 1:
            continue
        members, reason = bind_targets(rule, registry)
        if not reason:
            label = ' '.join(filter(None, [rule.get('qualifier'), rule['raw_alias']]))
            aliases.setdefault(members[0].recipient_id, []).append(label)
    changed = 0
    for rid, name, fullname, display, code, parent, raw, old in conn.execute(
            'SELECT recipient_id,name,full_name,display_name,code,parent_name,raw_json,search_text FROM recipients').fetchall():
        source = json.loads(raw or '{}')
        text = build_search_tokens(display, fullname, name, parent, source.get('refUname'),
                                   source.get('sign'), code, source.get('rank'), *aliases.get(rid, []))
        if text == old:
            continue
        conn.execute('UPDATE recipients SET search_text=? WHERE recipient_id=?', (text, rid))
        conn.execute('DELETE FROM recipients_fts WHERE recipient_id=?', (rid,))
        conn.execute('INSERT INTO recipients_fts (recipient_id,display_name,full_name,name,code,parent_name,search_text) VALUES (?,?,?,?,?,?,?)',
                     (rid, display, fullname or '', name, code, parent, text))
        changed += 1
    return changed


def compute_json_hash(data: Any) -> str:
    """Compute stable SHA-256 digest of arbitrary JSON-compatible data."""
    if data is None:
        return "empty"
    encoded = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def init_tenant_db(conn: sqlite3.Connection):
    """Ensure all required tables, indices, and views exist in the SQLite database."""
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS internal_nodes (
        id INTEGER PRIMARY KEY,
        parent_id INTEGER NOT NULL DEFAULT 0,
        type TEXT NOT NULL,
        name TEXT NOT NULL,
        ref_fullname TEXT,
        ref_uname TEXT,
        rank TEXT,
        sign TEXT,
        comm_code TEXT,
        unit_code TEXT,
        order_num INTEGER DEFAULT 0,
        raw_json TEXT
    );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_internal_parent ON internal_nodes(parent_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_internal_type ON internal_nodes(type);")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS comm_units (
        uuid TEXT PRIMARY KEY,
        code TEXT NOT NULL,
        name TEXT NOT NULL,
        sphere TEXT NOT NULL,
        send_count INTEGER DEFAULT 0,
        organ_id TEXT,
        username TEXT,
        alias_code TEXT,
        raw_json TEXT
    );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_comm_code ON comm_units(code);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_comm_sphere ON comm_units(sphere);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_comm_sphere_code ON comm_units(sphere, code);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_comm_count ON comm_units(send_count DESC);")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS recipients (
        recipient_id TEXT PRIMARY KEY,
        source_id TEXT NOT NULL,
        recipient_type TEXT NOT NULL,
        sphere TEXT NOT NULL,
        name TEXT NOT NULL,
        full_name TEXT,
        display_name TEXT NOT NULL,
        code TEXT,
        parent_name TEXT,
        rank_level TEXT,
        email TEXT,
        priority_score INTEGER DEFAULT 0,
        search_text TEXT,
        raw_json TEXT
    );
    """)
    columns = {r[1] for r in conn.execute("PRAGMA table_info(recipients)")}
    for column in ("rank_level", "email", "search_text"):
        if column not in columns:
            conn.execute("ALTER TABLE recipients ADD COLUMN " + column + " TEXT")
    has_observations = conn.execute("SELECT 1 FROM sqlite_master WHERE name='organization_observations'").fetchone()
    conn.execute("""CREATE TABLE IF NOT EXISTS organization_observations (
        sphere TEXT NOT NULL, code TEXT NOT NULL, source TEXT NOT NULL,
        observation_hash TEXT NOT NULL, raw_json TEXT NOT NULL,
        first_seen_at TEXT NOT NULL, last_seen_at TEXT NOT NULL,
        PRIMARY KEY (sphere,code,source,observation_hash))""")
    conn.execute("""CREATE TABLE IF NOT EXISTS unit_groups (
        sphere TEXT NOT NULL, group_id TEXT NOT NULL, name TEXT NOT NULL,
        member_codes_json TEXT NOT NULL, complete INTEGER NOT NULL,
        PRIMARY KEY (sphere, group_id))""")
    if not has_observations:
        now = datetime.now(timezone.utc).isoformat()
        for sphere, code, raw in conn.execute("SELECT sphere,code,raw_json FROM comm_units"):
            observation = json.loads(raw or '{}')
            conn.execute("INSERT OR IGNORE INTO organization_observations VALUES (?,?,?,?,?,?,?)",
                         (sphere, code, 'history', compute_json_hash(observation), raw or '{}', now, now))
    cur.execute("CREATE INDEX IF NOT EXISTS idx_recip_type ON recipients(recipient_type);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_recip_sphere ON recipients(sphere);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_recip_code ON recipients(code);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_recip_priority ON recipients(priority_score DESC);")

    cur.execute("""
    CREATE VIRTUAL TABLE IF NOT EXISTS recipients_fts USING fts5(
        recipient_id UNINDEXED,
        display_name,
        full_name,
        name,
        code,
        parent_name,
        search_text,
        tokenize = 'unicode61 remove_diacritics 2'
    );
    """)

    cur.execute("""
    CREATE VIEW IF NOT EXISTS v_internal_org_tree AS
    SELECT 
        child.id, child.parent_id, child.type, child.name AS title_or_dept,
        child.ref_fullname AS person_name, child.ref_uname AS email_uname,
        child.rank, child.sign, parent.name AS parent_name, parent.type AS parent_type
    FROM internal_nodes child
    LEFT JOIN internal_nodes parent ON child.parent_id = parent.id
    ORDER BY child.parent_id, child.order_num;
    """)

    cur.execute("""
    CREATE VIEW IF NOT EXISTS v_top_frequent_units AS
    SELECT code, name, sphere, send_count, uuid
    FROM comm_units
    ORDER BY send_count DESC;
    """)
    conn.commit()


def _diff_and_sync_comm_units(conn, elements, is_internal, source="history"):
    """Merge partial observations by sphere/code; native UUID is only metadata."""
    sphere = "int_province_comm" if is_internal else "ext_province_comm"
    recipient_type = "INT_PROVINCE_UNIT" if is_internal else "EXT_PROVINCE_UNIT"
    parent = "Nội tỉnh Gia Lai" if is_internal else "Khối Ngoài tỉnh / Bộ ngành Trung ương"
    incoming = {}
    for element in elements:
        code = str(element.get("code") or "").strip()
        name = str(element.get("name") or "").strip()
        if not code or not name:
            continue
        if code not in incoming or int(element.get("count") or 0) > int(incoming[code].get("count") or 0):
            incoming[code] = element
    changes = {"added": 0, "updated": 0, "deleted": 0}
    now = datetime.now(timezone.utc).isoformat()
    for code, element in incoming.items():
        raw = json.dumps(element, ensure_ascii=False, sort_keys=True)
        observation_hash = compute_json_hash(element)
        conn.execute("""INSERT INTO organization_observations
            (sphere,code,source,observation_hash,raw_json,first_seen_at,last_seen_at) VALUES (?,?,?,?,?,?,?)
            ON CONFLICT(sphere,code,source,observation_hash) DO UPDATE SET last_seen_at=excluded.last_seen_at""",
            (sphere, code, source, observation_hash, raw, now, now))
        old = conn.execute("SELECT uuid,name,send_count,raw_json FROM comm_units WHERE sphere=? AND code=?", (sphere, code)).fetchone()
        recipient = conn.execute("SELECT recipient_id,source_id,priority_score FROM recipients WHERE sphere=? AND code=? ORDER BY recipient_id LIMIT 1", (sphere, code)).fetchone()
        identity = old[0] if old else compute_json_hash([sphere, code])
        # Keep the historical ID spelling for old sync clients. UUID is never
        # used to find a matching unit; a collision gets a sphere/code key.
        if not old and not recipient and source == "history":
            native = str(element.get("uuid") or "").strip()
            if (native and not conn.execute("SELECT 1 FROM comm_units WHERE uuid=?", (native,)).fetchone()
                    and not conn.execute("SELECT 1 FROM recipients WHERE recipient_id=?", ("comm_" + native,)).fetchone()):
                identity = native
        rid = recipient[0] if recipient else "comm_" + identity
        source_id = recipient[1] if recipient else identity
        # Preserve frequency from history; directory/search counts are not usage.
        count = old[2] if old else (recipient[2] or 0 if recipient else 0)
        if source == "history":
            count = max(count, int(element.get("count") or 0))
        enriched = conn.execute("SELECT 1 FROM organization_observations WHERE sphere=? AND code=? AND source IN ('directory','search') LIMIT 1", (sphere, code)).fetchone()
        chosen_raw = old[3] if source == "history" and enriched and old else raw
        chosen = json.loads(chosen_raw or '{}')
        name = old[1] if source == "history" and enriched and old else str(element['name']).strip()
        if old and (old[1], old[2], old[3]) == (name, count, chosen_raw):
            continue
        conn.execute("""INSERT OR REPLACE INTO comm_units
            (uuid,code,name,sphere,send_count,organ_id,username,alias_code,raw_json) VALUES (?,?,?,?,?,?,?,?,?)""",
            (identity, code, name, sphere, count, chosen.get('organId'), chosen.get('username'), chosen.get('aliasCode'), chosen_raw))
        text = build_search_tokens(name, parent, chosen.get('refUname'), chosen.get('sign'), code, chosen.get('rank'))
        conn.execute("""INSERT OR REPLACE INTO recipients
            (recipient_id,source_id,recipient_type,sphere,name,display_name,code,parent_name,priority_score,search_text,raw_json)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)""", (rid, source_id, recipient_type, sphere, name, name, code, parent, count, text, chosen_raw))
        if old or recipient:
            conn.execute("DELETE FROM recipients_fts WHERE recipient_id=?", (rid,))
        conn.execute("INSERT INTO recipients_fts (recipient_id,display_name,full_name,name,code,parent_name,search_text) VALUES (?,?,?,?,?,?,?)", (rid, name, '', name, code, parent, text))
        changes['updated' if old or recipient else 'added'] += 1
    return changes


def _diff_and_sync_internal_org(
    conn: sqlite3.Connection,
    elements: list
) -> Dict[str, int]:
    """Smart diff and sync for internal personnel and department tree."""
    id_map = {e["id"]: e for e in elements if "id" in e}

    cur = conn.cursor()
    cur.execute("""
    SELECT id, parent_id, type, name, ref_fullname, ref_uname, rank, sign, comm_code, unit_code, order_num, raw_json
    FROM internal_nodes
    """)
    existing_rows = cur.fetchall()
    existing_by_id = {row[0]: row for row in existing_rows}

    incoming_ids = set(id_map.keys())
    existing_ids = set(existing_by_id.keys())

    added = 0
    updated = 0
    deleted = 0

    # 1. Deletions
    deleted_ids = existing_ids - incoming_ids
    for eid in deleted_ids:
        cur.execute("DELETE FROM internal_nodes WHERE id = ?", (eid,))
        cur.execute("DELETE FROM recipients WHERE recipient_id = ?", (f"internal_{eid}",))
        cur.execute("DELETE FROM recipients_fts WHERE recipient_id = ?", (f"internal_{eid}",))
        deleted += 1

    # 2. Inserts and Updates
    for eid, e in id_map.items():
        pid = e.get("parent", 0)
        etype = e.get("type", "")
        ename = e.get("name", "").strip()
        fullname = e.get("refFullname")
        uname = e.get("refUname")
        rank = e.get("rank")
        sign = e.get("sign")
        comm_code = e.get("commCode")
        unit_code = e.get("unitCode")
        order_num = e.get("order", 0)
        raw_json = json.dumps(e, ensure_ascii=False)

        parent_node = id_map.get(pid)
        parent_name = parent_node.get("name", "").strip() if parent_node else ""

        recipient_id = f"internal_{eid}"
        code = uname or comm_code or sign or ""

        # Priority calculation
        if rank == "org_leader":
            priority = 50000 - order_num * 10
        elif rank == "unit_leader":
            priority = 40000 - order_num * 10
        elif rank == "leader":
            priority = 30000 - order_num * 10
        elif rank == "specialist":
            priority = 10000 - order_num * 10
        elif etype in ["dept", "group"]:
            priority = 20000 - order_num * 10
        else:
            priority = 5000

        # Type and display_name
        if etype == "alias":
            recipient_type = "INTERNAL_PERSON"
            display_name = f"{fullname} - {ename}"
            if parent_name:
                display_name += f" ({parent_name})"
        elif etype == "dept":
            recipient_type = "INTERNAL_DEPT"
            display_name = f"{ename} (Nội bộ UBND tỉnh)"
        elif etype == "group":
            recipient_type = "INTERNAL_GROUP"
            display_name = f"{ename} [Tổ/Nhóm xử lý]"
        elif etype == "unit":
            recipient_type = "INTERNAL_UNIT"
            display_name = f"{ename} [Cơ quan nội bộ]"
        else:
            recipient_type = f"INTERNAL_{etype.upper()}"
            display_name = ename

        search_text = build_search_tokens(
            display_name, fullname, ename, parent_name, uname, sign, code, rank
        )

        if eid not in existing_by_id:
            # INSERT
            cur.execute("""
            INSERT INTO internal_nodes (
                id, parent_id, type, name, ref_fullname, ref_uname,
                rank, sign, comm_code, unit_code, order_num, raw_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (eid, pid, etype, ename, fullname, uname, rank, sign, comm_code, unit_code, order_num, raw_json))

            cur.execute("""
            INSERT INTO recipients (
                recipient_id, source_id, recipient_type, sphere, name,
                full_name, display_name, code, parent_name, rank_level,
                email, priority_score, search_text, raw_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                recipient_id, str(eid), recipient_type, "internal", ename,
                fullname, display_name, code, parent_name, rank,
                uname, priority, search_text, raw_json
            ))

            cur.execute("""
            INSERT INTO recipients_fts (
                recipient_id, display_name, full_name, name, code, parent_name, search_text
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (recipient_id, display_name, fullname or "", ename, code, parent_name, search_text))
            added += 1
        else:
            old_row = existing_by_id[eid]
            # row: id, parent_id, type, name, ref_fullname, ref_uname, rank, sign, comm_code, unit_code, order_num, raw_json
            if (old_row[1] != pid or old_row[2] != etype or old_row[3] != ename or
                old_row[4] != fullname or old_row[5] != uname or old_row[6] != rank or
                old_row[7] != sign or old_row[8] != comm_code or old_row[9] != unit_code or
                old_row[10] != order_num):

                cur.execute("""
                UPDATE internal_nodes SET
                    parent_id = ?, type = ?, name = ?, ref_fullname = ?, ref_uname = ?,
                    rank = ?, sign = ?, comm_code = ?, unit_code = ?, order_num = ?, raw_json = ?
                WHERE id = ?
                """, (pid, etype, ename, fullname, uname, rank, sign, comm_code, unit_code, order_num, raw_json, eid))

                cur.execute("""
                UPDATE recipients SET
                    recipient_type = ?, name = ?, full_name = ?, display_name = ?,
                    code = ?, parent_name = ?, rank_level = ?, email = ?,
                    priority_score = ?, search_text = ?, raw_json = ?
                WHERE recipient_id = ?
                """, (
                    recipient_type, ename, fullname, display_name, code,
                    parent_name, rank, uname, priority, search_text, raw_json, recipient_id
                ))

                cur.execute("DELETE FROM recipients_fts WHERE recipient_id = ?", (recipient_id,))
                cur.execute("""
                INSERT INTO recipients_fts (
                    recipient_id, display_name, full_name, name, code, parent_name, search_text
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (recipient_id, display_name, fullname or "", ename, code, parent_name, search_text))
                updated += 1

    return {"added": added, "updated": updated, "deleted": deleted}


def sync_tenant_lookup(
    tenant_id: str,
    payload: Dict[str, Any],
    settings: Settings,
    tenant_manager: Optional[TenantManager] = None
) -> Dict[str, Any]:
    """Execute complete Smart Sync for a tenant lookup database."""
    from .contracts import LookupDirectoryBatch, UnitGroupBatch
    directory = LookupDirectoryBatch.model_validate({"source": "directory", "elements": (payload.get("unit_directory") or {}).get("elements", [])})
    groups = UnitGroupBatch.model_validate(payload["unit_groups"]) if "unit_groups" in payload else None
    tid = normalize_tenant_id(tenant_id, settings.default_tenant)
    mgr = tenant_manager or TenantManager(settings)

    tenant_dir = mgr.get_tenant_dir(tid)
    tenant_dir.mkdir(parents=True, exist_ok=True)
    db_path = mgr.ensure_tenant_initialized(tid)
    # The default tenant can still be using the legacy DB. Move its policy with it.
    from .learning import FILENAME, read_learning
    legacy_learning = settings.lookup_db.parent / FILENAME
    tenant_learning = tenant_dir / FILENAME
    if (not db_path.exists() and tid == normalize_tenant_id(settings.default_tenant)
            and legacy_learning.exists() and not tenant_learning.exists()):
        tenant_learning.write_bytes(legacy_learning.read_bytes())

    person_data = payload.get("person") or {}
    unit_int_data = payload.get("unit_internal") or {}
    unit_ext_data = payload.get("unit_external") or {}

    # Extract elements
    person_elements = person_data.get("elements", []) if isinstance(person_data, dict) else (person_data if isinstance(person_data, list) else [])
    unit_int_elements = unit_int_data.get("elements", []) if isinstance(unit_int_data, dict) else (unit_int_data if isinstance(unit_int_data, list) else [])
    unit_ext_elements = unit_ext_data.get("elements", []) if isinstance(unit_ext_data, dict) else (unit_ext_data if isinstance(unit_ext_data, list) else [])

    h_person = compute_json_hash(person_elements)
    h_int = compute_json_hash(unit_int_elements)
    h_ext = compute_json_hash(unit_ext_elements)
    h_directory = compute_json_hash(directory.model_dump(mode="json")["elements"])
    h_groups = compute_json_hash(groups.model_dump(mode="json")) if groups else None
    search_hash = compute_json_hash({'abbreviations': ABBREVIATIONS, 'learning': read_learning(db_path)})

    meta_file = tenant_dir / "metadata.json"
    if meta_file.exists() and db_path.exists():
        try:
            meta = json.loads(meta_file.read_text(encoding="utf-8"))
            if (meta.get("person_hash") == h_person and
                meta.get("unit_internal_hash") == h_int and
                meta.get("unit_external_hash") == h_ext and
                meta.get("unit_directory_hash") == h_directory and
                (groups is None or meta.get("unit_groups_hash") == h_groups) and
                meta.get('search_policy_hash') == search_hash):
                # No change detected
                reg = mgr.get_registry(tid)
                return {
                    "status": "no_change",
                    "tenant_id": tid,
                    "message": "Datasets unchanged; lookup database is up to date.",
                    "registry_version": reg.registry_version,
                    "alias_policy_version": reg.alias_policy_version
                }
        except Exception:
            pass

    # Open connection to tenant DB
    conn = sqlite3.connect(str(db_path))
    try:
        init_tenant_db(conn)

        with conn:
            p_res = _diff_and_sync_internal_org(conn, person_elements)
            int_res = _diff_and_sync_comm_units(conn, unit_int_elements, is_internal=True)
            ext_res = _diff_and_sync_comm_units(conn, unit_ext_elements, is_internal=False)
            directory_res = _merge_organizations(conn, directory)
            if groups is not None:
                present = {(g.sphere, g.id) for g in groups.elements}
                absent = [key for key in conn.execute("SELECT sphere,group_id FROM unit_groups") if key not in present]
                command = ("DELETE FROM unit_groups WHERE sphere=? AND group_id=?" if groups.complete
                           else "UPDATE unit_groups SET complete=0 WHERE sphere=? AND group_id=?")
                conn.executemany(command, absent)
                conn.executemany("""INSERT INTO unit_groups VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(sphere,group_id) DO UPDATE SET name=excluded.name,
                    member_codes_json=CASE WHEN excluded.complete THEN excluded.member_codes_json ELSE unit_groups.member_codes_json END,
                    complete=excluded.complete""",
                    [(g.sphere, g.id, g.name, json.dumps(sorted(g.member_codes)), g.complete) for g in groups.elements])

        with conn:
            from .registry import Registry
            refreshed = refresh_search_index(conn, Registry(replace(settings, lookup_db=db_path)))

        # Flush WAL changes to main database
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")

        total_recipients = conn.execute("SELECT count(*) FROM recipients").fetchone()[0]
    finally:
        conn.close()

    # Save backup JSON files
    (tenant_dir / "person.json").write_text(json.dumps({"elements": person_elements}, ensure_ascii=False, indent=2), encoding="utf-8")
    (tenant_dir / "unit_internal_province.json").write_text(json.dumps({"elements": unit_int_elements}, ensure_ascii=False, indent=2), encoding="utf-8")
    (tenant_dir / "unit_except_provice.json").write_text(json.dumps({"elements": unit_ext_elements}, ensure_ascii=False, indent=2), encoding="utf-8")

    meta_payload = {
        "tenant_id": tid,
        "last_synced_at": datetime.now(timezone.utc).isoformat(),
        "person_hash": h_person,
        "unit_internal_hash": h_int,
        "unit_external_hash": h_ext,
        "unit_directory_hash": h_directory,
        "unit_groups_hash": h_groups,
        "search_policy_hash": search_hash,
        "counts": {
            "recipients": total_recipients,
            "person_elements": len(person_elements),
            "unit_internal_elements": len(unit_int_elements),
            "unit_external_elements": len(unit_ext_elements)
        }
    }
    meta_file.write_text(json.dumps(meta_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    # Invalidate cached registry for this tenant
    mgr.invalidate_registry(tid)
    reg = mgr.get_registry(tid)

    return {
        "status": "synced",
        "tenant_id": tid,
        "changes": {
            "person": p_res,
            "unit_internal": int_res,
            "unit_external": ext_res,
            "unit_directory": directory_res
        },
        "total_recipients": total_recipients,
        "search_rows_refreshed": refreshed,
        "registry_version": reg.registry_version,
        "alias_policy_version": reg.alias_policy_version
    }


def _merge_organizations(conn, batch):
    changes = {"added": 0, "updated": 0, "deleted": 0}
    for sphere in ("int_province_comm", "ext_province_comm"):
        elements = [n.model_dump(mode="json", exclude_none=True) for n in batch.elements if n.sphere == sphere]
        result = _diff_and_sync_comm_units(conn, elements, sphere == "int_province_comm", batch.source)
        for key in changes:
            changes[key] += result[key]
    return changes


def sync_tenant_organizations(tenant_id, batch, settings, tenant_manager=None):
    """Import validated directory/search observations without changing personnel."""
    from .contracts import OrganizationBatch
    batch = OrganizationBatch.model_validate(batch)
    tid = normalize_tenant_id(tenant_id, settings.default_tenant)
    mgr = tenant_manager or TenantManager(settings)
    path = mgr.ensure_tenant_initialized(tid)
    conn = sqlite3.connect(path)
    try:
        init_tenant_db(conn)
        with conn:
            changes = _merge_organizations(conn, batch)
        with conn:
            from .registry import Registry
            refresh_search_index(conn, Registry(replace(settings, lookup_db=path)))
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    finally:
        conn.close()
    mgr.invalidate_registry(tid)
    registry = mgr.get_registry(tid)
    return {"status": "synced" if changes["added"] or changes["updated"] else "no_change",
            "tenant_id": tid, "registry_version": registry.registry_version,
            "alias_policy_version": registry.alias_policy_version, "changes": changes}
