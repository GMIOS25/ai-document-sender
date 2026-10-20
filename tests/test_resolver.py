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
async def test_staff_code_does_not_require_sign_number_context(settings, sign_number):
    result = await resolve_mentions(Extraction(status="complete", mentions=[mention("V5", "staff_code", "luu")]),
        Registry(settings), DocumentMetadata(document_id="doc", sign_number=sign_number), "job", "hash")
    assert [p.recipient_id for p in result.people] == ["internal_341"]
    assert not result.unresolved
    assert result.audit["resolution_context"] == {"department_code":None, "department_source":"unknown"}


@pytest.mark.asyncio
async def test_explicit_department_does_not_filter_staff_codes(settings):
    result = await resolve_mentions(Extraction(status="complete", mentions=[mention("V5", "staff_code", "luu")]),
        Registry(settings), DocumentMetadata(document_id="doc", sign_number="12355/UBND-KGVX", department_code="XDCT"), "job", "hash")
    assert [p.recipient_id for p in result.people] == ["internal_341"]
    assert not result.unresolved
    assert result.audit["resolution_context"] == {"department_code":"XDCT", "department_source":"metadata"}


@pytest.mark.asyncio
@pytest.mark.parametrize("department", [None, "UBND", "KGVX", "NC"])
async def test_document_keeps_staff_codes_across_departments(settings, department):
    from ai_document_sender.mentions import extract_rule_mentions

    # Recipient lines from the 1528ATTr-UBND sample; each code is a separate recipient.
    text = "Nơi nhận:\n- CT;\n- Lưu: VT, C4, C7, V6, V4."
    mentions, _ = extract_rule_mentions([{"page": 5, "text": text}])
    # Even an extraction carrying a single department must retain the other codes.
    for item in mentions:
        item.department_context = "NC"
    result = await resolve_mentions(Extraction(status="complete", mentions=mentions), Registry(settings),
        DocumentMetadata(document_id="1528ATTr-UBND", sign_number="1528/UBND-KGVX",
                         department_code=department), "job", "hash")

    assert {p.recipient_id for p in result.people} == {
        "internal_270", "internal_332", "internal_451", "internal_489", "internal_343"}
    assert {p.name for p in result.people} == {
        "Phạm Anh Tuấn", "Văn Kim Thành", "Lê Ngọc Ngân", "Đoàn Thị Minh Hiếu", "Lê Thanh Sơn"}
    assert all(p.evidence and p.evidence[0].page == 5 for p in result.people)
    assert [u.raw for u in result.unresolved] == ["VT"]


@pytest.mark.asyncio
async def test_duplicate_staff_code_across_departments_requires_review(settings):
    import sqlite3

    with sqlite3.connect(settings.lookup_db) as conn:
        conn.execute("INSERT INTO recipients SELECT 'duplicate_v4', 'duplicate', name, 'Người khác', "
                     "'Người khác - Chuyên viên V4', '', sphere, recipient_type, 'Phòng Nội chính', "
                     "priority_score, raw_json FROM recipients WHERE recipient_id='internal_343'")
    result = await resolve(settings, [mention("V4", "staff_code", "luu")])
    assert not result.people and result.needs_review
    assert result.unresolved[0].reason == "ambiguous_registry_identity"
    assert {p.recipient_id for p in result.unresolved[0].candidates} == {"internal_343", "duplicate_v4"}


@pytest.mark.asyncio
async def test_archive_department_is_not_automatically_a_recipient(settings):
    r=await resolve(settings,[mention("KGVX","unknown","luu")])
    assert not r.people and not r.units and r.unresolved[0].reason == "policy_unknown"


@pytest.mark.parametrize("raw,kind,quantifier,rid,source_id,recipient_type", [
    ("Lãnh đạo UBND tỉnh", "unit", None, "internal_269", "269", "INTERNAL_DEPT"),
    ("Lãnh đạo Văn phòng UBND tỉnh", "group", "all", "internal_286", "286", "INTERNAL_DEPT"),
    ("Phòng Khoa giáo Văn xã", "unit", None, "internal_338", "338", "INTERNAL_DEPT"),
    ("Toàn bộ Phòng Khoa giáo Văn xã", "group", "all", "internal_338", "338", "INTERNAL_DEPT"),
    ("Tất cả Phòng Khoa giáo Văn xã", "group", "all", "internal_338", "338", "INTERNAL_DEPT"),
    ("UBND tỉnh Gia Lai", "unit", None, "internal_249", "249", "INTERNAL_UNIT"),
    ("Toàn bộ UBND tỉnh Gia Lai", "group", "all", "internal_249", "249", "INTERNAL_UNIT"),
    ("H21", "unit", None, "internal_249", "249", "INTERNAL_UNIT"),
    ("Trung tâm Phục vụ hành chính công tỉnh Gia Lai", "group", "all", "internal_1816321", "1816321", "INTERNAL_UNIT"),
])
async def test_parent_node_keeps_identity_without_expanding_children(settings, raw, kind, quantifier, rid, source_id, recipient_type):
    result = await resolve(settings, [mention(raw, kind, quantifier=quantifier)])

    assert not result.people and not result.unresolved and not result.needs_review
    assert [(r.recipient_id, r.source_id, r.recipient_type, r.sphere) for r in result.units] == [
        (rid, source_id, recipient_type, "internal")]
    assert result.units[0].mention_ids == ["m1"]
    assert result.units[0].evidence[0].raw == raw


async def test_collective_without_matching_parent_still_requires_membership(settings):
    result = await resolve(settings, [mention("Các PCT UBND tỉnh", "group", quantifier="all")])
    assert not result.people and not result.units
    assert result.unresolved[0].reason == "missing_group_membership"


async def test_parent_node_does_not_hide_duplicate_identity(settings):
    import sqlite3

    with sqlite3.connect(settings.lookup_db) as conn:
        conn.execute("INSERT INTO recipients SELECT 'duplicate_dept', 'other', name, full_name, "
                     "display_name, code, sphere, recipient_type, parent_name, priority_score, raw_json "
                     "FROM recipients WHERE recipient_id='internal_286'")
    result = await resolve(settings, [mention("Lãnh đạo Văn phòng UBND tỉnh", "group")])
    assert not result.people and not result.units and result.needs_review
    assert result.unresolved[0].reason == "ambiguous_registry_identity"
    assert {r.recipient_id for r in result.unresolved[0].candidates} == {"internal_286", "duplicate_dept"}


async def test_parent_node_does_not_replace_explicit_person_or_role_subset(settings):
    for raw in ["Trưởng Phòng Khoa giáo Văn xã", "Lãnh đạo Phòng Khoa giáo Văn xã", "Phòng không tồn tại"]:
        result = await resolve(settings, [mention(raw, "group", quantifier="all")])
        assert not result.people and not result.units and result.needs_review


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
