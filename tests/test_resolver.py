import pytest
from ai_document_sender.contracts import DocumentMetadata, Evidence, Extraction, Mention
from ai_document_sender.registry import Registry
from ai_document_sender.resolver import resolve_mentions


def mention(raw, kind="unknown", section="noi_nhan", mid="m1", **kw):
    return Mention(mention_id=mid, raw=raw, kind=kind, evidence=[Evidence(page=1, section=section, raw=raw)], **kw)


async def resolve(settings, mentions, **kw):
    return await resolve_mentions(Extraction(mentions=mentions, status="complete"), Registry(settings),
        DocumentMetadata(document_id="doc", issuer="UBND tỉnh Gia Lai", department_code="KGVX"), "job", "hash", **kw)


@pytest.mark.asyncio
async def test_chair_unique_and_initials_and_dedupe(settings):
    r = await resolve(settings, [mention("Chủ tịch UBND tỉnh", "role"), mention("Phạm Anh Tuấn", "person", mid="m2"), mention("PCT N.T.T.Lịch", "person", mid="m3")])
    assert {x.recipient_id for x in r.people} == {"internal_270", "internal_278"}
    assert len(r.people[0].evidence) == 2
    assert not r.needs_review


@pytest.mark.asyncio
async def test_bare_chair_abbreviation_in_role_context(settings):
    r=await resolve(settings,[mention("CT","role")])
    assert [p.recipient_id for p in r.people] == ["internal_270"]


@pytest.mark.asyncio
async def test_honorific_report_annotation_and_given_name_with_role(settings):
    r=await resolve(settings,[mention("Đ/c Chủ tịch UBND tỉnh (để b/c)","role"),mention("Đồng chí Lịch – PCT UBND tỉnh","person",mid="m2"),mention("PVPVX UBND tỉnh","role",mid="m3")])
    assert {p.recipient_id for p in r.people} == {"internal_270","internal_278"}
    assert r.unresolved[0].reason == "unverified_business_alias"


@pytest.mark.asyncio
async def test_conflicting_aliases_fail_closed_instead_of_lexical_fallback(settings,tmp_path):
    import json
    from dataclasses import replace
    policy=json.loads(settings.policy_path.read_text(encoding="utf-8"))
    policy["aliases"].append({"raw_alias":"CVP","canonical_role":"Chủ tịch UBND tỉnh","verification_status":"verified"})
    path=tmp_path/"conflicting.json"; path.write_text(json.dumps(policy,ensure_ascii=False),encoding="utf-8")
    r=await resolve(replace(settings,policy_path=path),[mention("CVP","role")])
    assert not r.people and r.needs_review
    assert r.unresolved[0].reason == "ambiguous_alias_policy"
    assert {p.recipient_id for p in r.unresolved[0].candidates} == {"internal_270","internal_287"}


@pytest.mark.asyncio
async def test_roles_and_pending_aliases_never_top_one(settings):
    for raw in ["PCT UBND tỉnh", "PCVP", "PVPQT", "PCVP XD", "Các PCT UBND tỉnh"]:
        r = await resolve(settings, [mention(raw, "role")])
        assert not r.people
        assert r.unresolved and r.needs_review


@pytest.mark.asyncio
async def test_staff_code_and_vt_policy_unknown(settings):
    r = await resolve(settings, [mention("V1", "staff_code", "luu"), mention("V5", "staff_code", "luu", mid="m2"), mention("V8", "staff_code", "luu", mid="m3"), mention("VT", "unknown", "luu", mid="m4")])
    assert {x.recipient_id for x in r.people} == {"internal_491", "internal_341", "internal_485"}
    assert r.unresolved[0].reason == "policy_unknown"
    assert not r.excluded


@pytest.mark.asyncio
async def test_staff_codes_use_verified_sign_number_suffix_when_department_absent(settings):
    metadata = DocumentMetadata(document_id="doc", sign_number="12355/UBND-KGVX")
    extraction = Extraction(status="complete", mentions=[
        mention("V1", "staff_code", "luu"), mention("V5", "staff_code", "luu", mid="m2"),
        mention("V8", "staff_code", "luu", mid="m3")])
    result = await resolve_mentions(extraction, Registry(settings), metadata, "job", "hash")
    assert {p.recipient_id for p in result.people} == {"internal_491", "internal_341", "internal_485"}
    assert not result.unresolved
    assert result.audit["resolution_context"] == {"department_code":"KGVX", "department_source":"sign_number_suffix"}
    assert metadata.department_code is None and metadata.issuer is None


@pytest.mark.asyncio
@pytest.mark.parametrize("sign_number", ["12355/UBND-UNKNOWN", "12355/VP-KGVX", "internal_uuid/UBND-KGVX", "12355/UBND-KGVX-extra"])
async def test_staff_code_unknown_sign_number_context_abstains(settings, sign_number):
    result = await resolve_mentions(Extraction(status="complete", mentions=[mention("V5", "staff_code", "luu")]),
        Registry(settings), DocumentMetadata(document_id="doc", sign_number=sign_number), "job", "hash")
    assert not result.people and result.unresolved and result.needs_review
    assert result.audit["resolution_context"] == {"department_code":None, "department_source":"unknown"}


@pytest.mark.asyncio
async def test_explicit_department_is_not_overridden_by_sign_number(settings):
    result = await resolve_mentions(Extraction(status="complete", mentions=[mention("V5", "staff_code", "luu")]),
        Registry(settings), DocumentMetadata(document_id="doc", sign_number="12355/UBND-KGVX", department_code="XDCT"), "job", "hash")
    assert not result.people and result.unresolved
    assert result.audit["resolution_context"] == {"department_code":"XDCT", "department_source":"metadata"}


@pytest.mark.asyncio
async def test_archive_department_is_not_automatically_a_recipient(settings):
    r=await resolve(settings,[mention("KGVX","unknown","luu")])
    assert not r.people and not r.units and r.unresolved[0].reason == "policy_unknown"


@pytest.mark.asyncio
async def test_unit_keeps_issuer_context_without_becoming_child_of_issuer(settings):
    r=await resolve(settings,[mention("Sở Văn hóa, Thể thao và Du lịch - tỉnh Gia Lai","unit",organization_scope="UBND tỉnh Gia Lai")])
    assert [u.recipient_id for u in r.units] == ["comm_culture"]


@pytest.mark.asyncio
async def test_duplicates_missing_entity_and_model_ids(settings):
    r = await resolve(settings, [mention("Báo Gia Lai", "unit"), mention("Sở Ngoại vụ - tỉnh Gia Lai", "unit", mid="m2"), mention("Nguyễn Văn Đã Nghỉ", "person", mid="m3")])
    assert not r.people and not r.units
    assert [u.reason for u in r.unresolved] == ["ambiguous_registry_identity", "not_in_registry", "not_in_registry"]
    class Bad:
        async def choose_candidate(self, *args): return "invented-id"
    r = await resolve(settings, [mention("Sở văn hoá TT DL", "unit")], provider=Bad())
    assert not r.units
    assert r.needs_review and r.unresolved[0].reason == "invalid_model_output"


@pytest.mark.asyncio
async def test_named_officeholder_not_replaced_and_nfd_initials(settings):
    import unicodedata
    r=await resolve(settings,[mention("Chủ tịch UBND tỉnh Nguyễn Văn Đã Nghỉ","person"),mention(unicodedata.normalize("NFD","PCT N.T.T.Lịch"),"person",mid="m2")])
    assert {x.recipient_id for x in r.people} == {"internal_278"}
    assert r.unresolved[0].raw == "Chủ tịch UBND tỉnh Nguyễn Văn Đã Nghỉ"
    spaced=await resolve(settings,[mention("PCT  N.T.T.Lịch","person")])
    assert [p.recipient_id for p in spaced.people] == ["internal_278"]


@pytest.mark.asyncio
async def test_generic_provincial_association_not_wrong_province(settings):
    import sqlite3
    with sqlite3.connect(settings.lookup_db) as c:
        c.execute("INSERT INTO recipients VALUES ('outside_association','source','Hội Văn học Nghệ thuật tỉnh',NULL,'Hội Văn học Nghệ thuật tỉnh','A15.10.19','ext_province_comm','EXT_PROVINCE_UNIT','Outside',1000,'{}')")
    r=await resolve(settings,[mention("Hội Văn học Nghệ thuật tỉnh","unit")])
    assert not r.units and r.unresolved


@pytest.mark.asyncio
async def test_partial_always_needs_review(settings):
    r = await resolve_mentions(Extraction(status="partial"), Registry(settings), DocumentMetadata(document_id="doc"), "j", "h")
    assert r.needs_review and "extraction_partial" in r.review_reasons
