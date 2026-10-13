"""
Script tạo và chuẩn hóa Cơ sở dữ liệu Lookup từ 3 file JSON:
- person.json (Cơ cấu tổ chức & Cán bộ nội bộ UBND tỉnh Gia Lai)
- unit_internal_province.json (Đơn vị liên thông nội tỉnh)
- unit_except_provice.json (Đơn vị liên thông ngoại tỉnh / Bộ ngành)

Database đích: resources/data/lookup.db (SQLite + FTS5)
"""

import os
import sys
import json
import sqlite3
import unicodedata
from pathlib import Path
from collections import Counter

# Đảm bảo in UTF-8 trên Windows console
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def remove_accents(input_str: str) -> str:
    """Chuyển chuỗi tiếng Việt có dấu thành không dấu chuẩn."""
    if not input_str:
        return ""
    s = input_str.replace("đ", "d").replace("Đ", "D")
    nfkd = unicodedata.normalize("NFKD", s)
    return "".join([c for c in nfkd if not unicodedata.combining(c)])


# Từ điển viết tắt hành chính phổ biến để mở rộng từ khóa tìm kiếm
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
    """Tạo chuỗi từ khóa tìm kiếm gồm cả có dấu, không dấu, viết tắt và dạng viết đầy đủ."""
    tokens = []
    for arg in args:
        if arg:
            val = str(arg).strip()
            if val:
                tokens.append(val)
                no_acc = remove_accents(val)
                if no_acc != val:
                    tokens.append(no_acc)
                
                # Mở rộng từ viết tắt sang dạng đầy đủ
                for abbr, full_forms in ABBREVIATIONS.items():
                    if abbr.lower() in val.lower():
                        tokens.extend(full_forms)
    return " ".join(tokens)


def init_database(db_path: Path):
    """Khởi tạo cấu trúc các bảng và chỉ mục trong SQLite."""
    if db_path.exists():
        try:
            for suffix in ["", "-wal", "-shm"]:
                p = db_path.with_name(db_path.name + suffix) if suffix else db_path
                if p.exists():
                    p.unlink()
            print(f"[*] Đã xóa database cũ tại {db_path.name}")
        except Exception as e:
            print(f"[!] Không thể xóa file DB cũ ({e}), sẽ làm sạch các bảng hiện có.")

    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    cur = conn.cursor()

    # Làm sạch các bảng/views nếu DB đã tồn tại
    cur.execute("DROP VIEW IF EXISTS v_internal_org_tree;")
    cur.execute("DROP VIEW IF EXISTS v_top_frequent_units;")
    cur.execute("DROP TABLE IF EXISTS recipients_fts;")
    cur.execute("DROP TABLE IF EXISTS recipients;")
    cur.execute("DROP TABLE IF EXISTS comm_units;")
    cur.execute("DROP TABLE IF EXISTS internal_nodes;")

    # 1. Bảng lưu trữ cây tổ chức nội bộ (Internal Org Tree)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS internal_nodes (
        id INTEGER PRIMARY KEY,
        parent_id INTEGER NOT NULL DEFAULT 0,
        type TEXT NOT NULL,                  -- 'unit', 'dept', 'group', 'alias'
        name TEXT NOT NULL,                  -- Tên cơ quan, phòng ban hoặc chức vụ
        ref_fullname TEXT,                   -- Họ tên cán bộ (nếu là alias)
        ref_uname TEXT,                      -- Tài khoản/Email cán bộ
        rank TEXT,                           -- 'org_leader', 'leader', 'specialist', ...
        sign TEXT,                           -- Chữ ký tắt (UBND, KTTH, NNMT...)
        comm_code TEXT,                      -- Mã định danh cơ quan (H21, H21.21.01...)
        unit_code TEXT,                      -- UUID đơn vị trong hệ thống
        order_num INTEGER DEFAULT 0,
        raw_json TEXT
    );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_internal_parent ON internal_nodes(parent_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_internal_type ON internal_nodes(type);")

    # 2. Bảng lưu trữ các đơn vị liên thông (Nội tỉnh & Ngoại tỉnh)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS comm_units (
        uuid TEXT PRIMARY KEY,
        code TEXT NOT NULL,                  -- Mã liên thông (H21.24, G01, ...)
        name TEXT NOT NULL,                  -- Tên cơ quan, đơn vị
        sphere TEXT NOT NULL,                -- 'int_province_comm' hoặc 'ext_province_comm'
        send_count INTEGER DEFAULT 0,        -- Tần suất gửi văn bản
        organ_id TEXT,                       -- H21
        username TEXT,                       -- vanthu@vpub.gialai.gov.vn
        alias_code TEXT,
        raw_json TEXT
    );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_comm_code ON comm_units(code);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_comm_sphere ON comm_units(sphere);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_comm_count ON comm_units(send_count DESC);")

    # 3. BẢNG TRA CỨU HỢP NHẤT (Unified Recipients Registry)
    # Phục vụ AI Router, Auto Sender và tìm kiếm nhanh (Autocomplete / Full-Text Search)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS recipients (
        recipient_id TEXT PRIMARY KEY,       -- ID duy nhất (uuid hoặc 'internal_<id>')
        source_id TEXT NOT NULL,             -- ID gốc trong file (id số hoặc uuid)
        recipient_type TEXT NOT NULL,        -- 'INTERNAL_PERSON', 'INTERNAL_DEPT', 'INTERNAL_GROUP', 'INT_PROVINCE_UNIT', 'EXT_PROVINCE_UNIT'
        sphere TEXT NOT NULL,                -- 'internal', 'int_province_comm', 'ext_province_comm'
        name TEXT NOT NULL,                  -- Tên cơ quan/phòng ban hoặc chức vụ
        full_name TEXT,                      -- Họ tên người (đối với person)
        display_name TEXT NOT NULL,          -- Tên hiển thị đầy đủ, rõ nghĩa
        code TEXT,                           -- Mã định danh liên thông hoặc tài khoản nội bộ
        parent_name TEXT,                    -- Cơ quan / Phòng ban trực thuộc
        rank_level TEXT,                     -- Cấp bậc lãnh đạo
        email TEXT,                          -- Email cán bộ
        priority_score INTEGER DEFAULT 0,    -- Điểm ưu tiên sắp xếp (count hoặc bậc lãnh đạo)
        search_text TEXT,                    -- Chuỗi tổng hợp có dấu + không dấu để search
        raw_json TEXT
    );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_recip_type ON recipients(recipient_type);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_recip_sphere ON recipients(sphere);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_recip_code ON recipients(code);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_recip_priority ON recipients(priority_score DESC);")

    # 4. FTS5 Virtual Table phục vụ Full-Text Search siêu tốc
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

    conn.commit()
    return conn


def populate_internal_org(conn: sqlite3.Connection, person_json_path: Path):
    """Nạp dữ liệu từ person.json vào internal_nodes và recipients."""
    with open(person_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    elements = data.get("elements", [])
    print(f"[*] Đọc {len(elements)} bản ghi từ {person_json_path.name}")

    id_map = {e["id"]: e for e in elements}
    cur = conn.cursor()

    # 1. Lưu vào bảng internal_nodes
    for e in elements:
        cur.execute("""
        INSERT INTO internal_nodes (
            id, parent_id, type, name, ref_fullname, ref_uname,
            rank, sign, comm_code, unit_code, order_num, raw_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            e.get("id"),
            e.get("parent", 0),
            e.get("type", ""),
            e.get("name", "").strip(),
            e.get("refFullname"),
            e.get("refUname"),
            e.get("rank"),
            e.get("sign"),
            e.get("commCode"),
            e.get("unitCode"),
            e.get("order", 0),
            json.dumps(e, ensure_ascii=False)
        ))

    # 2. Chuyển đổi đưa vào bảng recipients
    recipients_count = 0
    for e in elements:
        eid = e.get("id")
        etype = e.get("type", "")
        ename = e.get("name", "").strip()
        pid = e.get("parent", 0)
        parent_node = id_map.get(pid)
        parent_name = parent_node.get("name", "").strip() if parent_node else ""

        recipient_id = f"internal_{eid}"
        rank = e.get("rank", "")
        fullname = e.get("refFullname")
        uname = e.get("refUname")
        sign = e.get("sign", "")
        code = uname or e.get("commCode") or sign or ""

        # Tính điểm ưu tiên ranking
        if rank == "org_leader":
            priority = 50000 - e.get("order", 0) * 10
        elif rank == "unit_leader":
            priority = 40000 - e.get("order", 0) * 10
        elif rank == "leader":
            priority = 30000 - e.get("order", 0) * 10
        elif rank == "specialist":
            priority = 10000 - e.get("order", 0) * 10
        elif etype in ["dept", "group"]:
            priority = 20000 - e.get("order", 0) * 10
        else:
            priority = 5000

        # Phân loại recipient_type và định dạng display_name
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

        cur.execute("""
        INSERT INTO recipients (
            recipient_id, source_id, recipient_type, sphere, name,
            full_name, display_name, code, parent_name, rank_level,
            email, priority_score, search_text, raw_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            recipient_id,
            str(eid),
            recipient_type,
            "internal",
            ename,
            fullname,
            display_name,
            code,
            parent_name,
            rank,
            uname,
            priority,
            search_text,
            json.dumps(e, ensure_ascii=False)
        ))

        # Đẩy vào FTS5
        cur.execute("""
        INSERT INTO recipients_fts (
            recipient_id, display_name, full_name, name, code, parent_name, search_text
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            recipient_id, display_name, fullname or "", ename, code, parent_name, search_text
        ))
        recipients_count += 1

    conn.commit()
    print(f"  [+] Đã nạp {recipients_count} bản ghi nội bộ vào recipients & FTS")


def populate_comm_units(conn: sqlite3.Connection, json_path: Path, is_internal: bool):
    """Nạp dữ liệu từ unit_internal_province.json hoặc unit_except_provice.json."""
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    elements = data.get("elements", [])
    sphere = "int_province_comm" if is_internal else "ext_province_comm"
    recipient_type = "INT_PROVINCE_UNIT" if is_internal else "EXT_PROVINCE_UNIT"
    parent_scope = "Nội tỉnh Gia Lai" if is_internal else "Khối Ngoài tỉnh / Bộ ngành Trung ương"

    print(f"[*] Đọc {len(elements)} bản ghi từ {json_path.name} ({sphere})")

    # Xử lý khử trùng lặp (deduplication) dựa trên mã code, ưu tiên bản ghi có count cao nhất
    elements_by_code = {}
    for e in elements:
        code = e.get("code", "").strip()
        count = int(e.get("count") or 0)
        if code not in elements_by_code:
            elements_by_code[code] = e
        else:
            old_count = int(elements_by_code[code].get("count") or 0)
            if count > old_count:
                elements_by_code[code] = e

    print(f"  [i] Khử trùng lặp: từ {len(elements)} bản ghi còn {len(elements_by_code)} đơn vị duy nhất.")

    cur = conn.cursor()
    inserted_count = 0
    for code, e in elements_by_code.items():
        uuid = e.get("uuid", "").strip()
        name = e.get("name", "").strip()
        count = int(e.get("count") or 0)
        organ_id = e.get("organId")
        uname = e.get("username")
        alias_code = e.get("aliasCode")

        # 1. Lưu vào bảng comm_units
        cur.execute("""
        INSERT OR REPLACE INTO comm_units (
            uuid, code, name, sphere, send_count, organ_id, username, alias_code, raw_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            uuid, code, name, sphere, count, organ_id, uname, alias_code,
            json.dumps(e, ensure_ascii=False)
        ))

        # 2. Lưu vào bảng tra cứu thống nhất recipients
        recipient_id = f"comm_{uuid}"
        display_name = name
        search_text = build_search_tokens(name, code, parent_scope)

        cur.execute("""
        INSERT OR REPLACE INTO recipients (
            recipient_id, source_id, recipient_type, sphere, name,
            full_name, display_name, code, parent_name, rank_level,
            email, priority_score, search_text, raw_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            recipient_id,
            uuid,
            recipient_type,
            sphere,
            name,
            None,
            display_name,
            code,
            parent_scope,
            None,
            None,
            count,
            search_text,
            json.dumps(e, ensure_ascii=False)
        ))

        # Đẩy vào FTS5
        cur.execute("""
        INSERT INTO recipients_fts (
            recipient_id, display_name, full_name, name, code, parent_name, search_text
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            recipient_id, display_name, "", name, code, parent_scope, search_text
        ))
        inserted_count += 1

    conn.commit()
    print(f"  [+] Đã nạp {inserted_count} đơn vị liên thông vào recipients & FTS")


def create_useful_views(conn: sqlite3.Connection):
    """Tạo các View tiện ích cho việc truy vấn báo cáo và tra cứu."""
    cur = conn.cursor()

    # View Cây tổ chức nội bộ đầy đủ thông tin cha-con
    cur.execute("""
    CREATE VIEW IF NOT EXISTS v_internal_org_tree AS
    SELECT 
        child.id,
        child.parent_id,
        child.type,
        child.name AS title_or_dept,
        child.ref_fullname AS person_name,
        child.ref_uname AS email_uname,
        child.rank,
        child.sign,
        parent.name AS parent_name,
        parent.type AS parent_type
    FROM internal_nodes child
    LEFT JOIN internal_nodes parent ON child.parent_id = parent.id
    ORDER BY child.parent_id, child.order_num;
    """)

    # View Các đơn vị liên thông được gửi nhiều nhất
    cur.execute("""
    CREATE VIEW IF NOT EXISTS v_top_frequent_units AS
    SELECT 
        code,
        name,
        sphere,
        send_count,
        uuid
    FROM comm_units
    ORDER BY send_count DESC;
    """)

    conn.commit()
    print("[*] Đã tạo các SQL Views: v_internal_org_tree, v_top_frequent_units")


def main():
    base_dir = Path(__file__).resolve().parent.parent
    data_dir = base_dir / "resources" / "data"
    person_file = data_dir / "person.json"
    int_file = data_dir / "unit_internal_province.json"
    ext_file = data_dir / "unit_except_provice.json"
    db_file = data_dir / "lookup.db"

    print("=" * 60)
    print("BẮT ĐẦU XÂY DỰNG DATABASE LOOKUP VĂN BẢN")
    print(f"Thư mục dữ liệu: {data_dir}")
    print(f"Database đích:   {db_file}")
    print("=" * 60)

    # 1. Khởi tạo DB & Schemas
    conn = init_database(db_file)

    # 2. Nạp dữ liệu nội bộ
    populate_internal_org(conn, person_file)

    # 3. Nạp dữ liệu đơn vị nội tỉnh
    populate_comm_units(conn, int_file, is_internal=True)

    # 4. Nạp dữ liệu đơn vị ngoại tỉnh
    populate_comm_units(conn, ext_file, is_internal=False)

    # 5. Tạo Views
    create_useful_views(conn)

    # 6. Thống kê tổng kết
    cur = conn.cursor()
    cur.execute("SELECT recipient_type, COUNT(*) FROM recipients GROUP BY recipient_type;")
    stats = cur.fetchall()
    cur.execute("SELECT COUNT(*) FROM recipients;")
    total = cur.fetchone()[0]

    print("\n" + "=" * 60)
    print(f"HOÀN TẤT XÂY DỰNG DATABASE! Tổng số bản ghi tra cứu: {total}")
    for r_type, count in stats:
        print(f"  - {r_type:<25}: {count:>5} bản ghi")
    print("=" * 60)

    conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
    conn.close()


if __name__ == "__main__":
    main()
