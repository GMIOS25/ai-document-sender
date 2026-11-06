import pytest

from ai_document_sender.contracts import DocumentMetadata, Evidence, Extraction, Mention, Recipient
from ai_document_sender.registry import Registry
from ai_document_sender.resolver import resolve_mentions
from ai_document_sender.sync import sync_tenant_lookup
from ai_document_sender.tenants import TenantManager


def recipient(rid, name, code, internal=False):
    return Recipient(recipient_id=rid, source_id=rid, name=name, code=code,
                     recipient_type="INTERNAL_PERSON" if internal else "INT_PROVINCE_UNIT",
                     sphere="internal" if internal else "int_province_comm")


def setup_registry(settings, *recipients):
    registry = Registry(settings)
    registry.by_id.update((r.recipient_id, r) for r in recipients)
    registry._build_indexes()
    registry.tenant_id = "vpub"
    return registry


@pytest.mark.asyncio
@pytest.mark.parametrize(("day", "external", "tenant", "applies"), [
    ("2026-10-16", True, "vpub", False),
    ("2026-10-17", False, "vpub", False),
    ("2026-10-17", True, "other", False),
    ("2026-10-17", True, "vpub", True),
])
async def test_publication_policy_uses_confirmed_context_and_exact_routes(settings, day, external, tenant, applies):
    registry = setup_registry(settings,
        recipient("team", "Tổ công tác", "tct@vpub.gialai.gov.vn", True),
        recipient("pvhcc", "Trung tâm PVHCC", "H21.21.04"))
    registry.tenant_id = tenant
    metadata = DocumentMetadata.model_validate({
        "document_id": "doc", "document_date": "2026-10-12",
        "publication": {"mode": "history", "date": day, "external": external},
    })
    result = await resolve_mentions(Extraction(status="complete"), registry, metadata, "job", "hash")
    assert result.mentions == []
    assert [r.recipient_id for r in result.people] == (["team"] if applies else [])
    assert [r.recipient_id for r in result.units] == (["pvhcc"] if applies else [])
    assert [(a.recipient_id, a.field) for a in result.field_suggestions] == (
        [("team", "responsible"), ("pvhcc", "inside_unit")] if applies else [])


@pytest.mark.asyncio
async def test_group_selection_and_explicit_list_are_distinct(settings):
    members = [recipient(f"c{i}", f"UBND xã Địa phương {i} - tỉnh Gia Lai", f"H21.{i}") for i in range(100, 235)]
    registry = setup_registry(settings, *members)
    registry.unit_groups = [{
        "id": "native-group", "name": "135 xã phường", "sphere": "int_province_comm",
        "complete": True, "member_codes": [r.code for r in members],
    }]
    metadata = DocumentMetadata(document_id="doc", issuer="UBND tỉnh Gia Lai")
    async def run(raw):
        mention = Mention(mention_id="group", raw=raw, kind="group",
                          evidence=[Evidence(raw=raw, page=1, section="noi_nhan")])
        return await resolve_mentions(Extraction(mentions=[mention], status="complete"), registry, metadata, "job", "hash")
    whole = await run("UBND các xã, phường")
    assert len(whole.units) == 135
    assert [g.group_id for g in whole.selection_plan] == ["native-group"]
    subset = await run("Ủy ban nhân dân các xã, phường: Địa phương 100, Địa phương 101")
    assert {r.code for r in subset.units} == {"H21.100", "H21.101"}
    assert not subset.selection_plan
    filtered = await run("UBND các xã, phường trừ xã Địa phương 100")
    assert len(filtered.units) == 134
    assert "H21.100" not in {r.code for r in filtered.units}
    assert not filtered.selection_plan
    assert len(filtered.audit["group_dependencies"][0]["member_codes"]) == 135
    assert (await run("UBND các xã, phường trừ địa bàn chưa xác định")).unresolved

    short = "UBND các xã, phường"
    full = short + " trừ xã Địa phương 100"
    mentions = [Mention(mention_id=mid, raw=raw, kind="group",
                        evidence=[Evidence(raw=evidence, page=1, section="noi_nhan")])
                for mid, raw, evidence in [("model", short, short), ("rule", full, full)]]
    overlapping = await resolve_mentions(Extraction(mentions=mentions, status="complete"),
                                         registry, metadata, "job", "hash")
    assert len(overlapping.units) == 134
    assert not overlapping.selection_plan
    assert overlapping.unresolved[0].reason == "conflicting_group_scope"
    page = {"page": 1, "text": f"Nơi nhận:\n- {short} (trừ xã Địa phương 100);"}
    shortened = await resolve_mentions(Extraction(mentions=mentions[:1], pages=[page], status="complete"),
                                       registry, metadata, "job", "hash")
    assert not shortened.units and not shortened.selection_plan
    assert shortened.unresolved[0].reason == "conflicting_group_scope"
    no_comma = mentions[0].model_copy(update={"raw": "UBND các xã phường"})
    source_page = {"page": 1, "text": f"Nơi nhận:\n- {full};"}
    shortened = await resolve_mentions(Extraction(mentions=[no_comma, mentions[1]], pages=[source_page]),
                                       registry, metadata, "job", "hash")
    assert len(shortened.units) == 134 and not shortened.selection_plan


def test_sync_catalog_withdraws_removed_or_unavailable_groups(settings):
    mgr = TenantManager(settings)
    group = {"id": "g1", "name": "Các sở", "sphere": "int_province_comm",
             "complete": True, "member_codes": ["H21.11"]}
    sync_tenant_lookup("vpub", {"unit_groups": {"complete": True, "elements": [group]}}, settings, mgr)
    original = mgr.get_registry("vpub").registry_version
    assert mgr.get_registry("vpub").unit_groups[0]["complete"]
    sync_tenant_lookup("vpub", {"unit_groups": {"complete": False, "elements": []}}, settings, mgr)
    unavailable = mgr.get_registry("vpub")
    assert unavailable.registry_version != original
    assert unavailable.unit_groups[0]["member_codes"] == ["H21.11"]
    assert not unavailable.unit_groups[0]["complete"]
    sync_tenant_lookup("vpub", {"unit_groups": {"complete": True, "elements": []}}, settings, mgr)
    assert mgr.get_registry("vpub").unit_groups == []


@pytest.mark.asyncio
async def test_explicit_pvhcc_in_archival_line_uses_provincial_route(settings):
    registry = setup_registry(settings, recipient("pvhcc", "Trung tâm PVHCC", "H21.21.04"))
    raw = "PVHCC(KSTT)"
    mention = Mention(mention_id="pvhcc", raw=raw, kind="archive_reference",
                      evidence=[Evidence(raw="Lưu: VT, PVHCC(KSTT).", section="luu", page=2)])
    result = await resolve_mentions(Extraction(mentions=[mention]), registry,
                                    DocumentMetadata(document_id="doc"), "job", "hash")
    assert [r.recipient_id for r in result.units] == ["pvhcc"]
    assert result.units[0].evidence[0].section == "luu"
    assert not result.field_suggestions
