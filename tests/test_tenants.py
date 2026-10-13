import sqlite3
from ai_document_sender.config import Settings
from ai_document_sender.tenants import normalize_tenant_id, TenantManager


def test_normalize_tenant_id():
    assert normalize_tenant_id("vpub") == "vpub"
    assert normalize_tenant_id("/vpub/") == "vpub"
    assert normalize_tenant_id("SNNMT") == "snnmt"
    assert normalize_tenant_id(None) == "vpub"
    assert normalize_tenant_id("", default="custom") == "custom"
    assert normalize_tenant_id("tenant!@#_123") == "tenant_123"


def test_tenant_manager_fallback_and_custom_db(settings, tmp_path):
    # settings has a temporary lookup_db created by conftest fixture
    manager = TenantManager(settings)

    # Default tenant returns settings.lookup_db when tenant directory doesn't have its own db yet
    default_db = manager.get_db_path("vpub")
    assert default_db.resolve() == settings.lookup_db.resolve()

    # Registry can be retrieved and cached
    reg1 = manager.get_registry("vpub")
    reg2 = manager.get_registry("vpub")
    assert reg1 is reg2

    # Invalidation clears cache
    manager.invalidate_registry("vpub")
    reg3 = manager.get_registry("vpub")
    assert reg3 is not reg1
    assert reg3.registry_version == reg1.registry_version


def test_isolated_tenant_registries(settings, tmp_path):
    tenants_dir = tmp_path / "tenants"
    settings = Settings(
        lookup_db=settings.lookup_db,
        tenants_dir=tenants_dir,
        policy_path=settings.policy_path,
        runtime_dir=settings.runtime_dir,
        default_tenant="vpub"
    )
    manager = TenantManager(settings)

    # Setup tenant 'snnmt' with distinct database
    snnmt_dir = tenants_dir / "snnmt"
    snnmt_dir.mkdir(parents=True)
    snnmt_db = snnmt_dir / "lookup.db"
    with sqlite3.connect(snnmt_db) as conn:
        conn.execute("CREATE TABLE recipients (recipient_id TEXT PRIMARY KEY, source_id TEXT, name TEXT, full_name TEXT, display_name TEXT, code TEXT, sphere TEXT, recipient_type TEXT, parent_name TEXT, priority_score INT, raw_json TEXT)")
        conn.execute("INSERT INTO recipients VALUES ('snnmt_01', '1', 'Giám đốc Sở', 'Nguyễn Văn A', 'Nguyễn Văn A - Giám đốc Sở', 'SNNMT.01', 'internal', 'INTERNAL_PERSON', 'Lãnh đạo Sở', 100, '{}')")

    reg_vpub = manager.get_registry("vpub")
    reg_snnmt = manager.get_registry("snnmt")

    assert "snnmt_01" not in reg_vpub.by_id
    assert "snnmt_01" in reg_snnmt.by_id
    assert reg_snnmt.registry_version != reg_vpub.registry_version
