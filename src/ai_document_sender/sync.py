"""Smart Sync Diff Engine for updating tenant lookup databases and FTS5 indices."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
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
}


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
                for abbr, full_forms in ABBREVIATIONS.items():
                    if abbr.lower() in val.lower():
                        tokens.extend(full_forms)
    return " ".join(tokens)


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


def _diff_and_sync_comm_units(
    conn: sqlite3.Connection,
    elements: list,
    is_internal: bool
) -> Dict[str, int]:
    """Smart diff and sync for organizational units."""
    sphere = "int_province_comm" if is_internal else "ext_province_comm"
    recipient_type = "INT_PROVINCE_UNIT" if is_internal else "EXT_PROVINCE_UNIT"
    parent_scope = "Nội tỉnh Gia Lai" if is_internal else "Khối Ngoài tỉnh / Bộ ngành Trung ương"

    # Deduplicate incoming elements by code, choosing highest send_count
    incoming_by_code: Dict[str, dict] = {}
    for e in elements:
        code = str(e.get("code") or "").strip()
        if not code:
            continue
        count = int(e.get("count") or 0)
        if code not in incoming_by_code:
            incoming_by_code[code] = e
        else:
            old_count = int(incoming_by_code[code].get("count") or 0)
            if count > old_count:
                incoming_by_code[code] = e

    cur = conn.cursor()
    # Fetch existing records for this sphere
    cur.execute("SELECT uuid, code, name, send_count, organ_id, username, alias_code, raw_json FROM comm_units WHERE sphere = ?", (sphere,))
    existing_rows = cur.fetchall()
    existing_by_code = {row[1]: row for row in existing_rows}

    added = 0
    updated = 0
    deleted = 0

    # 1. Identify Deletions
    incoming_codes = set(incoming_by_code.keys())
    existing_codes = set(existing_by_code.keys())
    deleted_codes = existing_codes - incoming_codes

    for code in deleted_codes:
        row = existing_by_code[code]
        uuid = row[0]
        cur.execute("DELETE FROM comm_units WHERE uuid = ?", (uuid,))
        cur.execute("DELETE FROM recipients WHERE recipient_id = ?", (f"comm_{uuid}",))
        cur.execute("DELETE FROM recipients_fts WHERE recipient_id = ?", (f"comm_{uuid}",))
        deleted += 1

    # 2. Identify Inserts and Updates
    for code, e in incoming_by_code.items():
        uuid = str(e.get("uuid") or "").strip()
        name = str(e.get("name") or "").strip()
        count = int(e.get("count") or 0)
        organ_id = e.get("organId")
        uname = e.get("username")
        alias_code = e.get("aliasCode")
        raw_json = json.dumps(e, ensure_ascii=False)

        recipient_id = f"comm_{uuid}"
        search_text = build_search_tokens(name, code, parent_scope)

        if code not in existing_by_code:
            # INSERT
            cur.execute("""
            INSERT OR REPLACE INTO comm_units (
                uuid, code, name, sphere, send_count, organ_id, username, alias_code, raw_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (uuid, code, name, sphere, count, organ_id, uname, alias_code, raw_json))

            cur.execute("""
            INSERT OR REPLACE INTO recipients (
                recipient_id, source_id, recipient_type, sphere, name,
                full_name, display_name, code, parent_name, rank_level,
                email, priority_score, search_text, raw_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                recipient_id, uuid, recipient_type, sphere, name,
                None, name, code, parent_scope, None,
                None, count, search_text, raw_json
            ))

            cur.execute("""
            INSERT INTO recipients_fts (
                recipient_id, display_name, full_name, name, code, parent_name, search_text
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (recipient_id, name, "", name, code, parent_scope, search_text))
            added += 1
        else:
            old_row = existing_by_code[code]
            # Check if updated (name, send_count, organ_id, username, uuid)
            old_uuid, _, old_name, old_count, old_organ, old_uname, old_alias, _ = old_row
            if (old_uuid != uuid or old_name != name or old_count != count or
                old_organ != organ_id or old_uname != uname or old_alias != alias_code):
                
                # Delete old recipients row if uuid changed
                if old_uuid != uuid:
                    cur.execute("DELETE FROM comm_units WHERE uuid = ?", (old_uuid,))
                    cur.execute("DELETE FROM recipients WHERE recipient_id = ?", (f"comm_{old_uuid}",))
                    cur.execute("DELETE FROM recipients_fts WHERE recipient_id = ?", (f"comm_{old_uuid}",))

                cur.execute("""
                INSERT OR REPLACE INTO comm_units (
                    uuid, code, name, sphere, send_count, organ_id, username, alias_code, raw_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (uuid, code, name, sphere, count, organ_id, uname, alias_code, raw_json))

                cur.execute("""
                INSERT OR REPLACE INTO recipients (
                    recipient_id, source_id, recipient_type, sphere, name,
                    full_name, display_name, code, parent_name, rank_level,
                    email, priority_score, search_text, raw_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    recipient_id, uuid, recipient_type, sphere, name,
                    None, name, code, parent_scope, None,
                    None, count, search_text, raw_json
                ))

                cur.execute("DELETE FROM recipients_fts WHERE recipient_id = ?", (recipient_id,))
                cur.execute("""
                INSERT INTO recipients_fts (
                    recipient_id, display_name, full_name, name, code, parent_name, search_text
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (recipient_id, name, "", name, code, parent_scope, search_text))
                updated += 1

    return {"added": added, "updated": updated, "deleted": deleted}


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
    tid = normalize_tenant_id(tenant_id, settings.default_tenant)
    mgr = tenant_manager or TenantManager(settings)

    tenant_dir = mgr.get_tenant_dir(tid)
    tenant_dir.mkdir(parents=True, exist_ok=True)
    db_path = tenant_dir / "lookup.db"

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

    meta_file = tenant_dir / "metadata.json"
    if meta_file.exists() and db_path.exists():
        try:
            meta = json.loads(meta_file.read_text(encoding="utf-8"))
            if (meta.get("person_hash") == h_person and
                meta.get("unit_internal_hash") == h_int and
                meta.get("unit_external_hash") == h_ext):
                # No change detected
                reg = mgr.get_registry(tid)
                return {
                    "status": "no_change",
                    "tenant_id": tid,
                    "message": "Datasets unchanged; lookup database is up to date.",
                    "registry_version": reg.registry_version
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
            "unit_external": ext_res
        },
        "total_recipients": total_recipients,
        "registry_version": reg.registry_version
    }
