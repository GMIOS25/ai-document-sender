"""Asynchronous outgoing.v1 HTTP boundary. No iDesk credentials are accepted."""
import asyncio
from contextlib import asynccontextmanager
import hmac
from io import BytesIO
import json
import sqlite3
from fastapi import FastAPI, Depends, File, Form, Header, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from pypdf import PdfReader
from .config import Settings
from .contracts import DocumentMetadata, Feedback, JobEnvelope, OrganizationBatch
from .jobs import JobStore, StoreError, Worker
from .registry import Registry
from .tenants import TenantManager, normalize_tenant_id
from .sync import sync_tenant_lookup, sync_tenant_organizations


class RequestTooLarge(Exception): pass


class RequestLimit:
    def __init__(self,app,max_bytes): self.app,self.max_bytes=app,max_bytes

    async def __call__(self,scope,receive,send):
        if scope["type"] != "http":
            return await self.app(scope,receive,send)
        length=dict(scope.get("headers",[])).get(b"content-length")
        if length:
            try:
                if int(length) > self.max_bytes:
                    return await JSONResponse({"error":{"code":"upload_too_large","message":"Upload exceeds configured limit"}},status_code=413)(scope,receive,send)
            except ValueError:
                return await JSONResponse({"error":{"code":"invalid_request","message":"Invalid content length"}},status_code=400)(scope,receive,send)
        size=0
        async def bounded_receive():
            nonlocal size
            message=await receive()
            size+=len(message.get("body",b""))
            if size > self.max_bytes: raise RequestTooLarge()
            return message
        try: await self.app(scope,bounded_receive,send)
        except RequestTooLarge:
            await JSONResponse({"error":{"code":"upload_too_large","message":"Upload exceeds configured limit"}},status_code=413)(scope,receive,send)


def create_app(settings=None,provider=None,extractor=None):
    settings=(settings or Settings.from_env()).validate()
    tenant_manager=TenantManager(settings)

    @asynccontextmanager
    async def lifespan(app):
        nonlocal provider
        store=JobStore(settings)
        if provider is None and settings.provider_mode == "cloud":
            from .provider import OpenRouterProvider
            provider=OpenRouterProvider(settings)
        worker=Worker(settings,store,provider,extractor)
        app.state.store,app.state.worker,app.state.provider=store,worker,provider
        task=asyncio.create_task(worker.run()) if settings.worker_enabled else None
        try: yield
        finally:
            worker.stopping.set()
            if task:
                task.cancel()
                try: await task
                except asyncio.CancelledError: pass
            close=getattr(provider,"aclose",None)
            if close: await close()

    app=FastAPI(title="Outgoing recipient backend",version="outgoing.v1",lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestLimit,max_bytes=settings.max_file_bytes+65536)

    async def authenticate(x_api_key: str | None = Header(default=None)):
        if settings.api_key and not hmac.compare_digest(x_api_key or "",settings.api_key):
            raise StoreError("unauthorized","Invalid or missing API key",401)

    @app.exception_handler(StoreError)
    async def store_error(request,error):
        return JSONResponse({"error":{"code":error.code,"message":error.message}},status_code=error.status,
                            headers={"Retry-After":"2"} if error.status == 429 else None)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request,error):
        return JSONResponse({"error":{"code":"invalid_request","message":"Request does not match outgoing.v1 schema"}},status_code=422)

    def current_registry(tenant_id: str | None = None):
        tid=normalize_tenant_id(tenant_id, settings.default_tenant)
        try: return tenant_manager.get_registry(tid)
        except (OSError,ValueError,KeyError,sqlite3.Error) as error:
            raise StoreError("registry_unavailable",f"Registry or policy could not be loaded for tenant '{tid}'",503) from error

    @app.get("/health",dependencies=[Depends(authenticate)])
    async def health(x_tenant_id: str | None = Header(default=None)):
        from .ocr import capabilities as ocr_capabilities
        registry=current_registry(x_tenant_id)
        active=getattr(app.state,"provider",None)
        capabilities=active.capabilities() if active and hasattr(active,"capabilities") else {"text":False,"vision":False}
        tid=normalize_tenant_id(x_tenant_id, settings.default_tenant)
        return {"readiness":"ready","schema_version":"outgoing.v1","tenant_id":tid,
                "registry_version":registry.registry_version,
                "alias_policy_version":registry.alias_policy_version,"provider":{"mode":settings.provider_mode,
                "configured":bool(active and getattr(active,"available",True)),"capabilities":capabilities},
                "local_ocr":ocr_capabilities(settings),
                "limits":{"max_file_bytes":settings.max_file_bytes,"max_pages":settings.max_pages}}

    @app.get("/v1/outgoing/recipients/search",dependencies=[Depends(authenticate)])
    async def search(q: str = Query(min_length=1,max_length=256),limit: int = Query(default=10,ge=1,le=50),x_tenant_id: str | None = Header(default=None)):
        registry=current_registry(x_tenant_id)
        return {"items":[r.model_dump(mode="json") for r in registry.search(q,limit)],
                "registry_version":registry.registry_version,"alias_policy_version":registry.alias_policy_version}

    @app.post("/v1/outgoing/jobs",status_code=202,dependencies=[Depends(authenticate)])
    async def create_job(file: UploadFile = File(),metadata: str = Form(),idempotency_key: str | None = Header(default=None),x_tenant_id: str | None = Header(default=None)):
        if not idempotency_key or len(idempotency_key)>256 or not idempotency_key.strip():
            raise StoreError("invalid_idempotency_key","Idempotency-Key is required and must be at most 256 characters",422)
        if len(metadata)>32768: raise StoreError("invalid_metadata","Metadata exceeds limit",422)
        try: parsed=DocumentMetadata.model_validate_json(metadata)
        except ValidationError as error: raise StoreError("invalid_metadata","Metadata does not match outgoing.v1 schema",422) from error
        data=await file.read(settings.max_file_bytes+1)
        await file.close()
        if len(data)>settings.max_file_bytes: raise StoreError("upload_too_large","PDF exceeds configured limit",413)
        if not data.startswith(b"%PDF-"): raise StoreError("invalid_pdf","Upload must contain a PDF document",422)
        def check_pdf():
            try:
                pdf=PdfReader(BytesIO(data))
                if pdf.is_encrypted: raise StoreError("encrypted_pdf","Encrypted PDFs are not supported",422)
                count=len(pdf.pages)
                if count<1: raise StoreError("invalid_pdf","PDF has no pages",422)
                if count>settings.max_pages: raise StoreError("page_limit_exceeded","PDF exceeds configured page limit",422)
            except StoreError: raise
            except Exception as error: raise StoreError("invalid_pdf","PDF could not be parsed",422) from error
        await asyncio.to_thread(check_pdf)
        created=app.state.store.create(data,parsed,idempotency_key,current_registry(x_tenant_id))
        return {"job_id":created["job_id"],"status":created["status"]}

    @app.get("/v1/outgoing/jobs/{job_id}",response_model=JobEnvelope,dependencies=[Depends(authenticate)])
    async def read_job(job_id: str,x_tenant_id: str | None = Header(default=None)):
        job=app.state.store.get_for_tenant(job_id,normalize_tenant_id(x_tenant_id, settings.default_tenant),allow_legacy=True)
        return {key:job[key] for key in ("job_id","status","result","error")}

    @app.post("/v1/outgoing/jobs/{job_id}/feedback",status_code=201,dependencies=[Depends(authenticate)])
    async def feedback(job_id: str,body: Feedback,x_tenant_id: str | None = Header(default=None)):
        return {"feedback_id":app.state.store.feedback(job_id,body,current_registry(x_tenant_id))}

    @app.post("/v1/outgoing/jobs/{job_id}/resolutions",status_code=202,dependencies=[Depends(authenticate)])
    async def resolution(job_id: str,x_tenant_id: str | None = Header(default=None)):
        created=app.state.store.create_resolution(job_id,current_registry(x_tenant_id))
        return {"job_id":created["job_id"],"status":created["status"]}

    @app.post("/v1/sync/organizations",dependencies=[Depends(authenticate)])
    async def sync_organizations(body: OrganizationBatch,x_tenant_id: str | None = Header(default=None)):
        tid=normalize_tenant_id(x_tenant_id, settings.default_tenant)
        return await asyncio.to_thread(sync_tenant_organizations,tid,body,settings,tenant_manager)

    @app.post("/v1/sync/lookup",dependencies=[Depends(authenticate)])
    async def sync_lookup(body: dict,x_tenant_id: str | None = Header(default=None)):
        tid=normalize_tenant_id(x_tenant_id, settings.default_tenant)
        try:
            return await asyncio.to_thread(sync_tenant_lookup, tid, body, settings, tenant_manager)
        except ValidationError as error:
            section = {"LookupDirectoryBatch": "unit_directory", "UnitGroupBatch": "unit_groups"}.get(error.title)
            if section is not None:
                issue = error.errors(include_input=False, include_context=False, include_url=False)[0]
                location = issue["loc"]
                if issue["type"] == "extra_forbidden":
                    location = location[:-1]  # The extra key comes from the request.
                path = ".".join(map(str, (section, *location)))
                raise StoreError("invalid_request", f"Invalid lookup data at {path} ({issue['type']})", 422) from error
            raise StoreError("invalid_request", "Invalid organization directory batch", 422) from error
        except (TypeError, AttributeError) as error:
            raise StoreError("invalid_request", "Invalid organization directory batch", 422) from error
        except Exception as error:
            raise StoreError("sync_failed", f"Lookup sync failed for tenant '{tid}': {error}", 500) from error

    return app
