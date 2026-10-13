from fastapi.testclient import TestClient
from ai_document_sender.api import create_app


def test_api_tenant_resolution_and_sync(settings):
    app = create_app(settings)
    client = TestClient(app)

    # 1. Health check with default and custom tenant
    r_default = client.get("/health")
    assert r_default.status_code == 200
    assert r_default.json()["tenant_id"] == "vpub"

    r_custom = client.get("/health", headers={"X-Tenant-ID": "snnmt"})
    assert r_custom.status_code == 200
    assert r_custom.json()["tenant_id"] == "snnmt"

    # 2. Sync endpoint for tenant 'snnmt'
    payload = {
        "person": {
            "elements": [
                {
                    "id": 888,
                    "parent": 0,
                    "type": "alias",
                    "name": "Chi cục trưởng",
                    "refFullname": "Hoàng Văn Thái",
                    "refUname": "thaihv@snnmt.gialai.gov.vn",
                    "rank": "leader",
                    "order": 1
                }
            ]
        },
        "unit_internal": {
            "elements": [
                {
                    "code": "H21.88",
                    "name": "Chi cục Thủy lợi - tỉnh Gia Lai",
                    "count": 45,
                    "uuid": "uuid_thuy_loi"
                }
            ]
        },
        "unit_external": {
            "elements": []
        }
    }

    r_sync = client.post("/v1/sync/lookup", json=payload, headers={"X-Tenant-ID": "snnmt"})
    assert r_sync.status_code == 200
    body = r_sync.json()
    assert body["status"] == "synced"
    assert body["tenant_id"] == "snnmt"
    assert body["total_recipients"] == 2

    # 3. Search endpoint isolates tenants
    # Searching snnmt finds the new person
    r_search_snnmt = client.get("/v1/outgoing/recipients/search?q=Hoàng+Văn+Thái", headers={"X-Tenant-ID": "snnmt"})
    assert r_search_snnmt.status_code == 200
    items = r_search_snnmt.json()["items"]
    assert len(items) >= 1
    assert any("Hoàng Văn Thái" in item["display_name"] for item in items)

    # Searching vpub does NOT find the person belonging only to snnmt
    r_search_vpub = client.get("/v1/outgoing/recipients/search?q=Hoàng+Văn+Thái")
    assert r_search_vpub.status_code == 200
    assert len(r_search_vpub.json()["items"]) == 0

    # 4. Repeat sync returns no_change
    r_sync_again = client.post("/v1/sync/lookup", json=payload, headers={"X-Tenant-ID": "snnmt"})
    assert r_sync_again.status_code == 200
    assert r_sync_again.json()["status"] == "no_change"
