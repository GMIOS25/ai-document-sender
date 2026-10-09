"""Explicit environment configuration; importing does not load secrets."""
from dataclasses import dataclass, field
from pathlib import Path
import os
import ipaddress
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    lookup_db: Path = ROOT / "resources/data/lookup.db"
    policy_path: Path = ROOT / "resources/policies/recipient_aliases.v1.json"
    runtime_dir: Path = ROOT / "var"
    host: str = "127.0.0.1"
    port: int = 8001
    api_key: str = field(default="",repr=False)
    provider_mode: str = "offline"
    openrouter_api_key: str = field(default="",repr=False)
    openrouter_text_model: str = ""
    openrouter_vision_model: str = ""
    openrouter_url: str = "https://openrouter.ai/api/v1"
    provider_timeout_seconds: float = 60
    provider_max_retries: int = 2
    max_file_bytes: int = 20 * 1024 * 1024
    max_pages: int = 100
    max_vision_pages: int = 6
    poppler_path: str | None = None
    lease_seconds: int = 300
    max_pending_jobs: int = 32
    retention_days: int = 7
    worker_poll_seconds: float = 0.25
    worker_enabled: bool = True

    @property
    def runtime_db(self) -> Path:
        return self.runtime_dir / "runtime.sqlite"

    def validate(self):
        try:
            loopback = ipaddress.ip_address(self.host).is_loopback
        except ValueError:
            loopback = self.host.lower() == "localhost"
        if not loopback and not self.api_key:
            raise ValueError("Non-loopback binding requires SENDER_API_KEY")
        if self.provider_mode not in {"offline", "cloud"}:
            raise ValueError("SENDER_PROVIDER_MODE must be offline or cloud")
        if min(self.max_file_bytes, self.max_pages, self.max_pending_jobs, self.lease_seconds, self.retention_days) <= 0:
            raise ValueError("Limits must be positive")
        if self.provider_timeout_seconds <= 0 or self.provider_max_retries < 0 or self.max_vision_pages < 0:
            raise ValueError("Provider limits must be bounded positive values")
        return self

    @classmethod
    def from_env(cls, env_file: Path | None = None):
        # Local .env is read only on explicit startup, never on import. Process wins.
        values = {}
        path = env_file or ROOT / ".env"
        if path.exists():
            # Parse quoting/comments without evaluating $ variables or shell text.
            values.update(dotenv_values(path,encoding="utf-8-sig",interpolate=False))
        values.update(os.environ)
        mapping = {
            "lookup_db": ("SENDER_LOOKUP_DB", Path), "policy_path": ("SENDER_POLICY_PATH", Path),
            "runtime_dir": ("SENDER_RUNTIME_DIR", Path), "host": ("SENDER_HOST", str), "port": ("SENDER_PORT", int),
            "api_key": ("SENDER_API_KEY", str), "provider_mode": ("SENDER_PROVIDER_MODE", str),
            "openrouter_api_key": ("OPENROUTER_API_KEY", str), "openrouter_text_model": ("OPENROUTER_TEXT_MODEL", str),
            "openrouter_vision_model": ("OPENROUTER_VISION_MODEL", str), "openrouter_url": ("OPENROUTER_URL", str),
            "provider_timeout_seconds": ("SENDER_PROVIDER_TIMEOUT_SECONDS", float),
            "provider_max_retries": ("SENDER_PROVIDER_MAX_RETRIES", int), "max_file_bytes": ("SENDER_MAX_FILE_BYTES", int),
            "max_pages": ("SENDER_MAX_PAGES", int), "max_vision_pages": ("SENDER_MAX_VISION_PAGES", int),
            "poppler_path": ("SENDER_POPPLER_PATH", str), "lease_seconds": ("SENDER_LEASE_SECONDS", int),
            "max_pending_jobs": ("SENDER_MAX_PENDING_JOBS", int), "retention_days": ("SENDER_RETENTION_DAYS", int),
        }
        kwargs = {field: cast(values[key]) for field, (key, cast) in mapping.items() if values.get(key)}
        for name in ("lookup_db", "policy_path", "runtime_dir"):
            if name in kwargs and not kwargs[name].is_absolute():
                kwargs[name] = (ROOT / kwargs[name]).resolve()
        return cls(**kwargs).validate()
