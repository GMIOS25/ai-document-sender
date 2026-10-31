from dataclasses import replace
import json
import sqlite3
import pytest

from ai_document_sender.contracts import DocumentMetadata, Evidence, Extraction
from ai_document_sender.mentions import make_mention
from ai_document_sender.registry import Registry
from ai_document_sender.resolver import resolve_mentions
from ai_document_sender.tenants import TenantManager


def learning_file(settings, rules, **policy_fields):
    path = settings.lookup_db.parent / 'recipient_learning.v1.json'
    path.write_text(json.dumps({'version': 1, 'organization_scope': 'UBND tỉnh Gia Lai',
                                'rules': rules, **policy_fields}, ensure_ascii=False), encoding='utf-8')
    return path


def target(name, role=None):
    return {'name': name, **({'role': role} if role else {})}


async def run(registry, raw, issuer='UBND tỉnh Gia Lai', qualifier=None, section='noi_nhan', kind='group'):
    mention = make_mention(raw, kind, 1, section, qualifier=qualifier, organization_scope=issuer)
    return await resolve_mentions(Extraction(mentions=[mention], status='complete'), registry,
                                  DocumentMetadata(document_id='learning-test', issuer=issuer), 'job', 'sha')


async def test_scoped_learning_overrides_pending_policy_and_preserves_evidence(settings):
    learning_file(settings, [{'raw_alias': 'PVPQT', 'targets': [target('Trương Công Hoài', 'Phó Chánh Văn phòng')],
                              'sections': ['noi_nhan'], 'verification_status': 'verified', 'source_rows': [41]}])
    registry = Registry(settings)
    result = await run(registry, 'PVPQT', kind='role')
    assert [r.recipient_id for r in result.people] == ['internal_297']
    assert result.people[0].match_method == 'verified_sheet_alias'
    assert result.people[0].evidence[0].raw == 'PVPQT'
    assert not (await run(registry, 'PVPQT', issuer='UBND tỉnh Đắk Lắk')).people
    assert not (await run(registry, 'PVPQT', section='body_reference')).people
    restored = Registry.from_snapshot(settings, registry.snapshot())
    assert (await run(restored, 'PVPQT', kind='role')).people[0].recipient_id == 'internal_297'


@pytest.mark.parametrize('source_reference', ['Như Điều 3', 'Như Điều 4', None])
async def test_recipient_alias_applies_to_linked_article_reference_only(settings, source_reference):
    learning_file(settings, [{'raw_alias': 'PVPQT', 'targets': [target('Trương Công Hoài', 'Phó Chánh Văn phòng')],
                              'sections': ['noi_nhan'], 'verification_status': 'verified'}])
    mention = make_mention('PVPQT', 'role', 2, 'body_reference', 'PVPQT chịu trách nhiệm thi hành.',
                           references=['Như Điều 3', 'Điều 3'], organization_scope='UBND tỉnh Gia Lai')
    if source_reference:
        mention.evidence.append(Evidence(page=2, section='noi_nhan', raw=source_reference))
    result = await resolve_mentions(Extraction(mentions=[mention], status='complete'), Registry(settings),
        DocumentMetadata(document_id='article-reference', issuer='UBND tỉnh Gia Lai'), 'job', 'sha')
    if source_reference == 'Như Điều 3':
        assert [r.recipient_id for r in result.people] == ['internal_297']
        assert result.people[0].match_method == 'verified_sheet_alias'
        assert {e.section for e in result.people[0].evidence} == {'noi_nhan', 'body_reference'}
    else:
        assert not result.people


async def test_confirmed_target_route_selects_unique_unit_and_survives_reimport(settings):
    from tools.learn_recipient_sheet import compile_learning
    routes = [{'name': 'Báo Gia Lai', 'code': 'H21.94', 'sphere': 'int_province_comm',
               'verification_status': 'verified', 'verified_by': 'user'}]
    learning_file(settings, [{'raw_alias': 'Báo tỉnh', 'targets': [target('Báo Gia Lai')],
                              'sections': ['noi_nhan'], 'verification_status': 'verified'}], target_routes=routes)
    registry = Registry(settings)
    result = await run(registry, 'Báo tỉnh', kind='unit')
    assert [r.recipient_id for r in result.units] == ['comm_news_1']
    assert not result.unresolved
    assert not (await run(registry, 'Báo tỉnh', issuer='UBND tỉnh Đắk Lắk', kind='unit')).units
    restored = Registry.from_snapshot(settings, registry.snapshot())
    assert (await run(restored, 'Báo tỉnh', kind='unit')).units[0].code == 'H21.94'
    policy, report = compile_learning([{'row': 20, 'raw': 'Báo tỉnh', 'target': 'Báo Gia Lai', 'red': True}], registry)
    assert policy['target_routes'] == routes
    assert policy['rules'][0]['targets'][0]['code'] == 'H21.94'


async def test_learning_groups_require_every_unique_current_member(settings):
    learning_file(settings, [{'raw_alias': 'các PCT đã đối soát', 'targets': [
        target('Lâm Hải Giang', 'Phó Chủ tịch UBND tỉnh'),
        target('Nguyễn Thị Thanh Lịch', 'Phó Chủ tịch UBND tỉnh')], 'verification_status': 'verified'}])
    before = Registry(settings)
    assert len((await run(before, 'các PCT đã đối soát')).people) == 2
    with sqlite3.connect(settings.lookup_db) as conn:
        conn.execute("DELETE FROM recipients WHERE recipient_id='internal_278'")
    result = await run(Registry(settings), 'các PCT đã đối soát')
    assert result.people == []
    assert result.unresolved[0].reason == 'learned_target_missing'
    assert len((await run(before, 'các PCT đã đối soát')).people) == 2


async def test_learning_requires_qualifier_and_blocks_conflicts(settings):
    learning_file(settings, [
        {'raw_alias': 'NV', 'qualifier': 'Sở', 'targets': [target('Sở Nội vụ - tỉnh Gia Lai')], 'verification_status': 'verified'},
        {'raw_alias': 'Chủ tịch', 'verification_status': 'conflicting', 'targets': []}])
    registry = Registry(settings)
    assert (await run(registry, 'NV', qualifier='Sở', kind='unit')).units[0].recipient_id == 'comm_interior'
    assert not (await run(registry, 'NV', qualifier='Bộ', kind='unit')).units
    result = await run(registry, 'Chủ tịch', kind='role')
    assert not result.people and result.unresolved[0].reason == 'ambiguous_learned_alias'
    assert registry.search('NV')[0].recipient_id == 'comm_interior'


def test_learning_change_invalidates_tenant_cache_and_does_not_leak(settings):
    tenant_dir = settings.tenants_dir / 'vpub'
    tenant_dir.mkdir(parents=True)
    import shutil
    shutil.copy2(settings.lookup_db, tenant_dir / 'lookup.db')
    local = replace(settings, lookup_db=tenant_dir / 'lookup.db')
    manager = TenantManager(settings)
    before = manager.get_registry('vpub')
    learning_file(local, [{'raw_alias': 'PVPQT', 'targets': [target('Trương Công Hoài', 'Phó Chánh Văn phòng')], 'verification_status': 'verified'}])
    after = manager.get_registry('vpub')
    assert after is not before and after.alias_policy_version != before.alias_policy_version
    assert Registry(settings).alias_policy_version == before.alias_policy_version


def test_abbreviations_are_bidirectional_and_match_whole_tokens():
    from ai_document_sender.sync import build_search_tokens
    assert 'VHTTDL' in build_search_tokens('Sở Văn hóa, Thể thao và Du lịch')
    assert 'Quản lý dự án' in build_search_tokens('Ban QLDA')
    assert 'Văn phòng' not in build_search_tokens('VPUBXYZ')


def test_sheet_compiler_rejects_conflicts_and_qualifier_mismatch(settings):
    from tools.learn_recipient_sheet import compile_learning
    rows = [
        {'row': 1, 'raw': 'YT', 'target': 'Sở Nội vụ - tỉnh Gia Lai', 'qualifier': 'Sở', 'red': True},
        {'row': 2, 'raw': 'YT', 'target': 'Bộ Y tế', 'qualifier': 'Sở', 'red': True},
        {'row': 3, 'raw': 'PVPQT', 'target': 'Phó Chánh Văn phòng (Trương Công Hoài)', 'red': True},
        {'row': 4, 'raw': 'V5', 'target': 'Lê Thị Kim Yến', 'red': True},
        {'row': 5, 'raw': 'Như trên', 'target': 'Lê Thị Kim Yến', 'red': True},
    ]
    policy, report = compile_learning(rows, Registry(settings))
    rules = {r['raw_alias']: r for r in policy['rules']}
    assert rules['YT']['verification_status'] == 'conflicting'
    assert rules['PVPQT']['targets'][0]['name'] == 'Trương Công Hoài'
    assert 'V5' not in rules and 'Như trên' not in rules


def test_search_learning_survives_unchanged_sync_and_is_idempotent(settings):
    from ai_document_sender.sync import sync_tenant_lookup
    manager = TenantManager(settings)
    payload = {'person': {'elements': []}, 'unit_internal': {'elements': [
        {'uuid': 'health', 'code': 'H21.YT', 'name': 'Sở Y tế - tỉnh Gia Lai', 'count': 1}]}}
    sync_tenant_lookup('newtenant', payload, settings, manager)
    db = manager.get_db_path('newtenant')
    local = replace(settings, lookup_db=db)
    path = learning_file(local, [{'raw_alias': 'Sở YT', 'targets': [target('Sở Y tế - tỉnh Gia Lai')],
                                  'verification_status': 'verified'}])
    sync_tenant_lookup('newtenant', payload, settings, manager)
    with sqlite3.connect(db) as conn:
        text = conn.execute('SELECT search_text FROM recipients').fetchone()[0]
        assert 'Sở YT' in text
        assert conn.execute("SELECT count(*) FROM recipients_fts WHERE recipients_fts MATCH '\"YT\"'").fetchone()[0] == 1
    assert sync_tenant_lookup('newtenant', payload, settings, manager)['status'] == 'no_change'
    with sqlite3.connect(db) as conn:
        assert conn.execute('SELECT search_text FROM recipients').fetchone()[0] == text
    path.unlink()
    sync_tenant_lookup('newtenant', payload, settings, manager)
    with sqlite3.connect(db) as conn:
        assert 'Sở YT' not in conn.execute('SELECT search_text FROM recipients').fetchone()[0]


@pytest.mark.parametrize('initialize_first', [False, True])
def test_default_tenant_migration_keeps_legacy_learning(settings, initialize_first):
    from ai_document_sender.sync import sync_tenant_lookup
    learning_file(settings, [{'raw_alias': 'Sở YT', 'targets': [target('Sở Y tế - tỉnh Gia Lai')],
                              'verification_status': 'verified'}])
    manager = TenantManager(settings)
    if initialize_first:
        # conftest's read-only registry fixture omits columns present in real sync DBs.
        with sqlite3.connect(settings.lookup_db) as conn:
            conn.execute('ALTER TABLE recipients ADD COLUMN rank_level TEXT')
            conn.execute('ALTER TABLE recipients ADD COLUMN email TEXT')
            conn.execute('ALTER TABLE recipients ADD COLUMN search_text TEXT')
        manager.ensure_tenant_initialized('vpub')
    sync_tenant_lookup('vpub', {'unit_internal': {'elements': [
        {'uuid': 'health', 'code': 'H21.YT', 'name': 'Sở Y tế - tỉnh Gia Lai'}]}}, settings, manager)
    registry = manager.get_registry('vpub')
    assert registry.policy.get('learning', {}).get('rules')
    assert registry.search('Sở YT')[0].recipient_id == 'comm_health'


async def test_learning_cannot_reenter_model_candidates_after_context_rejection(settings):
    learning_file(settings, [{'raw_alias': 'UniqueOpaqueAlias', 'qualifier': 'Sở', 'sections': ['noi_nhan'],
                              'targets': [target('Sở Nội vụ - tỉnh Gia Lai')], 'verification_status': 'verified'}])
    class Provider:
        async def choose_candidate(self, *args):
            raise AssertionError('Rejected learning must not become model candidates')
    registry = Registry(settings)
    m = make_mention('UniqueOpaqueAlias', 'unit', 1, 'noi_nhan', qualifier='Bộ', organization_scope='UBND tỉnh Gia Lai')
    result = await resolve_mentions(Extraction(mentions=[m], status='complete'), registry,
        DocumentMetadata(document_id='d', issuer='UBND tỉnh Gia Lai'), 'j', 'sha', provider=Provider())
    assert not result.units


def test_search_refresh_preserves_staff_sign_rank_and_email(settings):
    from ai_document_sender.sync import sync_tenant_lookup
    manager = TenantManager(settings)
    sync_tenant_lookup('stafftest', {'person': {'elements': [
        {'id': 1, 'type': 'alias', 'name': 'Chuyên viên', 'refFullname': 'Nguyễn Văn Kiểm',
         'refUname': 'kiemnv@example.vn', 'sign': 'V5', 'rank': 'specialist'}]}}, settings, manager)
    with sqlite3.connect(manager.get_db_path('stafftest')) as conn:
        text = conn.execute('SELECT search_text FROM recipients').fetchone()[0]
        assert all(token in text for token in ('V5', 'specialist', 'kiemnv@example.vn'))
        assert conn.execute("SELECT count(*) FROM recipients_fts WHERE recipients_fts MATCH 'V5'").fetchone()[0] == 1
