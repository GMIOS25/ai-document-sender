import hashlib
import sqlite3
from ai_document_sender.registry import Registry


def test_readonly_and_current_staff_snapshot(settings):
    before = hashlib.sha256(settings.lookup_db.read_bytes()).hexdigest()
    r = Registry(settings)
    assert r.staff_code("V5")[0].name == "Lê Thị Kim Yến"
    assert r.staff_code("V50") == []
    assert hashlib.sha256(settings.lookup_db.read_bytes()).hexdigest() == before
    old = r.registry_version
    with sqlite3.connect(settings.lookup_db) as c:
        c.execute("UPDATE recipients SET full_name='Cán bộ mới', display_name='Cán bộ mới - Chuyên viên V5' WHERE recipient_id='internal_341'")
    updated = Registry(settings)
    assert updated.registry_version != old
    assert updated.staff_code("V5")[0].name == "Cán bộ mới"
    assert r.staff_code("V5")[0].name == "Lê Thị Kim Yến"  # pinned snapshot


def test_duplicate_units_and_search(settings):
    r = Registry(settings)
    assert len(r.exact_name("Báo Gia Lai")) == 2
    assert len(r.exact_role("Chủ tịch UBND tỉnh")) == 1
    assert len(r.exact_role("Phó Chủ tịch UBND tỉnh")) == 2
    assert r.search("Sở Ngoại vụ - tỉnh Gia Lai") == []
    assert all(x.recipient_id in r.by_id for x in r.search("Lịch"))


def test_initials_role_scoped(settings):
    r = Registry(settings)
    assert r.initials("N.T.T.Lịch", "Phó Chủ tịch UBND tỉnh")[0].recipient_id == "internal_278"
    assert r.initials("N.T.T.Lịch", "Chủ tịch UBND tỉnh") == []


def test_verified_overlay_version_and_groups(settings):
    from ai_document_sender.jobs import JobStore
    r=Registry(settings)
    store=JobStore(settings)
    import pytest
    with pytest.raises(ValueError):
        store.import_overlay([{"selector":"Các PCT UBND tỉnh","member_ids":["internal_278"],"verification_status":"pending"}])
    store.import_overlay([{"selector":"Các PCT UBND tỉnh","member_ids":["internal_276","internal_278"],"verification_status":"verified","verified_by":"test-admin","evidence":"Current members checked"}])
    updated=Registry(settings)
    assert updated.registry_version != r.registry_version
    assert updated.alias_policy_version == r.alias_policy_version
    assert {p.recipient_id for p in updated.group_members("Các PCT UBND tỉnh")} == {"internal_276","internal_278"}
    assert not r.group_members("Các PCT UBND tỉnh")


def test_snapshot_readers_release_database_handles(settings):
    from ai_document_sender.jobs import JobStore
    JobStore(settings)
    registry = Registry(settings)
    # Windows refuses rename/unlink while an SQLite reader retains the file handle.
    moved_lookup = settings.lookup_db.with_suffix(".moved.db")
    settings.lookup_db.rename(moved_lookup)
    settings.runtime_db.unlink()
    assert registry.exact_role("Chủ tịch UBND tỉnh")[0].recipient_id == "internal_270"


def test_local_names_preserves_tinh_suffix_without_commune_underscore_collision(settings):
    with sqlite3.connect(settings.lookup_db) as conn:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(recipients)")}
        for rid, code, sphere, rtype, name in [
            ("comm_h21_38", "H21.38", "int_province_comm", "INT_PROVINCE_UNIT", "Ban Quản lý các dự án đầu tư xây dựng tỉnh Gia Lai"),
            ("comm_h21_49", "H21.49", "int_province_comm", "INT_PROVINCE_UNIT", "Trung tâm Phát triển Quỹ đất - tỉnh Gia Lai"),
            ("comm_h21_51_30", "H21.51.30", "ext_province_comm", "EXT_PROVINCE_UNIT", "Ban Quản lý các dự án đầu tư xây dựng_Tỉnh Gia Lai"),
            ("comm_h21_58_17", "H21.58.17", "ext_province_comm", "EXT_PROVINCE_UNIT", "Ban Quản lý các Dự án đầu tư xây dựng_Tỉnh Gia Lai"),
        ]:
            row = {
                "recipient_id": rid, "source_id": rid, "recipient_type": rtype,
                "sphere": sphere, "name": name, "full_name": "", "display_name": name,
                "code": code, "parent_name": "", "rank_level": "", "email": "",
                "priority_score": 10, "search_text": name,
            }
            use_cols = [c for c in row if c in cols]
            conn.execute(
                f"INSERT INTO recipients ({','.join(use_cols)}) VALUES ({','.join('?' * len(use_cols))})",
                [row[c] for c in use_cols],
            )
    registry = Registry(settings)
    assert [r.code for r in registry._local_names.get("ban quan ly cac du an dau tu xay dung tinh", [])] == ["H21.38"]
    assert [r.code for r in registry._local_names.get("trung tam phat trien quy dat tinh", [])] == ["H21.49"]
    assert "ban quan ly cac du an dau tu xay dung_tinh" not in registry._local_names


def test_search_prioritizes_local_jurisdiction_before_limit_and_normalizes_ubnd(settings):
    with sqlite3.connect(settings.lookup_db) as conn:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(recipients)")}
        for i in range(12):
            rid = f"comm_000_ext_{i:02d}"
            name = f"Ban Quản lý các dự án đầu tư xây dựng tỉnh Ngoài {i}"
            row = {
                "recipient_id": rid, "source_id": rid, "recipient_type": "EXT_PROVINCE_UNIT",
                "sphere": "ext_province_comm", "name": name, "full_name": "", "display_name": name,
                "code": f"G99.{i:02d}", "parent_name": "", "rank_level": "", "email": "",
                "priority_score": 10, "search_text": name,
            }
            use_cols = [c for c in row if c in cols]
            conn.execute(
                f"INSERT INTO recipients ({','.join(use_cols)}) VALUES ({','.join('?' * len(use_cols))})",
                [row[c] for c in use_cols],
            )
        for rid, code, sphere, rtype, name in [
            ("comm_zzz_local", "H21.38", "int_province_comm", "INT_PROVINCE_UNIT", "Ban Quản lý các dự án đầu tư xây dựng tỉnh Gia Lai"),
            ("comm_dang_uy", "A21.07", "ext_province_comm", "EXT_PROVINCE_UNIT", "Đảng ủy Ủy ban nhân dân tỉnh Gia Lai"),
        ]:
            row = {
                "recipient_id": rid, "source_id": rid, "recipient_type": rtype,
                "sphere": sphere, "name": name, "full_name": "", "display_name": name,
                "code": code, "parent_name": "", "rank_level": "", "email": "",
                "priority_score": 10, "search_text": name,
            }
            use_cols = [c for c in row if c in cols]
            conn.execute(
                f"INSERT INTO recipients ({','.join(use_cols)}) VALUES ({','.join('?' * len(use_cols))})",
                [row[c] for c in use_cols],
            )
    registry = Registry(settings)
    local_hits = registry.search("Ban Quản lý các DA đầu tư xây dựng tỉnh", limit=10, local_only=True)
    assert [r.code for r in local_hits] == ["H21.38"]
    unfiltered_hits = registry.search("Ban Quản lý các dự án đầu tư xây dựng tỉnh", limit=10)
    assert unfiltered_hits[0].code == "H21.38"
    assert [r.code for r in registry.exact_name("Đảng ủy UBND tỉnh Gia Lai")] == ["A21.07"]
    assert [r.code for r in registry.search("Đảng ủy UBND tỉnh", limit=5)] == ["A21.07"]

