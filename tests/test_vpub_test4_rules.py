import json
from pathlib import Path
import sqlite3
import pytest

from ai_document_sender.config import Settings
from ai_document_sender.contracts import DocumentMetadata, Extraction
from ai_document_sender.learning import bind_targets, learned_alias
from ai_document_sender.mentions import extract_rule_mentions, make_mention
from ai_document_sender.registry import Registry
from ai_document_sender.resolver import resolve_mentions

ROOT = Path(__file__).resolve().parents[1]


def vpub_settings():
    return Settings(
        lookup_db=ROOT / "resources" / "tenants" / "vpub" / "lookup.db",
        tenants_dir=ROOT / "resources" / "tenants",
        policy_path=ROOT / "resources" / "policies" / "recipient_aliases.v1.json",
        runtime_dir=ROOT / "runtime",
        default_tenant="vpub",
    )


def expected_50_vpub_member_ids(db_path: Path) -> set[str]:
    depts = (269, 286, 318, 311, 304, 329, 338)
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            f"SELECT id FROM internal_nodes WHERE type='alias' AND parent_id IN ({','.join('?' * len(depts))})",
            depts,
        ).fetchall()
    return {f"internal_{row[0]}" for row in rows if row[0] != 334}


def expected_20_provincial_codes() -> set[str]:
    return {
        "H21.01", "H21.02", "H21.05", "H21.06", "H21.09", "H21.11", "H21.13",
        "H21.16", "H21.17", "H21.18", "H21.19", "H21.20", "H21.24", "H21.26",
        "H21.38", "H21.40", "H21.41", "H21.49", "G01.035.000.000", "G11.12.006",
    }


def test_vpub_learning_rules_bind_cleanly_with_complete_metadata():
    settings = vpub_settings()
    registry = Registry(settings)
    policy = json.loads((settings.lookup_db.parent / "recipient_learning.v1.json").read_text(encoding="utf-8"))
    for idx, rule in enumerate(policy["rules"]):
        if rule.get("verification_status") != "verified":
            continue
        members, reason = bind_targets(rule, registry)
        assert reason is None and members, f"rule[{idx}] {rule.get('raw_alias')!r} failed: {reason}"
        for t in rule.get("targets", []):
            assert t.get("recipient_type"), f"rule[{idx}] missing recipient_type on {t}"
            assert t.get("sphere"), f"rule[{idx}] missing sphere on {t}"
            assert t.get("code") or t.get("recipient_id"), f"rule[{idx}] missing code/recipient_id on {t}"
        assert "tổ chức đảng ủy ubnd tỉnh" not in rule.get("raw_alias", "").lower(), f"rule[{idx}] should be removed"


async def test_vpub_btcd_ldcv_and_20_unit_rules():
    settings = vpub_settings()
    registry = Registry(settings)
    registry.tenant_id = "vpub"
    expected_50 = expected_50_vpub_member_ids(settings.lookup_db)
    assert len(expected_50) == 50

    for alias in ("BTCD", "Ban TCD tỉnh", "Ban Tiếp công dân tỉnh", "Ban Tiếp công dân", "HSVV-TD", "HSVV, Vinh", "Long, , HSVV-TD"):
        for sec in ("kinh_gui", "noi_nhan", "luu"):
            mention = make_mention(alias, "unit", 1, sec, organization_scope="UBND tỉnh Gia Lai")
            result = await resolve_mentions(
                Extraction(mentions=[mention], status="complete"),
                registry,
                DocumentMetadata(document_id="doc-btcd-td", sign_number="13027/UBND-TD", issuer="UBND tỉnh Gia Lai"),
                "job",
                "sha",
            )
            assert {r.recipient_id for r in result.people} == {
                "internal_504", "internal_516", "internal_510", "internal_508", "internal_514", "internal_1163053"
            }, f"{alias} ({sec}) got people {[r.recipient_id for r in result.people]}"
            assert not result.units, f"{alias} ({sec}) unexpectedly matched units {[r.code for r in result.units]}"

    for alias in ("BTCD", "Ban TCD tỉnh", "Ban Tiếp công dân tỉnh", "Ban Tiếp công dân"):
        mention = make_mention(alias, "unit", 1, "noi_nhan", organization_scope="UBND tỉnh Gia Lai")
        result = await resolve_mentions(
            Extraction(mentions=[mention], status="complete"),
            registry,
            DocumentMetadata(document_id="doc-btcd-unit", sign_number="13021/UBND-NC", issuer="UBND tỉnh Gia Lai"),
            "job",
            "sha",
        )
        assert [r.code for r in result.units] == ["H21.21.01"], f"{alias} non-TD got units {result.units}"
        assert {r.recipient_id for r in result.people} == {"internal_397"}, f"{alias} non-TD unexpectedly matched people {[r.recipient_id for r in result.people]}"

    for alias, sec in [
        ("LĐ và CV Văn phòng UBND tỉnh", "noi_nhan"),
        ("LĐ và CV VP UBND tỉnh", "noi_nhan"),
        ("LĐ và CVVPUBND tỉnh", "noi_nhan"),
        ("LĐVP, CV", "noi_nhan"),
        ("Tr - LĐ, CV VP UBND tỉnh", "luu"),
    ]:
        mention = make_mention(alias, "group", 1, sec, organization_scope="UBND tỉnh Gia Lai")
        result = await resolve_mentions(
            Extraction(mentions=[mention], status="complete"),
            registry,
            DocumentMetadata(document_id="doc-ldcv", issuer="UBND tỉnh Gia Lai"),
            "job",
            "sha",
        )
        assert {r.recipient_id for r in result.people} == expected_50, f"{alias} got {len(result.people)}"
        assert "internal_334" not in {r.recipient_id for r in result.people}

    expected_20 = expected_20_provincial_codes()
    for alias in (
        "Các sở, ban, ngành",
        "Các Sở, ngành tỉnh",
        "Các sở, ban, ngành thuộc tỉnh",
        "Các sở, ban ngành tỉnh",
        "Các cơ quan chuyên môn thuộc UBND tỉnh",
        "Cơ quan chuyên môn thuộc Ủy ban nhân dân tỉnh",
        "Các cơ quan chuyên môn thuộc tỉnh",
        "Các sở, ban, ngành liên quan",
        "Các sở, ban thuộc tỉnh",
    ):
        for sec in ("kinh_gui", "noi_nhan"):
            mention = make_mention(alias, "group", 1, sec, organization_scope="UBND tỉnh Gia Lai")
            result = await resolve_mentions(
                Extraction(mentions=[mention], status="complete"),
                registry,
                DocumentMetadata(document_id="13095/UBND-NC", sign_number="13095/UBND-NC", issuer="UBND tỉnh Gia Lai"),
                "job",
                "sha",
            )
            assert {r.code for r in result.units} == expected_20, f"{alias} ({sec}) got { {r.code for r in result.units} }"

    for alias, expected_ids in [
        ("Lãnh đạo UBND tỉnh", {"internal_270", "internal_272", "internal_274", "internal_276", "internal_278", "internal_280", "internal_284"}),
        ("Chủ tịch, các PCT UBND tỉnh", {"internal_270", "internal_272", "internal_274", "internal_276", "internal_278", "internal_280", "internal_284"}),
        ("Lãnh đạo VP UBND tỉnh", {"internal_287", "internal_289", "internal_293", "internal_295", "internal_297", "internal_299"}),
        ("Lãnh đạo Văn phòng UBND tỉnh", {"internal_287", "internal_289", "internal_293", "internal_295", "internal_297", "internal_299"}),
    ]:
        m = make_mention(alias, "group", 1, "noi_nhan", organization_scope="UBND tỉnh Gia Lai")
        res = await resolve_mentions(
            Extraction(mentions=[m], status="complete"),
            registry,
            DocumentMetadata(document_id="doc-ld", issuer="UBND tỉnh Gia Lai"),
            "job",
            "sha",
        )
        assert {r.recipient_id for r in res.people} == expected_ids, f"{alias} got {[r.recipient_id for r in res.people]}"
        assert not res.units


async def test_vpub_kho_bac_ct_and_project_boards():
    settings = vpub_settings()
    registry = Registry(settings)

    m_xiv = make_mention("Kho bạc Nhà nước Khu vực XIV", "unit", 1, "noi_nhan", organization_scope="UBND tỉnh Gia Lai")
    res_xiv = await resolve_mentions(
        Extraction(mentions=[m_xiv], status="complete"),
        registry,
        DocumentMetadata(document_id="doc-kb14", issuer="UBND tỉnh Gia Lai"),
        "job",
        "sha",
    )
    assert {r.code for r in res_xiv.units} == {"G12.12.56", "G12.12.64"}
    assert all("khu vực XIV" in r.name for r in res_xiv.units)

    for raw_xv in ("Kho bạc Nhà nước khu vực XV", "Kho bạc Nhà nước Khu vực XV", "Kho bạc KV XV"):
        for sec in ("kinh_gui", "noi_nhan"):
            m_xv = make_mention(raw_xv, "unit", 1, sec, organization_scope="UBND tỉnh Gia Lai")
            res_xv = await resolve_mentions(
                Extraction(mentions=[m_xv], status="complete"),
                registry,
                DocumentMetadata(document_id="12976/UBND-KTTH", sign_number="12976/UBND-KTTH", issuer="UBND tỉnh Gia Lai"),
                "job",
                "sha",
            )
            assert [r.code for r in res_xv.units] == ["G12.12.52"]
            assert res_xv.units[0].name == "Kho bạc Nhà nước khu vực XV"

    m_ct = make_mention("CT", "role", 1, "noi_nhan", organization_scope="UBND tỉnh Gia Lai")
    res_ct = await resolve_mentions(
        Extraction(mentions=[m_ct], status="complete"),
        registry,
        DocumentMetadata(document_id="doc-ct", issuer="UBND tỉnh Gia Lai"),
        "job",
        "sha",
    )
    assert {r.recipient_id for r in res_ct.people} == {"internal_270"}
    assert not res_ct.units

    m_ct_so = make_mention("CT", "unit", 1, "noi_nhan", qualifier="Sở", organization_scope="UBND tỉnh Gia Lai")
    res_ct_so = await resolve_mentions(
        Extraction(mentions=[m_ct_so], status="complete"),
        registry,
        DocumentMetadata(document_id="doc-ct-so", issuer="UBND tỉnh Gia Lai"),
        "job",
        "sha",
    )
    assert not res_ct_so.people
    assert [r.code for r in res_ct_so.units] == ["H21.05"]

    res_ct_2 = await resolve_mentions(
        Extraction(mentions=[m_ct, m_ct_so], status="complete"),
        registry,
        DocumentMetadata(document_id="doc-ct-2", issuer="UBND tỉnh Gia Lai"),
        "job",
        "sha",
    )
    assert {r.recipient_id for r in res_ct_2.people} == {"internal_270"}
    assert [r.code for r in res_ct_2.units] == ["H21.05"]

    for raw in ("Thống kê tỉnh",):
        for sec in ("kinh_gui", "noi_nhan"):
            res_tk = await resolve_mentions(
                Extraction(mentions=[make_mention(raw, "unit", 1, sec, organization_scope="UBND tỉnh Gia Lai")], status="complete"),
                registry,
                DocumentMetadata(document_id="doc-tk", issuer="UBND tỉnh Gia Lai"),
                "job",
                "sha",
            )
            assert {r.code for r in res_tk.units} == {"H21.98", "G12.99.61"}

    res_cuc2 = await resolve_mentions(
        Extraction(mentions=[make_mention("Cục II - Thanh tra Chính phủ", "unit", 1, "noi_nhan", organization_scope="UBND tỉnh Gia Lai")], status="complete"),
        registry,
        DocumentMetadata(document_id="doc-cuc2", issuer="UBND tỉnh Gia Lai"),
        "job",
        "sha",
    )
    assert [r.code for r in res_cuc2.units] == ["000.00.11.G20"]

    res_vpub = await resolve_mentions(
        Extraction(mentions=[make_mention("Văn phòng UBND tỉnh", "unit", 1, "kinh_gui", organization_scope="UBND tỉnh Gia Lai")], status="complete"),
        registry,
        DocumentMetadata(document_id="doc-vpub", issuer="UBND tỉnh Gia Lai"),
        "job",
        "sha",
    )
    assert [r.code for r in res_vpub.units] == ["H21.21"]

    for pvhcc_raw, sec in [("PVHCC", "luu"), ("TTPVHCC", "noi_nhan"), ("Trung tâm PVHCC", "noi_nhan")]:
        res_pv = await resolve_mentions(
            Extraction(mentions=[make_mention(pvhcc_raw, "unit", 1, sec, organization_scope="UBND tỉnh Gia Lai")], status="complete"),
            registry,
            DocumentMetadata(document_id="doc-pv", issuer="UBND tỉnh Gia Lai"),
            "job",
            "sha",
        )
        assert {r.recipient_id for r in res_pv.people} == {"internal_500"}
        assert [r.code for r in res_pv.units] == ["H21.21.04"]

    res_isom = await resolve_mentions(
        Extraction(mentions=[make_mention("Các thành viên Ban Chỉ đạo phục vụ tổ chức Hội nghị ISOM – APEC 2027 tại Gia Lai", "group", 1, "kinh_gui", organization_scope="UBND tỉnh Gia Lai")], status="complete"),
        registry,
        DocumentMetadata(document_id="doc-isom", issuer="UBND tỉnh Gia Lai"),
        "job",
        "sha",
    )
    assert "020100684378" in {r.code for r in res_isom.units}
    assert len(res_isom.units) == 14

    res_sncl = await resolve_mentions(
        Extraction(mentions=[make_mention("Các đơn vị sự nghiệp công lập thuộc UBND tỉnh", "group", 1, "kinh_gui", organization_scope="UBND tỉnh Gia Lai")], status="complete"),
        registry,
        DocumentMetadata(document_id="doc-sncl", issuer="UBND tỉnh Gia Lai"),
        "job",
        "sha",
    )
    assert {r.code for r in res_sncl.units} == {"H21.43", "H21.22", "H21.39", "H21.38", "H21.40", "H21.41", "H21.49", "H21.21"}

    for raw, expected_code in [
        ("Ban Quản lý các dự án đầu tư xây dựng tỉnh", "H21.38"),
        ("Trung tâm Phát triển quỹ đất tỉnh", "H21.49"),
        ("Ban QLDA Giao thông và Dân dụng tỉnh", "H21.40"),
    ]:
        m = make_mention(raw, "unit", 1, "kinh_gui", organization_scope="UBND tỉnh Gia Lai")
        res = await resolve_mentions(
            Extraction(mentions=[m], status="complete"),
            registry,
            DocumentMetadata(document_id="doc-board", issuer="UBND tỉnh Gia Lai"),
            "job",
            "sha",
        )
        assert [r.code for r in res.units] == [expected_code], f"{raw} resolved to {[r.code for r in res.units]}"


def test_vpub_lookup_db_unit_groups_cleaned():
    settings = vpub_settings()
    with sqlite3.connect(settings.lookup_db) as conn:
        names = [row[0] for row in conn.execute("SELECT name FROM unit_groups").fetchall()]
        coastal = conn.execute("SELECT group_id, member_codes_json FROM unit_groups WHERE lower(name) LIKE '%ven biển%'").fetchall()
    assert not any("Môi trưởng" in name for name in names)
    assert len(coastal) == 1
    assert len(json.loads(coastal[0][1])) == 18


def test_vpub_muc5_qlda_boards_and_pcttt_rules():
    import asyncio
    from ai_document_sender.config import Settings
    from ai_document_sender.contracts import DocumentMetadata, Extraction
    from ai_document_sender.mentions import extract_rule_mentions, make_mention
    from ai_document_sender.resolver import resolve_mentions
    from ai_document_sender.tenants import TenantManager

    registry = TenantManager(Settings.from_env()).get_registry("vpub")
    meta = DocumentMetadata(document_id="test_stt353_74", issuer="UBND tỉnh Gia Lai")

    for qualifier in ("Ban QLDA", None):
        board_mentions = [
            make_mention("Giao thông và Dân dụng", "unit", 1, "kinh_gui", qualifier=qualifier),
            make_mention("Nông nghiệp và PTNT", "unit", 1, "kinh_gui", qualifier=qualifier),
            make_mention("Đầu tư xây dựng tỉnh", "unit", 1, "kinh_gui", qualifier=qualifier),
        ]
        board_mentions.append(make_mention("PCTTT UBND tỉnh", "person", 1, "noi_nhan"))
        result = asyncio.run(
            resolve_mentions(
                Extraction(mentions=board_mentions, status="complete"),
                registry,
                meta,
                job_id="j_stt353",
                input_sha256="h_stt353",
            )
        )
        assert {u.code for u in result.units} == {"H21.40", "H21.41", "H21.38"}
        assert {p.recipient_id for p in result.people} == {"internal_272"}
        assert result.unresolved == []


async def test_vpub_test5_round2_policy_and_unit_mappings():
    settings = vpub_settings()
    registry = Registry(settings)
    registry.tenant_id = "vpub"

    # A4 + Learning updates: unit mappings, NgV/NV qualifiers, dual HCMC police, TW BHXH
    for alias, qualifier, expected_codes in [
        ("Quỹ Phòng, chống thiên tai tỉnh", None, {"H21.24.59"}),
        ("Chi cục Kiểm lâm", None, {"H21.24.08"}),
        ("Thường trực Hội đồng nhân dân tỉnh", None, {"K21"}),
        ("NgV", "Sở", {"H21.26"}),
        ("NV", "Sở", {"H21.11"}),
        ("Đồng chí Phó Thủ tướng Chính phủ Hồ Quốc Dũng", None, {"G22"}),
        ("Cơ quan Cảnh sát điều tra Công an Thành phố Hồ Chí Minh", None, {"G01.899.000", "H29.996"}),
        ("Các đơn vị quản lý, khai thác, vận hành hồ chứa thủy lợi, thủy điện trên địa bàn tỉnh", None, {"5900182143", "4100259395"}),
        ("Công ty TNHH Lâm nghiệp Gia Lai", None, {"4100258842"}),
        ("Cty TNHH Lâm nghiệp Gia Lai", None, {"4100258842"}),
        ("VNPT Gia Lai", None, {"025900180675"}),
        ("Các doanh nghiệp viễn thông trên địa bàn tỉnh (VNPT, Viettel, MobiFone)", None, {"025900180675"}),
        ("Chủ tịch UBND phường Hội Phú", None, {"H21.105"}),
        ("UBND xã Ya Hội", None, {"H21.175"}),
    ]:
        for sec in (("kinh_gui",) if qualifier else ("kinh_gui", "noi_nhan")):
            m = make_mention(alias, "unit", 1, sec, qualifier=qualifier, organization_scope="UBND tỉnh Gia Lai")
            res = await resolve_mentions(
                Extraction(mentions=[m], status="complete"),
                registry,
                DocumentMetadata(document_id="doc-r2", issuer="UBND tỉnh Gia Lai"),
                "job",
                "sha",
            )
            assert {u.code for u in res.units} == expected_codes, f"{alias} ({sec}) got {[u.code for u in res.units]}"

    # TW agencies include BHXH (G12.98.52) on both 12843/UBND-NC and Các cơ quan Trung ương trên địa bàn tỉnh
    for alias, sign in [
        ("Các cơ quan Trung ương trên địa bàn tỉnh", "12890/UBND-KTTH"),
        ("Các cơ quan TW đóng trên địa bàn tỉnh", "12843/UBND-NC"),
    ]:
        m = make_mention(alias, "group", 1, "noi_nhan" if "TW" in alias else "kinh_gui", organization_scope="UBND tỉnh Gia Lai")
        res = await resolve_mentions(
            Extraction(mentions=[m], status="complete"),
            registry,
            DocumentMetadata(document_id="doc-tw", sign_number=sign, issuer="UBND tỉnh Gia Lai"),
            "job",
            "sha",
        )
        assert "G12.98.52" in {u.code for u in res.units}, f"{alias} missing G12.98.52"

    # A2 + A3: Phạm Anh Tuấn signer adds Lê Huy Vũ; foreign letters add Sở Ngoại vụ + Hoài + Hằng + signer
    res_pat = await resolve_mentions(
        Extraction(
            mentions=[make_mention("Chủ tịch UBND tỉnh", "role", 2, "noi_nhan")],
            pages=[{"page": 1, "text": "Kính gửi: Sở Nội vụ.\nNơi nhận:\n- Như trên;\nCHỦ TỊCH\nPhạm Anh Tuấn"}],
            status="complete",
        ),
        registry,
        DocumentMetadata(document_id="doc-pat", sign_number="13020/UBND-NC", issuer="UBND tỉnh Gia Lai"),
        "job",
        "sha",
    )
    assert "internal_289" in {p.recipient_id for p in res_pat.people}

    res_inv = await resolve_mentions(
        Extraction(
            mentions=[make_mention("Đồng chí", "role", 1, "kinh_gui")],
            pages=[{"page": 1, "text": "Kính gửi: Đồng chí\nMời tham dự Lễ Khánh thành.\nTM. ỦY BAN NHÂN DÂN\nCHỦ TỊCH\nPhạm Anh Tuấn"}],
            status="complete",
        ),
        registry,
        DocumentMetadata(document_id="doc-194", sign_number="12916/UBND-XDCT", issuer="UBND tỉnh Gia Lai"),
        "job",
        "sha",
    )
    assert "internal_289" not in {p.recipient_id for p in res_inv.people}

    res_foreign = await resolve_mentions(
        Extraction(
            mentions=[make_mention("Ngài Peter Styles, Thị trưởng thành phố Darwin, AUSTRALIA", "unit", 1, "kinh_gui")],
            pages=[{"page": 1, "text": "Kính gửi: Ngài Peter Styles\nAUSTRALIA"}, {"page": 2, "text": "Trân trọng!\nNGUYỄN HỮU QUẾ\nPhó Chủ tịch Ủy ban nhân dân tỉnh"}],
            status="complete",
        ),
        registry,
        DocumentMetadata(document_id="doc-429", sign_number="12680A/UBND-KTTH", issuer="UBND tỉnh Gia Lai"),
        "job",
        "sha",
    )
    assert {"H21.26"} <= {u.code for u in res_foreign.units}
    assert {"internal_297", "internal_479", "internal_280"} <= {p.recipient_id for p in res_foreign.people}

    res_coop = await resolve_mentions(
        Extraction(
            mentions=[make_mention("Sở Ngoại vụ", "unit", 2, "noi_nhan")],
            pages=[{"page": 1, "text": "Kính gửi: Ông X.\nCộng hòa Pháp\nĐSQ Pháp tại Việt Nam\nNơi nhận:\n- ĐSQ Pháp tại Việt Nam;\nCHỦ TỊCH\nPhạm Anh Tuấn"}],
            status="complete",
        ),
        registry,
        DocumentMetadata(document_id="doc-164", sign_number="12946/UBND-KGVX", issuer="UBND tỉnh Gia Lai"),
        "job",
        "sha",
    )
    assert {"internal_270", "internal_289"} <= {p.recipient_id for p in res_coop.people}
    assert {"H21.26"} <= {u.code for u in res_coop.units}


async def test_stt367_ld_cv_and_chu_dau_tu_rules_resolve_cleanly():
    settings = vpub_settings()
    registry = Registry(settings)
    registry.tenant_id = "vpub"
    res_367 = await resolve_mentions(
        Extraction(
            mentions=[
                make_mention("Sở Tài chính", "unit", 1, "kinh_gui"),
                make_mention("Các sở, ban, ngành, Chủ đầu tư", "group", 1, "noi_nhan", quantifier="all"),
                make_mention("LĐ, CV VP UBND tỉnh", "unit", 1, "noi_nhan"),
            ],
            pages=[{"page": 1, "text": "Kính gửi: Sở Tài chính\nNơi nhận:\n- Các sở, ban, ngành, Chủ đầu tư;\n- LĐ, CV VP UBND tỉnh;\n- Lưu: VT, T5."}],
            status="complete",
        ),
        registry,
        DocumentMetadata(document_id="doc-367", sign_number="12742/UBND-KTTH", issuer="UBND tỉnh Gia Lai"),
        "job",
        "sha",
    )
    unit_codes = {u.code for u in res_367.units}
    assert {"H21.02", "H21.19.32", "H21.19.20", "H21.24.65", "H08.70", "G01.035.000.000"} <= unit_codes
    assert len(res_367.people) >= 48
    assert not res_367.unresolved


async def test_stt490_ban_qlda_and_colonless_communes_resolve_cleanly():
    settings = vpub_settings()
    registry = Registry(settings)
    registry.tenant_id = "vpub"

    text_490 = (
        "Kính gửi:\n"
        "- Sở Công Thương;\n"
        "- Ban Quản lý dự án các công trình\n"
        "giao thông và dân dụng tỉnh;\n"
        "- UBND các xã Ia Pa, Ia Tul.\n"
        "Xét đề nghị của Sở Công Thương tại Văn bản số 5251/SCT-ĐCKS.\n"
        "2. Giao Sở Công Thương chủ trì, phối hợp với Ban Quản lý dự án các công trình giao thông và dân dụng tỉnh hướng dẫn các đơn vị.\n"
        "Nơi nhận:\n"
        "- Như trên;\n"
        "- Các Ban QLDA thuộc tỉnh;\n"
        "- UBND các xã, phường có liên quan;\n"
        "- CT, PCT UBND tỉnh;\n"
        "- CVP, PVP XD;\n"
        "- Lưu: VT, N4, X2.\n"
    )
    mentions, _ = extract_rule_mentions([{"page": 1, "text": text_490}], {"issuer": "UBND tỉnh Gia Lai"})
    by_raw = {m.raw: m for m in mentions}
    assert by_raw["Ban Quản lý dự án các công trình giao thông và dân dụng tỉnh"].kind == "unit"
    assert by_raw["Các Ban QLDA thuộc tỉnh"].kind == "group"

    res_490 = await resolve_mentions(
        Extraction(mentions=mentions, pages=[{"page": 1, "text": text_490}], status="complete"),
        registry,
        DocumentMetadata(document_id="doc-490", sign_number="12620/UBND-NNMT", issuer="UBND tỉnh Gia Lai"),
        "job",
        "sha",
    )
    unit_codes = {u.code for u in res_490.units}
    assert {"H21.05", "H21.40", "H21.149", "H21.158"} <= unit_codes
    unresolved_raws = {u.raw for u in res_490.unresolved}
    assert "Ban Quản lý dự án các công trình giao thông và dân dụng tỉnh" not in unresolved_raws
    assert "UBND các xã Ia Pa, Ia Tul" not in unresolved_raws
    assert "UBND các xã, phường có liên quan" not in unresolved_raws
    assert "commune_list_unverified" not in {u.reason for u in res_490.unresolved}
