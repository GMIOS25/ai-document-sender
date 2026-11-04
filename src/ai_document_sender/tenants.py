"""Multi-tenant management and isolated registry snapshot caching."""
from dataclasses import replace
from pathlib import Path
import re
import shutil
from typing import Dict, Optional

from .config import Settings
from .registry import Registry


def normalize_tenant_id(raw: Optional[str], default: str = "vpub") -> str:
    """Normalize tenant identifier to safe lowercase alphanumeric string."""
    cleaned = re.sub(r"[^a-z0-9_-]", "", (raw or "").strip().lower())
    return cleaned if cleaned else default.strip().lower()


class TenantManager:
    """Manages tenant directories, database files, and in-memory registry caches."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._registry_cache: Dict[str, Registry] = {}

    def get_tenant_dir(self, tenant_id: str) -> Path:
        tid = normalize_tenant_id(tenant_id, self.settings.default_tenant)
        return self.settings.tenants_dir / tid

    def ensure_tenant_initialized(self, tenant_id: str) -> Path:
        """Ensure tenant directory and database file exist.
        
        If tenant is the default tenant (e.g. 'vpub') and tenant directory does not have lookup.db,
        but legacy lookup_db exists, copy legacy lookup_db into tenant directory.
        """
        tenant_dir = self.get_tenant_dir(tenant_id)
        tenant_dir.mkdir(parents=True, exist_ok=True)
        db_path = tenant_dir / "lookup.db"

        tid = normalize_tenant_id(tenant_id, self.settings.default_tenant)
        if not db_path.exists() and tid == normalize_tenant_id(self.settings.default_tenant):
            if self.settings.lookup_db.exists():
                shutil.copy2(self.settings.lookup_db, db_path)
                from .learning import FILENAME
                legacy_learning = self.settings.lookup_db.parent / FILENAME
                tenant_learning = tenant_dir / FILENAME
                if legacy_learning.exists() and not tenant_learning.exists():
                    shutil.copy2(legacy_learning, tenant_learning)

        return db_path

    def get_db_path(self, tenant_id: str) -> Path:
        """Resolve database path for tenant, initializing empty database if new."""
        tid = normalize_tenant_id(tenant_id, self.settings.default_tenant)
        tenant_dir = self.get_tenant_dir(tid)
        tenant_db = tenant_dir / "lookup.db"
        if tenant_db.exists():
            return tenant_db
        if tid == normalize_tenant_id(self.settings.default_tenant) and self.settings.lookup_db.exists():
            return self.settings.lookup_db

        tenant_dir.mkdir(parents=True, exist_ok=True)
        import sqlite3
        from .sync import init_tenant_db
        conn = sqlite3.connect(str(tenant_db))
        try:
            init_tenant_db(conn)
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
        finally:
            conn.close()
        return tenant_db

    def get_registry(self, tenant_id: str) -> Registry:
        """Retrieve cached Registry for tenant or instantiate fresh snapshot if DB or policy changed."""
        tid = normalize_tenant_id(tenant_id, self.settings.default_tenant)
        db_path = self.get_db_path(tid)
        db_mtime = db_path.stat().st_mtime if db_path.exists() else 0
        policy_mtime = self.settings.policy_path.stat().st_mtime if self.settings.policy_path.exists() else 0
        from .learning import FILENAME
        learning_path = db_path.parent / FILENAME
        learning_stamp = (learning_path.stat().st_mtime_ns, learning_path.stat().st_size) if learning_path.exists() else None
        cache_key = (db_mtime, policy_mtime, learning_stamp)

        cached = self._registry_cache.get(tid)
        if cached and cached[0] == cache_key:
            return cached[1]

        tenant_settings = replace(self.settings, lookup_db=db_path)
        registry = Registry(tenant_settings)
        registry.tenant_id = tid
        self._registry_cache[tid] = (cache_key, registry)
        return registry

    def invalidate_registry(self, tenant_id: str) -> None:
        """Evict tenant registry from in-memory cache upon directory update."""
        tid = normalize_tenant_id(tenant_id, self.settings.default_tenant)
        self._registry_cache.pop(tid, None)

    def list_tenants(self) -> list[str]:
        """List active tenant IDs."""
        tenants = set()
        if self.settings.tenants_dir.exists():
            for p in self.settings.tenants_dir.iterdir():
                if p.is_dir() and (p / "lookup.db").exists():
                    tenants.add(p.name)
        if self.settings.lookup_db.exists():
            tenants.add(normalize_tenant_id(self.settings.default_tenant))
        return sorted(tenants)
