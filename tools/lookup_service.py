"""
Lookup Service: Module cung cấp API và CLI tra cứu Nơi nhận / Người nhận văn bản.
Sử dụng SQLite database (resources/data/lookup.db) kết hợp FTS5 & Ranking.
"""

import sys
import json
import sqlite3
import unicodedata
from pathlib import Path
from typing import List, Dict, Any, Optional

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "resources" / "data" / "lookup.db"


def remove_accents(input_str: str) -> str:
    if not input_str:
        return ""
    s = input_str.replace("đ", "d").replace("Đ", "D")
    nfkd = unicodedata.normalize("NFKD", s)
    return "".join([c for c in nfkd if not unicodedata.combining(c)])


class RecipientLookupService:
    def __init__(self, db_path: Optional[str or Path] = None):
        self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        if not self.db_path.exists():
            raise FileNotFoundError(
                f"Không tìm thấy database tại {self.db_path}. Hãy chạy `python tools/build_lookup_db.py` trước."
            )

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def lookup(
        self,
        query: str,
        sphere: Optional[str] = None,
        recipient_type: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Tra cứu linh hoạt theo từ khóa hoặc mã định danh.
        
        Args:
            query: Từ khóa tìm kiếm (họ tên cán bộ, chức vụ, tên cơ quan, mã code, email...)
            sphere: Lọc theo phân vùng ('internal', 'int_province_comm', 'ext_province_comm')
            recipient_type: Lọc theo loại ('INTERNAL_PERSON', 'INTERNAL_DEPT', 'INT_PROVINCE_UNIT', 'EXT_PROVINCE_UNIT'...)
            limit: Số lượng kết quả tối đa
            
        Returns:
            Danh sách các đối tượng recipient phù hợp nhất
        """
        query = query.strip()
        if not query:
            return []

        no_acc_query = remove_accents(query)
        conn = self._get_connection()
        cur = conn.cursor()

        # 1. Thử tìm kiếm chính xác theo mã CODE hoặc EMAIL trước (độ ưu tiên cao nhất)
        exact_sql = """
        SELECT * FROM recipients 
        WHERE LOWER(code) = LOWER(?) OR LOWER(email) = LOWER(?)
        """
        params = [query, query]
        if sphere:
            exact_sql += " AND sphere = ?"
            params.append(sphere)
        if recipient_type:
            exact_sql += " AND recipient_type = ?"
            params.append(recipient_type)

        cur.execute(exact_sql, params)
        exact_rows = cur.fetchall()
        if exact_rows:
            conn.close()
            return [dict(row) for row in exact_rows[:limit]]

        # 2. Tìm kiếm qua Full-Text Search (FTS5) & LIKE dự phòng
        # Chuẩn bị query cho FTS5: tách các từ, escape các ký tự đặc biệt
        clean_words = [w for w in query.replace('"', '').replace("'", '').split() if w]
        fts_terms = " ".join([f'"{w}"*' for w in clean_words])

        results = []
        seen_ids = set()

        # Truy vấn FTS5 kết hợp join với recipients để lấy điểm ưu tiên priority_score
        try:
            fts_sql = f"""
            SELECT r.*, fts.rank AS fts_rank
            FROM recipients_fts fts
            JOIN recipients r ON fts.recipient_id = r.recipient_id
            WHERE recipients_fts MATCH ?
            """
            fts_params = [fts_terms]

            if sphere:
                fts_sql += " AND r.sphere = ?"
                fts_params.append(sphere)
            if recipient_type:
                fts_sql += " AND r.recipient_type = ?"
                fts_params.append(recipient_type)

            # Ưu tiên theo điểm tần suất priority_score và độ khớp FTS
            fts_sql += " ORDER BY r.priority_score DESC, fts_rank LIMIT ?"
            fts_params.append(limit * 2)

            cur.execute(fts_sql, fts_params)
            for row in cur.fetchall():
                d = dict(row)
                d.pop("fts_rank", None)
                if d["recipient_id"] not in seen_ids:
                    seen_ids.add(d["recipient_id"])
                    results.append(d)
        except Exception:
            # Fallback nếu FTS cú pháp từ khóa có ký tự lạ
            pass

        # 3. Nếu FTS không đủ kết quả, dùng LIKE mở rộng trên cả có dấu và không dấu
        if len(results) < limit:
            like_sql = """
            SELECT * FROM recipients
            WHERE (search_text LIKE ? OR search_text LIKE ?)
            """
            like_params = [f"%{query}%", f"%{no_acc_query}%"]

            if sphere:
                like_sql += " AND sphere = ?"
                like_params.append(sphere)
            if recipient_type:
                like_sql += " AND recipient_type = ?"
                like_params.append(recipient_type)

            like_sql += " ORDER BY priority_score DESC LIMIT ?"
            like_params.append(limit)

            cur.execute(like_sql, like_params)
            for row in cur.fetchall():
                d = dict(row)
                if d["recipient_id"] not in seen_ids:
                    seen_ids.add(d["recipient_id"])
                    results.append(d)
                    if len(results) >= limit:
                        break

        conn.close()
        return results[:limit]

    def get_by_code(self, code: str) -> Optional[Dict[str, Any]]:
        """Lấy chính xác thông tin đơn vị/cán bộ qua mã code (H21.24, G01...)"""
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM recipients WHERE LOWER(code) = LOWER(?) LIMIT 1;", (code.strip(),))
        row = cur.fetchone()
        conn.close()
        return dict(row) if row else None

    def get_internal_org_tree(self) -> Dict[str, Any]:
        """Lấy cấu trúc cây tổ chức nội bộ dạng JSON phân cấp."""
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute("""
        SELECT id, parent_id, type, name, ref_fullname, ref_uname, rank, sign, comm_code
        FROM internal_nodes
        ORDER BY parent_id, order_num;
        """)
        nodes = [dict(row) for row in cur.fetchall()]
        conn.close()

        # Xây dựng cây
        by_parent = {}
        for n in nodes:
            pid = n["parent_id"]
            by_parent.setdefault(pid, []).append(n)

        def build_branch(node):
            nid = node["id"]
            children = by_parent.get(nid, [])
            if children:
                node["children"] = [build_branch(c) for c in children]
            return node

        roots = by_parent.get(0, [])
        return [build_branch(r) for r in roots]

    def get_top_frequent_units(self, sphere: Optional[str] = None, limit: int = 15) -> List[Dict[str, Any]]:
        """Lấy danh sách các cơ quan được gửi văn bản nhiều nhất."""
        conn = self._get_connection()
        cur = conn.cursor()
        sql = "SELECT * FROM comm_units"
        params = []
        if sphere:
            sql += " WHERE sphere = ?"
            params.append(sphere)
        sql += " ORDER BY send_count DESC LIMIT ?;"
        params.append(limit)
        cur.execute(sql, params)
        rows = [dict(row) for row in cur.fetchall()]
        conn.close()
        return rows


def print_search_results(results: List[Dict[str, Any]]):
    if not results:
        print("  Không tìm thấy kết quả nào phù hợp.")
        return

    print(f"  Tìm thấy {len(results)} kết quả:")
    print("-" * 80)
    for idx, r in enumerate(results, 1):
        scope_tag = {
            "internal": "[Nội bộ]",
            "int_province_comm": "[Liên thông Tỉnh]",
            "ext_province_comm": "[Liên thông Ngoài]"
        }.get(r.get("sphere"), "")

        print(f"  {idx}. {scope_tag} {r.get('display_name')}")
        code_str = f"Mã: {r.get('code')}" if r.get('code') else ""
        parent_str = f"Đơn vị: {r.get('parent_name')}" if r.get('parent_name') else ""
        priority = f"Điểm ưu tiên: {r.get('priority_score')}"
        info = " | ".join(filter(None, [code_str, parent_str, priority]))
        print(f"     -> {info}")
    print("-" * 80)


if __name__ == "__main__":
    service = RecipientLookupService()

    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        print(f"\n[?] Tra cứu với từ khóa: '{query}'")
        res = service.lookup(query, limit=10)
        print_search_results(res)
    else:
        # Chạy demo một số ca tra cứu tiêu biểu
        test_queries = [
            "Phạm Anh Tuấn",              # Tìm lãnh đạo nội bộ theo họ tên
            "Chủ tịch UBND tỉnh",         # Tìm theo chức vụ
            "Sở Nông nghiệp",             # Tìm Sở liên thông nội tỉnh
            "H21.24",                     # Tìm đích danh theo mã định danh
            "Bộ Công an",                 # Tìm Bộ ngành ngoại tỉnh
            "so tu phap",                 # Tìm không dấu
            "Kho bạc Nhà nước",           # Cơ quan ngành dọc
        ]

        print("=" * 80)
        print("CHẠY THỬ NGHIỆM LOOKUP SERVICE")
        print("=" * 80)

        for q in test_queries:
            print(f"\n>>> Query: '{q}'")
            results = service.lookup(q, limit=3)
            print_search_results(results)
