import asyncio
import pytest
from ai_document_sender.contracts import DocumentMetadata, Evidence, Extraction, Mention
from ai_document_sender.registry import Registry
from ai_document_sender.jobs import JobStore, Worker, StoreError


def create(store, settings, key="k", data=b"fake-pdf"):
    return store.create(data, DocumentMetadata(document_id="doc",department_code="KGVX"), key, Registry(settings))


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
