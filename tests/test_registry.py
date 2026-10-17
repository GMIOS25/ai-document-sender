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
