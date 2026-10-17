import json
import sqlite3
import pytest
from ai_document_sender.config import Settings


def row(rid, role, person=None, code="", sphere="internal", kind=None, parent="Lãnh đạo UBND tỉnh"):
    return dict(recipient_id=rid, source_id=rid.removeprefix("internal_"), name=role,
                full_name=person, display_name=f"{person} - {role}" if person else role, code=code,
                sphere=sphere, recipient_type=kind or ("INTERNAL_PERSON" if person else "INT_PROVINCE_UNIT"),
                parent_name=parent, priority_score=0, raw_json="{}")


@pytest.fixture
def settings(tmp_path):
    db = tmp_path / "lookup.db"
    c = sqlite3.connect(db)
    c.execute('CREATE TABLE recipients (recipient_id TEXT PRIMARY KEY, source_id TEXT, name TEXT, full_name TEXT, display_name TEXT, code TEXT, sphere TEXT, recipient_type TEXT, parent_name TEXT, priority_score INT, raw_json TEXT)')
    rows = [row("internal_270", "Chủ tịch UBND tỉnh", "Phạm Anh Tuấn", "tuanpa@vpub.gialai.gov.vn"),
            row("internal_278", "Phó Chủ tịch UBND tỉnh", "Nguyễn Thị Thanh Lịch", "lichntt@vpub.gialai.gov.vn"),
            row("internal_276", "Phó Chủ tịch UBND tỉnh", "Lâm Hải Giang", "gianglh@vpub.gialai.gov.vn"),
            row("internal_287", "Chánh Văn phòng UBND tỉnh", "Nguyễn Xuân Vĩnh", "vinhnx@vpub.gialai.gov.vn", parent="Lãnh đạo Văn phòng UBND tỉnh"),
            row("internal_297", "Phó Chánh Văn phòng", "Trương Công Hoài", "hoaitc@vpub.gialai.gov.vn", parent="Lãnh đạo Văn phòng UBND tỉnh"),
            row("internal_293", "Phó Chánh Văn phòng", "Võ Gia Nghĩa", "nghiavg@vpub.gialai.gov.vn", parent="Lãnh đạo Văn phòng UBND tỉnh"),
            row("internal_491", "Trưởng phòng V1", "Nguyễn Hoàng Đan", "danhnh@vpub.gialai.gov.vn", parent="Phòng Khoa giáo Văn xã"),
            row("internal_341", "Chuyên viên V5", "Lê Thị Kim Yến", "yenltk@vpub.gialai.gov.vn", parent="Phòng Khoa giáo Văn xã"),
            row("internal_485", "Chuyên viên V8", "Trần Duy Khánh", "khanhtd@vpub.gialai.gov.vn", parent="Phòng Khoa giáo Văn xã"),
            row("internal_343", "Chuyên viên V4", "Lê Thanh Sơn", parent="Phòng Khoa giáo Văn xã"),
            row("internal_489", "Chuyên viên V6", "Đoàn Thị Minh Hiếu", parent="Phòng Khoa giáo Văn xã"),
            row("internal_332", "Chuyên viên C4", "Văn Kim Thành", parent="Phòng Nội chính"),
            row("internal_451", "Chuyên viên C7", "Lê Ngọc Ngân", parent="Phòng Nội chính"),
            row("comm_news_1", "Báo Gia Lai", code="H21.94", sphere="int_province_comm"),
            row("comm_news_2", "Báo Gia Lai", code="A21.11", sphere="ext_province_comm", kind="EXT_PROVINCE_UNIT"),
            row("comm_culture", "Sở Văn hóa, Thể thao và Du lịch - tỉnh Gia Lai", code="H21.17", sphere="int_province_comm"),
            row("comm_interior", "Sở Nội vụ - tỉnh Gia Lai", code="H21.11", sphere="int_province_comm")]
    for r in rows:
        c.execute('INSERT INTO recipients VALUES (?,?,?,?,?,?,?,?,?,?,?)', tuple(r.values()))
    c.commit(); c.close()
    from pathlib import Path
    policy = Path(__file__).resolve().parents[1] / "resources/policies/recipient_aliases.v1.json"
    return Settings(lookup_db=db, tenants_dir=tmp_path / "tenants", policy_path=policy, runtime_dir=tmp_path / "runtime", worker_enabled=False)
