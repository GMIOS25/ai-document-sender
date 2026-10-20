from dataclasses import replace
from io import BytesIO
import hashlib
import json
from fastapi.testclient import TestClient
from reportlab.pdfgen import canvas
from ai_document_sender.api import create_app
from ai_document_sender.contracts import Evidence, Extraction, Mention


def pdf_bytes():
    data=BytesIO(); page=canvas.Canvas(data); page.drawString(50,750,"Recipient document"); page.showPage(); page.save(); return data.getvalue()


def submit(client,key="key",pdf=None,document="doc"):
    return client.post("/v1/outgoing/jobs",files={"file":("main.pdf",pdf or pdf_bytes(),"application/pdf")},
                       data={"metadata":json.dumps({"document_id":document,"department_code":"KGVX"})},headers={"Idempotency-Key":key})


def test_upload_auth_bounds_and_search(settings):
    app=create_app(replace(settings,api_key="test-key"))
    with TestClient(app) as client:
        assert client.get("/health").status_code == 401
        assert client.get("/health",headers={"X-API-Key":"test-key"}).status_code == 200
    with TestClient(create_app(settings)) as client:
        assert submit(client,pdf=b"invalid").status_code == 422
        assert client.post("/v1/outgoing/jobs",files={"file":("main.pdf",pdf_bytes())},data={"metadata":'{"document_id":"d"}'}).status_code == 422
        search=client.get("/v1/outgoing/recipients/search",params={"q":"Lịch"}).json()
        assert any(item["recipient_id"] == "internal_278" for item in search["items"])
        assert search["registry_version"] and search["alias_policy_version"]
    with TestClient(create_app(replace(settings,max_file_bytes=100))) as client:
        assert submit(client).status_code == 413


def test_health_reports_local_ocr_configuration_and_missing_weights(settings):
    configured = replace(settings, ocr_backend="vietocr", ocr_weights=settings.runtime_dir / "missing.pth")
    with TestClient(create_app(configured)) as client:
        health = client.get("/health").json()
    assert health["local_ocr"]["backend"] == "vietocr"
    assert health["local_ocr"]["weights_ready"] is False
    assert health["local_ocr"]["configured"] is False


def test_search_returns_parent_nodes_with_idesk_identity(settings):
    with TestClient(create_app(settings)) as client:
        for query, rid, source_id, kind in [
            ("Lãnh đạo Văn phòng UBND tỉnh", "internal_286", "286", "INTERNAL_DEPT"),
            ("Toàn bộ Phòng Khoa giáo Văn xã", "internal_338", "338", "INTERNAL_DEPT"),
            ("Toàn bộ UBND tỉnh Gia Lai", "internal_249", "249", "INTERNAL_UNIT"),
        ]:
            response = client.get("/v1/outgoing/recipients/search", params={"q": query})
            assert response.status_code == 200
            items = response.json()["items"]
            assert [(r["recipient_id"], r["source_id"], r["recipient_type"], r["sphere"]) for r in items] == [
                (rid, source_id, kind, "internal")]


def test_create_poll_feedback_smoke_and_source_unchanged(settings):
    async def extract(*args):
        return Extraction(status="partial",mentions=[Mention(mention_id="m",raw="Chủ tịch UBND tỉnh",kind="role",evidence=[Evidence(page=1,section="noi_nhan",raw="Chủ tịch UBND tỉnh")])])
    before=hashlib.sha256(settings.lookup_db.read_bytes()).hexdigest()
    app=create_app(settings,extractor=extract)
    with TestClient(app) as client:
        created=submit(client).json(); jid=created["job_id"]
        import asyncio
        client.portal.call(app.state.worker.run_once)
        job=client.get(f"/v1/outgoing/jobs/{jid}").json()
        assert set(job) == {"job_id","status","result","error"}
        assert job["status"] == "completed"
        result=job["result"]
        assert result["needs_review"]
        duplicate=submit(client,pdf=app.state.store.settings.runtime_dir.joinpath("inputs",result["input_sha256"]+".pdf").read_bytes()).json()
        assert duplicate["job_id"] == jid
        body={"registry_version":result["registry_version"],"alias_policy_version":result["alias_policy_version"],
              "final_recipients":[{"recipient_id":"internal_270","recipient_type":"INTERNAL_PERSON","sphere":"internal","code":"tuanpa@vpub.gialai.gov.vn"}],
              "review_decisions":[{"mention_id":"reason:extraction_partial","action":"accept_missing","note":"Reviewed incomplete extraction"}],"confirmed":True}
        accepted=client.post(f"/v1/outgoing/jobs/{jid}/feedback",json=body)
        assert accepted.status_code == 201 and accepted.json()["feedback_id"]
        body["review_decisions"]=[]
        assert client.post(f"/v1/outgoing/jobs/{jid}/feedback",json=body).status_code == 422
        body["alias_policy_version"]="stale"
        assert client.post(f"/v1/outgoing/jobs/{jid}/feedback",json=body).status_code == 409
        assert client.get("/v1/outgoing/jobs/unknown").status_code == 404
    assert hashlib.sha256(settings.lookup_db.read_bytes()).hexdigest() == before


def test_feedback_accepts_manual_id_from_same_snapshot_and_rejects_fake(settings):
    async def extract(*args): return Extraction(status="complete")
    app=create_app(settings,extractor=extract)
    with TestClient(app) as client:
        jid=submit(client).json()["job_id"]
        client.portal.call(app.state.worker.run_once)
        result=client.get(f"/v1/outgoing/jobs/{jid}").json()["result"]
        item=client.get("/v1/outgoing/recipients/search",params={"q":"V5"}).json()["items"][0]
        body={"registry_version":result["registry_version"],"alias_policy_version":result["alias_policy_version"],
              "final_recipients":[{k:item[k] for k in ("recipient_id","recipient_type","sphere","code")}],"confirmed":True}
        assert client.post(f"/v1/outgoing/jobs/{jid}/feedback",json=body).status_code == 201
        body["final_recipients"][0]["recipient_id"]="invented"
        assert client.post(f"/v1/outgoing/jobs/{jid}/feedback",json=body).status_code == 422


def test_resolve_decision_requires_linked_final_identity(settings):
    async def extract(*args):
        return Extraction(status="complete",mentions=[Mention(mention_id="pending",raw="PVPQT",kind="role",evidence=[Evidence(page=1,section="noi_nhan",raw="PVPQT")])])
    app=create_app(settings,extractor=extract)
    with TestClient(app) as client:
        jid=submit(client).json()["job_id"]
        client.portal.call(app.state.worker.run_once)
        result=client.get(f"/v1/outgoing/jobs/{jid}").json()["result"]
        body={"registry_version":result["registry_version"],"alias_policy_version":result["alias_policy_version"],
              "final_recipients":[],"confirmed":True,"review_decisions":[{"mention_id":"pending","action":"resolve"}]}
        assert client.post(f"/v1/outgoing/jobs/{jid}/feedback",json=body).status_code == 422
        body["review_decisions"][0]["recipient_ids"]=["internal_270"]
        assert client.post(f"/v1/outgoing/jobs/{jid}/feedback",json=body).status_code == 422
        body["final_recipients"]=[{"recipient_id":"internal_270","recipient_type":"INTERNAL_PERSON","sphere":"internal","code":"tuanpa@vpub.gialai.gov.vn"}]
        assert client.post(f"/v1/outgoing/jobs/{jid}/feedback",json=body).status_code == 201
