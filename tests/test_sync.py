from pathlib import Path
import sqlite3
from ai_document_sender.config import Settings
from ai_document_sender.sync import sync_tenant_lookup
from ai_document_sender.tenants import TenantManager


def test_smart_sync_lifecycle(tmp_path):
    tenants_dir = tmp_path / "tenants"
    settings = Settings(
        lookup_db=tmp_path / "legacy.db",
        tenants_dir=tenants_dir,
        policy_path=Path(__file__).resolve().parents[1] / "resources/policies/recipient_aliases.v1.json",
        runtime_dir=tmp_path / "runtime",
        default_tenant="vpub"
    )
    manager = TenantManager(settings)

    sample_person = [
        {
            "id": 101,
            "parent": 0,
            "type": "dept",
            "name": "Lãnh đạo Sở",
            "order": 1
        },
        {
            "id": 102,
            "parent": 101,
            "type": "alias",
            "name": "Giám đốc Sở",
            "refFullname": "Trần Văn An",
            "refUname": "antv@snnmt.gialai.gov.vn",
            "rank": "leader",
            "order": 1
        }
    ]

    sample_internal = [
        {
            "code": "H21.24",
            "name": "Sở Nông nghiệp và Môi trường - tỉnh Gia Lai",
            "count": 100,
            "uuid": "uuid_int_1"
        }
    ]

    sample_external = [
        {
            "code": "A21.11",
            "name": "Báo Gia Lai",
            "count": 50,
            "uuid": "uuid_ext_1"
        }
    ]

    payload = {
        "person": {"elements": sample_person},
        "unit_internal": {"elements": sample_internal},
        "unit_external": {"elements": sample_external}
    }

    # 1. Initial Sync
    res1 = sync_tenant_lookup("snnmt", payload, settings, manager)
    assert res1["status"] == "synced"
    assert res1["tenant_id"] == "snnmt"
    assert res1["changes"]["person"]["added"] == 2
    assert res1["changes"]["unit_internal"]["added"] == 1
    assert res1["changes"]["unit_external"]["added"] == 1
    assert res1["total_recipients"] == 4

    # Verify FTS search works
    reg = manager.get_registry("snnmt")
    assert any("Trần Văn An" in r.display_name for r in reg.search("Trần Văn An"))
    assert any("Báo Gia Lai" in r.name for r in reg.search("Báo Gia Lai"))

    # 2. No-change repeat sync
    res2 = sync_tenant_lookup("snnmt", payload, settings, manager)
    assert res2["status"] == "no_change"
    assert res2["tenant_id"] == "snnmt"

    # 3. Update existing element and add new element
    sample_internal_updated = [
        {
            "code": "H21.24",
            "name": "Sở Nông nghiệp và Môi trường - tỉnh Gia Lai (Cập nhật)",
            "count": 150,
            "uuid": "uuid_int_1"
        },
        {
            "code": "H21.99",
            "name": "Trung tâm Khuyến nông",
            "count": 20,
            "uuid": "uuid_int_2"
        }
    ]
    payload_updated = {
        "person": {"elements": sample_person},
        "unit_internal": {"elements": sample_internal_updated},
        "unit_external": {"elements": sample_external}
    }
    res3 = sync_tenant_lookup("snnmt", payload_updated, settings, manager)
    assert res3["status"] == "synced"
    assert res3["changes"]["unit_internal"]["updated"] == 1
    assert res3["changes"]["unit_internal"]["added"] == 1
    assert res3["total_recipients"] == 5

    reg_updated = manager.get_registry("snnmt")
    assert any("Trung tâm Khuyến nông" in r.name for r in reg_updated.search("Khuyến nông"))

    # 4. Delete element
    payload_deleted = {
        "person": {"elements": sample_person},
        "unit_internal": {"elements": [sample_internal_updated[0]]},  # removed H21.99
        "unit_external": {"elements": sample_external}
    }
    res4 = sync_tenant_lookup("snnmt", payload_deleted, settings, manager)
    assert res4["status"] == "synced"
    assert res4["changes"]["unit_internal"]["deleted"] == 1
    assert res4["total_recipients"] == 4

    reg_after_del = manager.get_registry("snnmt")
    assert not any("Trung tâm Khuyến nông" in r.name for r in reg_after_del.search("Khuyến nông"))
