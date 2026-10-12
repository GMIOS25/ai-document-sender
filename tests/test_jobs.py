import asyncio
from dataclasses import replace
import pytest
from ai_document_sender.contracts import DocumentMetadata, Evidence, Extraction, Mention
from ai_document_sender.registry import Registry
from ai_document_sender.jobs import JobStore, Worker, StoreError


def create(store, settings, key="k", data=b"fake-pdf"):
    return store.create(data, DocumentMetadata(document_id="doc",department_code="KGVX"), key, Registry(settings))


def test_replacing_local_ocr_weights_invalidates_processing_version(settings):
    from ai_document_sender.jobs import processing_version
    path = settings.runtime_dir / "weights.pth"
    configured = replace(settings, ocr_backend="vietocr", ocr_weights=path)
    path.parent.mkdir(parents=True)
    before = processing_version(configured)
    path.write_bytes(b"first model")
    first = processing_version(configured)
    path.write_bytes(b"second model with different weights")
    assert first != before
    assert processing_version(configured) != first


def test_idempotency_conflict_and_lease_recovery(settings):
    s = JobStore(settings)
    a = create(s, settings)
    assert create(s,settings)["job_id"] == a["job_id"]
    with pytest.raises(StoreError) as error: create(s,settings,data=b"different")
    assert error.value.code == "idempotency_key_conflict"
    claimed = s.claim()
    assert claimed["job_id"] == a["job_id"]
    assert s.claim() is None
    with s.connection() as c: c.execute("UPDATE jobs SET lease_until=0")
    reclaimed = JobStore(settings).claim()
    assert reclaimed["job_id"] == claimed["job_id"]
    assert reclaimed["lease_token"] != claimed["lease_token"]
    assert not s.update(claimed["job_id"],claimed["lease_token"],status="completed")


@pytest.mark.asyncio
@pytest.mark.parametrize("change", ["extractor", "prompt", "model", "vision_limit", "ocr", "legacy"])
async def test_same_request_reprocesses_after_processing_change(settings, monkeypatch, change):
    from ai_document_sender import extraction, provider

    store = JobStore(settings)
    calls = []

    async def extract(*args):
        raw = "V5" if not calls else "V8"
        calls.append(raw)
        return Extraction(status="complete", mentions=[Mention(
            mention_id="m", raw=raw, kind="staff_code",
            evidence=[Evidence(page=1, section="luu", raw=raw)])])

    original = create(store, settings)
    await Worker(settings, store, extractor=extract).run_once()
    saved = store.get(original["job_id"])
    assert create(store, settings)["job_id"] == original["job_id"]
    if change == "extractor":
        monkeypatch.setattr(extraction, "EXTRACTOR_VERSION", "new-extractor")
    elif change == "prompt":
        monkeypatch.setattr(provider, "PROMPT_VERSION", "new-prompt")
    elif change == "model":
        settings = replace(settings, openrouter_text_model="new-model")
    elif change == "vision_limit":
        settings = replace(settings, max_vision_pages=settings.max_vision_pages + 1)
    elif change == "ocr":
        settings = replace(settings, ocr_backend="vietocr")
    else:
        # Reopen a real pre-migration table, preserving completed audit records.
        with store.connection() as conn:
            conn.execute("UPDATE jobs SET idempotency_key='k'")
            conn.execute("DROP INDEX jobs_request_key")
            conn.execute("ALTER TABLE jobs DROP COLUMN request_key")
            conn.execute("ALTER TABLE jobs DROP COLUMN processing_version")
        monkeypatch.setattr(extraction, "EXTRACTOR_VERSION", "new-extractor")
    store = JobStore(settings)
    current = create(store, settings)
    assert current["job_id"] != original["job_id"]
    assert create(store, settings)["job_id"] == current["job_id"]
    await Worker(settings, store, extractor=extract).run_once()
    assert calls == ["V5", "V8"]
    assert store.get(current["job_id"])["result"]["people"][0]["recipient_id"] == "internal_485"
    assert store.get(original["job_id"])["result"] == saved["result"]
    assert create(store, settings)["job_id"] == current["job_id"]
    with pytest.raises(StoreError) as error:
        create(store, settings, data=b"different")
    assert error.value.code == "idempotency_key_conflict"


def test_processing_change_keeps_inflight_request_idempotent(settings, monkeypatch):
    from ai_document_sender import extraction

    store = JobStore(settings)
    original = create(store, settings)
    monkeypatch.setattr(extraction, "EXTRACTOR_VERSION", "new-extractor")
    assert create(store, settings)["job_id"] == original["job_id"]
    claimed = store.claim()
    assert create(store, settings)["job_id"] == original["job_id"]
    store.update(claimed["job_id"], claimed["lease_token"], status="failed")
    upgraded = create(store, settings)
    assert upgraded["job_id"] != original["job_id"]
    monkeypatch.setattr(extraction, "EXTRACTOR_VERSION", "third-extractor")
    assert create(store, settings)["job_id"] == upgraded["job_id"]


@pytest.mark.asyncio
async def test_restart_checkpoint_reuse_and_partial_not_shared_cache(settings):
    s = JobStore(settings)
    created = create(s,settings)
    claim = s.claim()
    extraction = Extraction(status="partial",mentions=[Mention(mention_id="m",raw="V5",kind="staff_code",evidence=[Evidence(page=1,section="luu",raw="V5")])])
    s.update(claim["job_id"],claim["lease_token"],checkpoint=extraction.model_dump(mode="json"),status="resolving")
    with s.connection() as c: c.execute("UPDATE jobs SET lease_until=0")
    async def never(*args): raise AssertionError("checkpoint must be reused")
    w = Worker(settings,s,extractor=never)
    await w.run_once()
    job = s.get(created["job_id"])
    assert job["status"] == "completed"
    assert job["result"]["needs_review"]
    assert job["result"]["people"][0]["recipient_id"] == "internal_341"
    assert s.cache_get("anything") is None


@pytest.mark.asyncio
async def test_complete_extraction_reused_across_registry_change(settings):
    s = JobStore(settings); calls = []
    async def extractor(*args):
        calls.append(1)
        return Extraction(status="complete",mentions=[Mention(mention_id="m",raw="V5",kind="staff_code",evidence=[Evidence(page=1,section="luu",raw="V5")])])
    first = create(s,settings)
    await Worker(settings,s,extractor=extractor).run_once()
    import sqlite3
    with sqlite3.connect(settings.lookup_db) as c:
        c.execute("UPDATE recipients SET full_name='Người hiện tại' WHERE recipient_id='internal_341'")
    second = create(s,settings,key="newversion")
    await Worker(settings,s,extractor=extractor).run_once()
    assert len(calls) == 1
    assert s.get(first["job_id"])["result"]["people"][0]["name"] == "Lê Thị Kim Yến"
    assert s.get(second["job_id"])["result"]["people"][0]["name"] == "Người hiện tại"


@pytest.mark.asyncio
async def test_worker_failure_safe_message(settings):
    s=JobStore(settings); item=create(s,settings)
    async def bad(*args): raise RuntimeError("Bearer SECRET should never escape")
    await Worker(settings,s,extractor=bad).run_once()
    job=s.get(item["job_id"])
    assert job["status"] == "failed"
    assert "SECRET" not in str(job["error"])
