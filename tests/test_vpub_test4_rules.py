import json
from pathlib import Path
import sqlite3
import pytest

from ai_document_sender.config import Settings
from ai_document_sender.contracts import DocumentMetadata, Extraction
from ai_document_sender.learning import bind_targets, learned_alias
from ai_document_sender.mentions import make_mention
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
    expected_50 = expected_50_vpub_member_ids(settings.lookup_db)
    assert len(expected_50) == 50

    for alias in ("BTCD", "Ban TCD tỉnh", "Ban Tiếp công dân tỉnh", "Ban Tiếp công dân"):
        for sec in ("kinh_gui", "noi_nhan", "luu"):
            mention = make_mention(alias, "unit", 1, sec, organization_scope="UBND tỉnh Gia Lai")
            result = await resolve_mentions(
                Extraction(mentions=[mention], status="complete"),
                registry,
                DocumentMetadata(document_id="doc-btcd", issuer="UBND tỉnh Gia Lai"),
                "job",
                "sha",
            )
            assert {r.recipient_id for r in result.people} == {
                "internal_504", "internal_516", "internal_508", "internal_514", "internal_1163053"
            }, f"{alias} ({sec}) got people {[r.recipient_id for r in result.people]}"
            assert not result.units, f"{alias} ({sec}) unexpectedly matched units {[r.code for r in result.units]}"

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
    for alias in ("Các sở, ban, ngành", "Các Sở, ngành tỉnh", "Các sở, ban, ngành thuộc tỉnh", "Các sở, ban ngành tỉnh"):
        mention = make_mention(alias, "group", 1, "noi_nhan", organization_scope="UBND tỉnh Gia Lai")
        result = await resolve_mentions(
            Extraction(mentions=[mention], status="complete"),
            registry,
            DocumentMetadata(document_id="13095/UBND-NC", sign_number="13095/UBND-NC", issuer="UBND tỉnh Gia Lai"),
            "job",
            "sha",
        )
        assert {r.code for r in result.units} == expected_20, f"{alias} got { {r.code for r in result.units} }"


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
    assert any(r.code in {"G12.12.56", "G12.12.64"} for r in res_xiv.units)
    assert all("khu vực XIV" in r.name for r in res_xiv.units)

    for raw_xv in ("Kho bạc Nhà nước khu vực XV", "Kho bạc Nhà nước Khu vực XV", "Kho bạc KV XV"):
        m_xv = make_mention(raw_xv, "unit", 1, "noi_nhan", organization_scope="UBND tỉnh Gia Lai")
        res_xv = await resolve_mentions(
            Extraction(mentions=[m_xv], status="complete"),
            registry,
            DocumentMetadata(document_id="12976/UBND-KTTH", sign_number="12976/UBND-KTTH", issuer="UBND tỉnh Gia Lai"),
            "job",
            "sha",
        )
        assert [r.code for r in res_xv.units] == ["G12.12.64"]
        assert res_xv.units[0].name == "Kho bạc Nhà nước khu vực XIV"

    m_ct = make_mention("CT", "role", 1, "noi_nhan", organization_scope="UBND tỉnh Gia Lai")
    res_ct = await resolve_mentions(
        Extraction(mentions=[m_ct], status="complete"),
        registry,
        DocumentMetadata(document_id="doc-ct", issuer="UBND tỉnh Gia Lai"),
        "job",
        "sha",
    )
    assert {r.recipient_id for r in res_ct.people} == {"internal_270"}
    assert {r.code for r in res_ct.units} == {"H21.05"}

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
