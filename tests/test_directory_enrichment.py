import json
import sqlite3
from dataclasses import replace
import pytest
from fastapi.testclient import TestClient
from ai_document_sender.api import create_app
from ai_document_sender.sync import sync_tenant_lookup
from ai_document_sender.tenants import TenantManager
from ai_document_sender.contracts import Extraction, Mention
from test_api import submit

INT = 'int_province_comm'
EXT = 'ext_province_comm'


def node(code='H21.99', name='Trung tâm Quan trắc', sphere=INT, uuid='native-1'):
    return dict(code=code, name=name, sphere=sphere, uuid=uuid,
                identifier='native-id', parentIdentifier='parent-id', centerCode='center')


def test_directory_observations_survive_history_and_uuid_changes(settings):
    manager = TenantManager(settings)
    history = {'person': {'elements': []}, 'unit_internal': {'elements': [dict(node(), count=42)]}}
    sync_tenant_lookup('new', history, settings, manager)
    before = manager.get_registry('new')
    rid = next(r.recipient_id for r in before.by_id.values() if r.code == 'H21.99')
    directory = {'unit_directory': {'elements': [node(name='Trung tâm Quan trắc hiện tại', uuid='changed'), node(code='H21.98')]}}
    enriched = sync_tenant_lookup('new', {**history, **directory}, settings, manager)
    assert enriched['status'] == 'synced'
    assert enriched['alias_policy_version']
    assert manager.get_registry('new').by_id[rid].name == 'Trung tâm Quan trắc hiện tại'
    sync_tenant_lookup('new', history, settings, manager)
    after = manager.get_registry('new')
    assert after.by_id[rid].name == 'Trung tâm Quan trắc hiện tại'
    assert len(after.by_id) == 2
    assert after is not before
    with sqlite3.connect(manager.get_db_path('new')) as conn:
        assert conn.execute('SELECT send_count FROM comm_units WHERE code=?', ('H21.99',)).fetchone()[0] == 42
        assert conn.execute("SELECT count(*) FROM recipients_fts WHERE recipients_fts MATCH 'Quan' ").fetchone()[0] == 2
        rows = conn.execute('SELECT source, raw_json, first_seen_at, last_seen_at FROM organization_observations').fetchall()
        assert {r[0] for r in rows} == {'history', 'directory'}
        assert any(json.loads(r[1]).get('uuid') == 'changed' for r in rows)
        assert all(r[2] and r[3] for r in rows)


def test_organization_import_is_atomic_bounded_authenticated_and_sphere_isolated(settings):
    configured = replace(settings, api_key='test')
    with TestClient(create_app(configured)) as client:
        assert client.post('/v1/sync/organizations', json={'source': 'search', 'elements': []}).status_code == 401
        headers = {'X-API-Key': 'test', 'X-Tenant-ID': 'one'}
        def send(elements, source='search'):
            return client.post('/v1/sync/organizations', json={'source': source, 'elements': elements}, headers=headers)
        assert send([node(), node(sphere=EXT)]).status_code == 200
        imported = send([node(), node(sphere=EXT)]).json()
        assert imported['status'] == 'no_change'
        assert imported['alias_policy_version']
        first = client.get('/v1/outgoing/recipients/search?q=Quan', headers=headers).json()['items']
        assert {r['sphere'] for r in first} == {INT, EXT}
        assert len({r['recipient_id'] for r in first}) == 2
        assert send([node(uuid='different'), node(uuid='different', sphere=EXT)]).status_code == 200
        second = client.get('/v1/outgoing/recipients/search?q=Quan', headers=headers).json()['items']
        assert {r['recipient_id'] for r in second} == {r['recipient_id'] for r in first}
        for bad in [node(code=' '), node(name=' '), node(sphere='internal'), dict(node(), code=12)]:
            assert send([node(code='fresh'), bad]).status_code == 422
        assert send([node()] * 10001).status_code == 422
        assert send([node()], source='history').status_code == 422
        assert client.get('/v1/outgoing/recipients/search?q=fresh', headers=headers).json()['items'] == []
        headers['X-Tenant-ID'] = 'two'
        assert client.get('/v1/outgoing/recipients/search?q=Quan', headers=headers).json()['items'] == []
        assert send([node()]).status_code == 200
        other = client.get('/v1/outgoing/recipients/search?q=Quan', headers=headers).json()
        assert len(other['items']) == 1


def test_lookup_invalid_directory_batch_leaves_person_and_units_untouched(settings):
    with TestClient(create_app(settings)) as client:
        headers = {'X-Tenant-ID': 'atomic'}
        payload = {'person': {'elements': [{'id': 1, 'type': 'dept', 'name': 'Must not appear'}]},
                   'unit_directory': {'elements': [node(), node(name=' ')]}}
        assert client.post('/v1/sync/lookup', json=payload, headers=headers).status_code == 422
        assert client.get('/v1/outgoing/recipients/search?q=appear', headers=headers).json()['items'] == []


def test_resolution_reuses_partial_checkpoint_keeps_original_and_rejects_stale_feedback(settings):
    calls = []
    async def extract(*args):
        calls.append(1)
        return Extraction(status='partial', mentions=[Mention(mention_id='m', raw='Trung tâm Quan trắc', kind='organization')])
    app = create_app(settings, extractor=extract)
    with TestClient(app) as client:
        jid = submit(client).json()['job_id']
        assert client.post(f'/v1/outgoing/jobs/{jid}/resolutions').status_code == 409
        client.portal.call(app.state.worker.run_once)
        original = app.state.store.get(jid)
        app.state.store.settings.runtime_dir.joinpath('inputs', original['input_sha256'] + '.pdf').unlink()
        enriched = client.post('/v1/sync/organizations', json={'source': 'directory', 'elements': [node()]}).json()
        assert 'registry_version' in enriched
        assert client.post(f'/v1/outgoing/jobs/{jid}/resolutions', headers={'X-Tenant-ID': 'other'}).status_code == 404
        new = client.post(f'/v1/outgoing/jobs/{jid}/resolutions')
        assert new.status_code == 202, new.text
        fresh_id = new.json()['job_id']
        assert fresh_id != jid
        assert client.post(f'/v1/outgoing/jobs/{jid}/resolutions').json()['job_id'] == fresh_id
        client.portal.call(app.state.worker.run_once)
        fresh = app.state.store.get(fresh_id)
        assert fresh['status'] == 'completed'
        assert fresh['checkpoint'] == original['checkpoint']
        assert len(calls) == 1
        assert fresh['result']['registry_version'] == enriched['registry_version']
        assert app.state.store.get(jid) == original
        body = {'registry_version': original['result']['registry_version'], 'alias_policy_version': original['result']['alias_policy_version'],
                'final_recipients': [], 'confirmed': False}
        assert client.post(f'/v1/outgoing/jobs/{jid}/feedback', json=body).json()['error']['code'] == 'stale_snapshot'
        assert client.post(f'/v1/outgoing/jobs/{fresh_id}/feedback', json=body).status_code == 409
        body.update(registry_version=fresh['result']['registry_version'], alias_policy_version=fresh['result']['alias_policy_version'])
        assert client.post(f'/v1/outgoing/jobs/{fresh_id}/feedback', json=body).status_code == 201
        assert client.post(f'/v1/outgoing/jobs/{fresh_id}/feedback', json=body, headers={'X-Tenant-ID': 'other'}).status_code == 404
        assert client.post(f'/v1/outgoing/jobs/{jid}/resolutions').json()['job_id'] == fresh_id


@pytest.mark.parametrize('reason', ['checkpoint', 'processing'])
def test_resolution_rejects_unavailable_or_incompatible_extraction(settings, reason):
    app = create_app(settings, extractor=lambda: None)
    with TestClient(app) as client:
        jid = submit(client).json()['job_id']
        with app.state.store.connection() as conn:
            conn.execute("UPDATE jobs SET status='completed', checkpoint=?, processing_version=? WHERE job_id=?",
                         (None if reason == 'checkpoint' else Extraction(status='partial').model_dump_json(),
                          'incompatible' if reason == 'processing' else app.state.store.get(jid)['processing_version'], jid))
        response = client.post(f'/v1/outgoing/jobs/{jid}/resolutions')
        assert response.status_code == 409
        assert response.json()['error']['code'] == ('extraction_unavailable' if reason == 'checkpoint' else 'incompatible_processing')

def test_existing_legacy_recipient_identity_and_frequency_survive_enrichment(settings):
    manager = TenantManager(settings)
    existing = manager.get_registry('vpub').by_id['comm_culture']
    with sqlite3.connect(settings.lookup_db) as conn:
        conn.execute("UPDATE recipients SET priority_score=120 WHERE recipient_id='comm_culture'")
    with TestClient(create_app(settings)) as client:
        response = client.post('/v1/sync/organizations', json={'source': 'directory', 'elements': [node(code='H21.17', name='New culture directory name')]} )
        assert response.status_code == 200
        found = client.get('/v1/outgoing/recipients/search?q=H21.17').json()['items']
        assert found[0]['recipient_id'] == existing.recipient_id
        with sqlite3.connect(manager.get_db_path('vpub')) as conn:
            assert conn.execute("SELECT priority_score FROM recipients WHERE recipient_id='comm_culture'").fetchone()[0] == 120


def test_identical_tenant_snapshots_and_request_keys_create_isolated_jobs(settings):
    app = create_app(settings)
    with TestClient(app) as client:
        created = []
        from test_api import pdf_bytes
        data = pdf_bytes()
        for tenant in ('one', 'two'):
            headers = {'X-Tenant-ID': tenant, 'Idempotency-Key': 'same-key'}
            assert client.post('/v1/sync/organizations', headers=headers, json={'source': 'search', 'elements': [node()]}).status_code == 200
            response = client.post('/v1/outgoing/jobs', headers=headers, files={'file': ('x.pdf', data)}, data={'metadata': '{"document_id":"same"}'})
            assert response.status_code == 202
            created.append(response.json()['job_id'])
        assert created[0] != created[1]
        assert client.get(f'/v1/outgoing/jobs/{created[0]}', headers={'X-Tenant-ID': 'two'}).status_code == 404

def test_legacy_history_raw_observation_is_retained_before_directory_updates(settings):
    manager = TenantManager(settings)
    sync_tenant_lookup('legacy', {'unit_internal': {'elements': [dict(node(), count=19)]}}, settings, manager)
    with sqlite3.connect(manager.get_db_path('legacy')) as conn:
        conn.execute('DROP TABLE organization_observations')
    with TestClient(create_app(settings)) as client:
        response = client.post('/v1/sync/organizations', headers={'X-Tenant-ID': 'legacy'},
                               json={'source': 'directory', 'elements': [node(name='Current name')]})
        assert response.status_code == 200
    with sqlite3.connect(manager.get_db_path('legacy')) as conn:
        rows = conn.execute("SELECT raw_json FROM organization_observations WHERE source='history'").fetchall()
        assert len(rows) == 1
        assert json.loads(rows[0][0])['count'] == 19

def test_unknown_legacy_job_ownership_preserves_audit_read_but_requires_reupload(settings):
    app = create_app(settings)
    with TestClient(app) as client:
        jid = submit(client).json()['job_id']
        with app.state.store.connection() as conn:
            conn.execute("UPDATE jobs SET tenant_id=NULL,status='completed',checkpoint=? WHERE job_id=?",
                         (Extraction(status='partial').model_dump_json(), jid))
        assert client.get(f'/v1/outgoing/jobs/{jid}').status_code == 200
        response = client.post(f'/v1/outgoing/jobs/{jid}/resolutions')
        assert response.status_code == 409
        assert response.json()['error']['code'] == 'reanalysis_required'
