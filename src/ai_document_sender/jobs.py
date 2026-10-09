"""SQLite-backed jobs with atomic leases, checkpoints and audited feedback."""
import asyncio
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import time
import uuid
from .contracts import DocumentMetadata, Extraction, OutgoingResult
from .registry import Registry, digest
from .resolver import resolve_mentions


class StoreError(Exception):
    def __init__(self, code, message, status=409):
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


class JobStore:
    def __init__(self, settings):
        self.settings = settings
        settings.runtime_dir.mkdir(parents=True,exist_ok=True)
        (settings.runtime_dir / "inputs").mkdir(exist_ok=True)
        with self.connection() as conn:
            conn.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY, idempotency_key TEXT UNIQUE NOT NULL,
                    fingerprint TEXT NOT NULL, input_sha256 TEXT NOT NULL, file_path TEXT NOT NULL,
                    metadata TEXT NOT NULL, snapshot TEXT NOT NULL, status TEXT NOT NULL,
                    checkpoint TEXT, result TEXT, error TEXT, lease_token TEXT, lease_until REAL,
                    created_at REAL NOT NULL, updated_at REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS extraction_cache (cache_key TEXT PRIMARY KEY, body TEXT NOT NULL, created_at REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS feedback (feedback_id TEXT PRIMARY KEY,job_id TEXT NOT NULL,body TEXT NOT NULL,created_at REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS registry_overlay (overlay_id TEXT PRIMARY KEY, body TEXT NOT NULL,created_at REAL NOT NULL);
            """)

    @contextmanager
    def connection(self):
        conn=sqlite3.connect(self.settings.runtime_db,timeout=15)
        conn.row_factory=sqlite3.Row
        try:
            yield conn
            conn.commit()
        except BaseException:
            conn.rollback()
            raise
        finally:
            conn.close()

    def create(self, data, metadata, key, registry):
        input_hash=hashlib.sha256(data).hexdigest()
        fingerprint=digest({"workflow":"outgoing.v1","input":input_hash,"metadata":metadata.model_dump(mode="json"),
                           "registry":registry.registry_version,"policy":registry.alias_policy_version})
        now=time.time()
        with self.connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            existing=conn.execute("SELECT * FROM jobs WHERE idempotency_key=?",(key,)).fetchone()
            if existing:
                if existing["fingerprint"] != fingerprint:
                    raise StoreError("idempotency_key_conflict","Idempotency key belongs to a different input or snapshot")
                return dict(existing)
            pending=conn.execute("SELECT COUNT(*) FROM jobs WHERE status NOT IN ('completed','failed')").fetchone()[0]
            if pending >= self.settings.max_pending_jobs:
                raise StoreError("queue_full","Job queue is full; retry later",429)
            file_path=self.settings.runtime_dir / "inputs" / (input_hash+".pdf")
            if not file_path.exists():
                temporary=file_path.with_suffix("."+uuid.uuid4().hex+".tmp")
                temporary.write_bytes(data)
                os.replace(temporary,file_path)
            job_id=uuid.uuid4().hex
            conn.execute("INSERT INTO jobs (job_id,idempotency_key,fingerprint,input_sha256,file_path,metadata,snapshot,status,created_at,updated_at) VALUES (?,?,?,?,?,?,?,'queued',?,?)",
                         (job_id,key,fingerprint,input_hash,str(file_path),metadata.model_dump_json(),json.dumps(registry.snapshot(),ensure_ascii=False),now,now))
            return dict(conn.execute("SELECT * FROM jobs WHERE job_id=?",(job_id,)).fetchone())

    def get(self, job_id):
        with self.connection() as conn:
            row=conn.execute("SELECT * FROM jobs WHERE job_id=?",(job_id,)).fetchone()
        if not row:
            raise StoreError("job_not_found","Job not found",404)
        data=dict(row)
        for name in ("metadata","snapshot","checkpoint","result","error"):
            data[name]=json.loads(data[name]) if data[name] else None
        return data

    def claim(self):
        now=time.time()
        with self.connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row=conn.execute("SELECT job_id FROM jobs WHERE status='queued' OR (status IN ('extracting','resolving') AND lease_until<?) ORDER BY created_at LIMIT 1",(now,)).fetchone()
            if not row: return None
            token=uuid.uuid4().hex
            conn.execute("UPDATE jobs SET status='extracting',lease_token=?,lease_until=?,updated_at=? WHERE job_id=?",(token,now+self.settings.lease_seconds,now,row[0]))
        return self.get(row[0])

    def update(self, job_id, token, **fields):
        allowed={"status","checkpoint","result","error","lease_until","lease_token"}
        if not fields or not set(fields) <= allowed: raise ValueError("Invalid job update")
        data={k:json.dumps(v,ensure_ascii=False) if k in {"checkpoint","result","error"} and v is not None else v for k,v in fields.items()}
        data["updated_at"]=time.time()
        columns=",".join(k+"=?" for k in data)
        with self.connection() as conn:
            return conn.execute("UPDATE jobs SET "+columns+" WHERE job_id=? AND lease_token=? AND status IN ('extracting','resolving')",(*data.values(),job_id,token)).rowcount == 1

    def cache_get(self, key):
        with self.connection() as conn:
            row=conn.execute("SELECT body FROM extraction_cache WHERE cache_key=?",(key,)).fetchone()
        return Extraction.model_validate_json(row[0]) if row else None

    def cache_put(self, key, extraction):
        if extraction.status != "complete": return
        with self.connection() as conn:
            conn.execute("INSERT OR REPLACE INTO extraction_cache VALUES (?,?,?)",(key,extraction.model_dump_json(),time.time()))

    def feedback(self, job_id, body, registry):
        job=self.get(job_id)
        if job["status"] != "completed": raise StoreError("job_not_completed","Feedback requires a completed job")
        snapshot=job["snapshot"]
        if (body.registry_version != snapshot["registry_version"] or body.alias_policy_version != snapshot["alias_policy_version"]
            or registry.registry_version != snapshot["registry_version"] or registry.alias_policy_version != snapshot["alias_policy_version"]):
            raise StoreError("stale_snapshot","Registry or policy changed; resolve again before confirmation")
        identities=snapshot["recipients"]
        selected=set()
        for item in body.final_recipients:
            known=identities.get(item.recipient_id)
            if not known or any(getattr(item,k) != known[k] for k in ("recipient_type","sphere","code")):
                raise StoreError("invalid_recipient","Recipient identity does not match job snapshot",422)
            if item.recipient_id in selected:
                raise StoreError("duplicate_recipient","Duplicate final recipient",422)
            selected.add(item.recipient_id)
        for assignment in body.field_assignments:
            if assignment.recipient_id not in selected:
                raise StoreError("invalid_assignment","Field assignment must reference a final recipient",422)
            sphere=identities[assignment.recipient_id]["sphere"]
            valid=(assignment.field in {"responsible","save","participants","follow"}) if sphere == "internal" else (assignment.field == "inside_unit" if sphere == "int_province_comm" else assignment.field == "outside_unit")
            if not valid: raise StoreError("invalid_assignment","Field does not match recipient sphere",422)
        mention_ids={m["mention_id"] for m in job["result"]["mentions"]}
        reason_ids={"reason:"+reason for reason in job["result"]["review_reasons"]}
        decisions=set()
        for decision in body.review_decisions:
            if decision.mention_id not in mention_ids | reason_ids or decision.mention_id in decisions:
                raise StoreError("invalid_review_decision","Review decision references an unknown or duplicate evidence ID",422)
            if decision.mention_id in reason_ids and (decision.action != "accept_missing" or not decision.note.strip()):
                raise StoreError("invalid_review_decision","Global review reasons require an explicit accept_missing note",422)
            if decision.action in {"accept_missing","exclude"} and not decision.note.strip():
                raise StoreError("invalid_review_decision","Missing/excluded decisions require a note",422)
            if decision.action == "resolve" and (not decision.recipient_ids or not set(decision.recipient_ids)<=selected):
                raise StoreError("invalid_review_decision","Resolve decisions must link one or more final recipient IDs",422)
            if decision.action != "resolve" and decision.recipient_ids:
                raise StoreError("invalid_review_decision","Only resolve decisions may link recipient IDs",422)
            decisions.add(decision.mention_id)
        required={x["mention_id"] for x in job["result"]["unresolved"]} | reason_ids
        if body.confirmed and not required <= decisions:
            raise StoreError("review_incomplete","Every unresolved mention and review reason must be acknowledged",422)
        fid=uuid.uuid4().hex
        with self.connection() as conn:
            conn.execute("INSERT INTO feedback VALUES (?,?,?,?)",(fid,job_id,body.model_dump_json(),time.time()))
        return fid

    def import_overlay(self, records):
        # Local administration only. Feedback never calls this function.
        from .contracts import Recipient
        validated=[]
        for record in records:
            if record.get("verification_status") != "verified" or not record.get("verified_by") or not record.get("evidence"):
                raise ValueError("Overlay requires verified status, verified_by and evidence")
            if "recipient" in record:
                recipient=Recipient.model_validate(record["recipient"])
                if recipient.sphere != "internal" and not recipient.code:
                    raise ValueError("Unit overlay requires code and sphere")
                record={**record,"recipient":recipient.model_dump(mode="json")}
                oid=recipient.recipient_id
            elif "selector" in record and record.get("member_ids"):
                oid="group:"+record["selector"]
            elif record.get("selectable_group_id"):
                oid="selectable:"+record["selectable_group_id"]
            else: raise ValueError("Overlay must contain a recipient, group members or selectable group confirmation")
            validated.append((oid,json.dumps(record,ensure_ascii=False),time.time()))
        with self.connection() as conn:
            conn.executemany("INSERT OR REPLACE INTO registry_overlay VALUES (?,?,?)",validated)
        return len(validated)

    def cleanup(self):
        cutoff=time.time()-self.settings.retention_days*86400
        with self.connection() as conn:
            active={Path(r[0]).resolve() for r in conn.execute("SELECT file_path FROM jobs WHERE status NOT IN ('completed','failed') OR updated_at>=?",(cutoff,))}
            conn.execute("DELETE FROM extraction_cache WHERE created_at<?",(cutoff,))
            conn.execute("UPDATE jobs SET checkpoint=NULL WHERE status IN ('completed','failed') AND updated_at<?",(cutoff,))
        inputs=(self.settings.runtime_dir/"inputs").resolve()
        for file in inputs.glob("*"):
            if file.resolve().parent == inputs and file.resolve() not in active and file.stat().st_mtime < cutoff:
                file.unlink()


class Worker:
    def __init__(self, settings, store, provider=None, extractor=None):
        self.settings,self.store,self.provider=settings,store,provider
        self.extractor=extractor
        self.stopping=asyncio.Event()

    def extraction_key(self,job,metadata):
        # Changing implementations/prompts invalidates caches without editing data.
        from . import extraction as extraction_module
        from . import provider as provider_module
        return digest({"input":job["input_sha256"],"extractor":getattr(extraction_module,"EXTRACTOR_VERSION","extraction-v1"),
                       "prompt":getattr(provider_module,"PROMPT_VERSION","outgoing-mentions-v1"),
                       "mode":self.settings.provider_mode,"text_model":self.settings.openrouter_text_model,
                       "vision_model":self.settings.openrouter_vision_model,
                       "limits":{"max_pages":self.settings.max_pages,"max_vision_pages":self.settings.max_vision_pages},
                       "context":{k:v for k,v in metadata.model_dump(mode="json").items() if k not in {"document_id","attachment_content_uid","attachment_name"}}})

    async def heartbeat(self,job):
        while True:
            await asyncio.sleep(max(0.1,self.settings.lease_seconds/3))
            if not self.store.update(job["job_id"],job["lease_token"],lease_until=time.time()+self.settings.lease_seconds):
                return

    async def run_once(self):
        job=self.store.claim()
        if not job: return False
        heart=asyncio.create_task(self.heartbeat(job))
        try:
            metadata=DocumentMetadata.model_validate(job["metadata"])
            registry=Registry.from_snapshot(self.settings,job["snapshot"])
            key=self.extraction_key(job,metadata)
            extraction=Extraction.model_validate(job["checkpoint"]) if job["checkpoint"] else self.store.cache_get(key)
            if extraction is None:
                extractor=self.extractor
                if extractor is None:
                    from .extraction import extract_document
                    extractor=extract_document
                extraction=await extractor(Path(job["file_path"]),self.provider,metadata,self.settings)
                extraction=Extraction.model_validate(extraction)
                if not self.store.update(job["job_id"],job["lease_token"],checkpoint=extraction.model_dump(mode="json"),status="resolving"):
                    return True
                self.store.cache_put(key,extraction)
            else:
                if not self.store.update(job["job_id"],job["lease_token"],status="resolving"):
                    return True
            result=await resolve_mentions(extraction,registry,metadata,job["job_id"],job["input_sha256"],self.provider)
            self.store.update(job["job_id"],job["lease_token"],status="completed",result=result.model_dump(mode="json"),lease_until=None)
        except asyncio.CancelledError:
            self.store.update(job["job_id"],job["lease_token"],status="queued",lease_until=None,lease_token=None)
            raise
        except Exception as error:
            # Never include raw exception messages: providers may embed keys/headers/URLs.
            code=getattr(error,"code","processing_failed")
            if code not in {"provider_unavailable","invalid_model_output","unreadable_pdf","page_limit_exceeded","provider_timeout"}:
                code="processing_failed"
            self.store.update(job["job_id"],job["lease_token"],status="failed",error={"code":code,"message":"Document processing failed; inspect configuration or retry with a valid document","retryable":code in {"provider_unavailable","provider_timeout"}},lease_until=None)
        finally:
            heart.cancel()
            try: await heart
            except asyncio.CancelledError: pass
        return True

    async def run(self):
        self.store.cleanup()
        while not self.stopping.is_set():
            if not await self.run_once():
                try: await asyncio.wait_for(self.stopping.wait(),timeout=self.settings.worker_poll_seconds)
                except TimeoutError: pass
