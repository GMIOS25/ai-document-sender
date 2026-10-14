import asyncio
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from ai_document_sender.contracts import DocumentMetadata
from ai_document_sender.extraction import extract_document
from ai_document_sender.mentions import extract_rule_mentions
from test_extraction import FakeProvider, pages


DECISION = '''Điều 1. Nội dung quyết định.
Điều 3. Quyết định này có hiệu lực thi hành kể từ ngày ký.
Chánh Văn phòng Ủy ban nhân dân tỉnh, Giám đốc các Sở: Nông nghiệp
và Môi trường, Tài chính, Công Thương, Xây dựng; Trưởng Thuế tỉnh, Chủ tịch
Ủy ban nhân dân xã Hội Sơn, Thủ trưởng các cơ quan, đơn vị liên quan và Giám
đốc Công ty TNHH Xây dựng Hồng Châu chịu trách nhiệm thi hành Quyết định
này./.
Nơi nhận:
-Như Điều 3;
- Lưu: VT, N4.
KT. CHỦ TỊCH
Nguyễn Tuấn Thanh
'''


def test_article_recovers_responsible_people_units_and_explicit_department_list():
    mentions, reasons = extract_rule_mentions(pages(DECISION))
    selectors = {" ".join(filter(None, (m.qualifier, m.raw))) for m in mentions}
    assert {
        "Chánh Văn phòng Ủy ban nhân dân tỉnh", "Sở Nông nghiệp và Môi trường",
        "Sở Tài chính", "Sở Công Thương", "Sở Xây dựng", "Thuế tỉnh",
        "Ủy ban nhân dân xã Hội Sơn", "Công ty TNHH Xây dựng Hồng Châu",
        "Thủ trưởng các cơ quan, đơn vị liên quan",
    } <= selectors
    assert not any(m.kind == "reference" or m.raw == "Nguyễn Tuấn Thanh" for m in mentions)
    assert "unsupported_reference" not in reasons
    for mention in mentions:
        if mention.evidence[0].section == "body_reference":
            assert "Như Điều 3" in mention.references
            assert any(e.section == "noi_nhan" and e.raw == "Như Điều 3" for e in mention.evidence)


def test_article_spans_pages_and_stops_at_next_article():
    source = [
        {"page": 1, "text": "Điều 3. Chánh Văn phòng UBND tỉnh, Sở Nông nghiệp và"},
        {"page": 2, "text": "2\nMôi trường chịu trách nhiệm thi hành.\nĐiều 4. Sở Y tế chịu trách nhiệm.\nNơi nhận:\n- Như Điều 3;"},
    ]
    mentions, reasons = extract_rule_mentions(source)
    assert {"Chánh Văn phòng UBND tỉnh", "Sở Nông nghiệp và Môi trường"} <= {m.raw for m in mentions}
    assert not any("Y tế" in m.raw for m in mentions)
    assert not reasons
    assert {e.page for m in mentions for e in m.evidence if e.section == "body_reference"} == {1, 2}


def test_responsibility_article_recovers_assigned_and_coordinating_units_only():
    text = '''Điều 3. Trách nhiệm của các cơ quan có liên quan:
1. Giao Sở Công Thương chủ trì, phối hợp với Sở Tài chính xác định tiền
cấp quyền khai thác và trình UBND tỉnh phê duyệt.
2. Giao UBND phường Quy Nhơn Đông chủ trì, phối hợp với Ban Quản lý
Khu kinh tế tỉnh, chủ đầu tư và đơn vị thi công tuyên truyền thông tin.
3. Giao Thuế tỉnh Gia Lai đôn đốc Công ty TNHH Đại An nộp nghĩa vụ tài chính.
Nơi nhận:
- Như Điều 3;
'''
    mentions, reasons = extract_rule_mentions(pages(text))
    assert {"Sở Công Thương", "Sở Tài chính", "UBND phường Quy Nhơn Đông",
            "Ban Quản lý Khu kinh tế tỉnh"} <= {m.raw for m in mentions}
    assert "unsupported_reference" not in reasons
    assert not any(m.raw in {"UBND tỉnh", "Công ty TNHH Đại An"} for m in mentions)


def test_nested_person_reference_follows_article_to_attached_list():
    source = [
        {"page": 1, "text": "Điều 1. Tổ chức Đoàn công tác (có danh sách kèm theo).\nĐiều 2. Sở Tài chính cấp kinh phí."},
        {"page": 2, "text": "Điều 3. Chánh Văn phòng UBND tỉnh, Giám đốc Sở Ngoại vụ, thủ trưởng các cơ quan liên quan và các cá nhân tại Điều 1 chịu trách nhiệm thi hành.\nNơi nhận:\n- Như Điều 3;\nKT. CHỦ TỊCH\nNgười Ký Khác"},
        {"page": 3, "text": "DANH SÁCH\nĐOÀN CÔNG TÁC (Kèm theo Quyết định này)\nI. Thành phần chính thức:\n1. Ông Phạm Anh Tuấn, Chủ tịch UBND tỉnh;\n2. Bà Phạm Thị Tố Hải, Giám đốc Sở Nội vụ;"},
        {"page": 4, "text": "4\nII. Thành phần mời:\n1. Ông Đoàn Đức Tùng, Hiệu trưởng Trường Đại học Quy Nhơn."},
    ]
    mentions, reasons = extract_rule_mentions(source)
    assert {"Phạm Anh Tuấn", "Phạm Thị Tố Hải", "Đoàn Đức Tùng", "Sở Ngoại vụ"} <= {m.raw for m in mentions}
    assert not any(m.raw in {"Sở Nội vụ", "Sở Tài chính", "Người Ký Khác"} for m in mentions)
    assert "unsupported_reference" not in reasons
    person = next(m for m in mentions if m.raw == "Đoàn Đức Tùng")
    assert person.kind == "person"
    assert {e.page for e in person.evidence} >= {1, 2, 4}


@pytest.mark.parametrize("text", [
    "Điều 2. Sở Y tế chịu trách nhiệm.\nNơi nhận:\n- Như Điều 3;",
    "Điều 3. Các cá nhân tại Điều 1 chịu trách nhiệm.\nNơi nhận:\n- Như Điều 3;",
    "Điều 1. Các cá nhân tại Điều 3 chịu trách nhiệm.\nĐiều 3. Các cá nhân tại Điều 1 chịu trách nhiệm.\nNơi nhận:\n- Như Điều 3;",
])
def test_missing_or_cyclic_article_reference_remains_unresolved(text):
    mentions, reasons = extract_rule_mentions(pages(text))
    assert any(m.kind == "reference" for m in mentions)
    assert "unsupported_reference" in reasons
    assert not any(m.raw == "Sở Y tế" for m in mentions)


def test_article_model_output_does_not_return_article_number_as_unit(settings):
    provider = FakeProvider({"mentions": [
        {"raw": "Điều 3", "kind": "unit", "evidence": [{"page": 1, "section": "noi_nhan", "raw": "Như Điều 3"}]},
        {"raw": "Thuế tỉnh", "kind": "unit", "references": ["Như Điều 3"],
         "evidence": [{"page": 1, "section": "body_reference", "raw": "Trưởng Thuế tỉnh"}]},
    ], "status": "complete", "review_reasons": [], "ocr_pages": []})
    with patch("ai_document_sender.extraction._read_pages", return_value=pages(DECISION)):
        result = asyncio.run(extract_document(Path("unused.pdf"), provider, DocumentMetadata(document_id="article"), settings))
    assert not any(m.raw in {"Điều 3", "Như Điều 3"} for m in result.mentions)
    assert "unsupported_reference" not in result.review_reasons
    assert any(m.raw == "Thuế tỉnh" for m in result.mentions)


def test_ocr_body_reference_is_expanded_after_transcription(settings):
    provider = FakeProvider({"mentions": [], "status": "partial", "review_reasons": [],
                             "ocr_pages": [{"page": 1, "text": DECISION}]})
    with patch("ai_document_sender.extraction._read_pages", return_value=pages("")), patch(
        "ai_document_sender.extraction._render_pages", return_value=[{"page": 1, "data_url": "data:image/png;base64,AA=="}]
    ):
        result = asyncio.run(extract_document(Path("unused.pdf"), provider, DocumentMetadata(document_id="scan"), settings))
    assert any(m.raw == "Thuế tỉnh" and m.evidence[0].section == "body_reference" for m in result.mentions)
    assert not any(m.raw == "Như Điều 3" for m in result.mentions)


def test_person_selector_recovers_explicit_people_in_referenced_article():
    text = """Điều 1. Ông Phạm Anh Tuấn, Bà Phạm Thị Tố Hải chịu trách nhiệm thực hiện.
Điều 3. Các cá nhân tại Điều 1 chịu trách nhiệm thi hành.
Nơi nhận:
- Như Điều 3;"""
    mentions, reasons = extract_rule_mentions(pages(text))
    assert {m.raw for m in mentions if m.kind == "person"} == {"Phạm Anh Tuấn", "Phạm Thị Tố Hải"}
    assert not reasons


def test_unit_selector_does_not_promote_people_or_their_employers():
    text = """Điều 1. Tổ chức đoàn (có danh sách kèm theo).
Điều 3. Các đơn vị tại Điều 1 chịu trách nhiệm thi hành.
Nơi nhận:
- Như Điều 3;
DANH SÁCH
1. Ông Nguyễn Văn An, Giám đốc Sở Y tế."""
    mentions, reasons = extract_rule_mentions(pages(text))
    assert not any(m.kind == "person" or m.raw == "Sở Y tế" for m in mentions)
    assert any(m.kind == "reference" for m in mentions)
    assert "unsupported_reference" in reasons


def test_missing_nested_reference_is_retained_alongside_resolved_subjects():
    text = """Điều 3. Chánh Văn phòng UBND tỉnh và các cá nhân tại Điều 1 chịu trách nhiệm.
Nơi nhận:
- Như Điều 3;"""
    mentions, reasons = extract_rule_mentions(pages(text))
    assert any(m.raw == "Chánh Văn phòng UBND tỉnh" for m in mentions)
    assert any(m.kind == "reference" for m in mentions)
    assert "unsupported_reference" in reasons


def test_person_reference_does_not_add_incidental_person_in_unit_duty():
    text = """Điều 1. Giao Sở Y tế hướng dẫn Ông Nguyễn Văn An nộp hồ sơ.
Điều 3. Các cá nhân tại Điều 1 chịu trách nhiệm.
Nơi nhận:
- Như Điều 3;"""
    mentions, reasons = extract_rule_mentions(pages(text))
    assert not any(m.kind == "person" for m in mentions)
    assert "unsupported_reference" in reasons


def test_body_model_can_include_source_link_but_cannot_invent_extra_evidence(settings):
    body = {"raw": "Thuế tỉnh", "kind": "unit", "references": ["Như Điều 3"], "evidence": [
        {"page": 1, "section": "noi_nhan", "raw": "Như Điều 3"},
        {"page": 1, "section": "body_reference", "raw": "Trưởng Thuế tỉnh"},
    ]}
    provider = FakeProvider({"mentions": [body], "status": "complete", "review_reasons": [], "ocr_pages": []})
    with patch("ai_document_sender.extraction._read_pages", return_value=pages(DECISION)):
        result = asyncio.run(extract_document(Path("unused.pdf"), provider, DocumentMetadata(document_id="body"), settings))
    assert result.status == "complete"
    assert not result.review_reasons

    body["evidence"].append({"page": 1, "section": "kinh_gui", "raw": "Evidence invented"})
    with patch("ai_document_sender.extraction._read_pages", return_value=pages(DECISION)):
        invalid = asyncio.run(extract_document(Path("unused.pdf"), provider, DocumentMetadata(document_id="body"), settings))
    assert "ungrounded_model_mention" in invalid.review_reasons


def test_unlinked_or_incidental_model_body_entity_is_rejected(settings):
    text = """Điều 3. Giao Thuế tỉnh hướng dẫn Công ty TNHH Đại An nộp thuế.
Nơi nhận:
- Như Điều 3;"""
    provider = FakeProvider({"mentions": [{"raw": "Công ty TNHH Đại An", "kind": "unit",
        "references": ["Như Điều 3"], "evidence": [{"page": 1, "section": "body_reference",
                                                  "raw": "Công ty TNHH Đại An"}]}],
        "status": "complete", "review_reasons": [], "ocr_pages": []})
    with patch("ai_document_sender.extraction._read_pages", return_value=pages(text)):
        result = asyncio.run(extract_document(Path("unused.pdf"), provider, DocumentMetadata(document_id="incidental"), settings))
    assert not any(m.raw == "Công ty TNHH Đại An" for m in result.mentions)
    assert "ungrounded_model_mention" in result.review_reasons


def test_named_responsible_person_does_not_add_appositive_employer():
    text = """Điều 3. Ông Nguyễn Văn An, Giám đốc Sở Y tế và Sở Nội vụ chịu trách nhiệm.
Nơi nhận:
- Như Điều 3;"""
    mentions, reasons = extract_rule_mentions(pages(text))
    assert {"Nguyễn Văn An", "Sở Nội vụ"} <= {m.raw for m in mentions}
    assert not any(m.raw == "Sở Y tế" for m in mentions)
    assert not reasons


def test_empty_body_evidence_cannot_certify_a_linked_recipient(settings):
    provider = FakeProvider({"mentions": [{"raw": "Thuế tỉnh", "kind": "unit",
        "references": ["Như Điều 3"], "evidence": [{"page": 1, "section": "body_reference",
                                                  "raw": "thi hành"}]}],
        "status": "complete", "review_reasons": [], "ocr_pages": []})
    with patch("ai_document_sender.extraction._read_pages", return_value=pages(DECISION)):
        result = asyncio.run(extract_document(Path("unused.pdf"), provider, DocumentMetadata(document_id="empty-evidence"), settings))
    assert "ungrounded_model_mention" in result.review_reasons


def test_duplicate_article_heading_is_not_guessed():
    text = """Điều 3. Sở Y tế chịu trách nhiệm.
Điều 3. Sở Nội vụ chịu trách nhiệm.
Nơi nhận:
- Như Điều 3;"""
    mentions, reasons = extract_rule_mentions(pages(text))
    assert all(m.kind == "reference" for m in mentions)
    assert "unsupported_reference" in reasons


def test_model_article_number_is_rejected_even_with_whole_recipient_block(settings):
    provider = FakeProvider({"mentions": [{"raw": "Điều 3", "kind": "unit",
        "evidence": [{"page": 1, "section": "noi_nhan", "raw": "Như Điều 3;\n- Lưu: VT"}]}],
        "status": "complete", "review_reasons": [], "ocr_pages": []})
    with patch("ai_document_sender.extraction._read_pages", return_value=pages(DECISION)):
        result = asyncio.run(extract_document(Path("unused.pdf"), provider, DocumentMetadata(document_id="article-number"), settings))
    assert not any(m.raw == "Điều 3" for m in result.mentions)


def test_attached_person_name_can_wrap_to_next_line():
    text = """Điều 1. Tổ chức đoàn (có danh sách kèm theo).
Điều 3. Các cá nhân tại Điều 1 chịu trách nhiệm.
Nơi nhận:
- Như Điều 3;
DANH SÁCH
1. Ông Nguyễn Văn
An, Giám đốc Sở Y tế."""
    mentions, reasons = extract_rule_mentions(pages(text))
    assert {m.raw for m in mentions if m.kind == "person"} == {"Nguyễn Văn An"}
    assert not reasons


def test_unreadable_attached_list_is_retained_even_with_explicit_responsible_person():
    text = """Điều 1. Ông Nguyễn Văn An chịu trách nhiệm chuẩn bị.
Tổ chức đoàn (có danh sách kèm theo).
Điều 3. Các cá nhân tại Điều 1 chịu trách nhiệm thi hành.
Nơi nhận:
- Như Điều 3;
DANH SÁCH
Thành phần đoàn sẽ được bổ sung."""
    mentions, reasons = extract_rule_mentions(pages(text))
    assert any(m.raw == "Nguyễn Văn An" for m in mentions)
    assert any(m.kind == "reference" for m in mentions)
    assert "unsupported_reference" in reasons


def test_named_person_office_title_is_context_and_coordination_is_split():
    text = """Điều 3. Ông Nguyễn Văn An, Chánh Văn phòng UBND tỉnh chịu trách nhiệm.
Giao Sở Y tế phối hợp với Sở Nội vụ thực hiện.
Nơi nhận:
- Như Điều 3;"""
    mentions, reasons = extract_rule_mentions(pages(text))
    assert {m.raw for m in mentions} == {"Nguyễn Văn An", "Sở Y tế", "Sở Nội vụ"}
    assert not reasons


@pytest.mark.parametrize("label", ["-Như Điều 3", "• Điều 3"])
def test_bullet_prefixed_model_article_label_is_not_a_unit(label, settings):
    provider = FakeProvider({"mentions": [{"raw": label, "kind": "unit",
        "evidence": [{"page": 1, "section": "noi_nhan", "raw": "-Như Điều 3;\n- Lưu: VT"}]}],
        "status": "complete", "review_reasons": [], "ocr_pages": []})
    with patch("ai_document_sender.extraction._read_pages", return_value=pages(DECISION)):
        result = asyncio.run(extract_document(Path("unused.pdf"), provider, DocumentMetadata(document_id="bullet-label"), settings))
    assert not any(m.raw == label for m in result.mentions)


@pytest.mark.parametrize("descendant, expected, missing", [
    ("", {"Nguyễn Văn An"}, True),
    ("Điều 2. Bà Trần Thị Bình chịu trách nhiệm tham gia.", {"Nguyễn Văn An", "Trần Thị Bình"}, False),
])
def test_nested_participant_clause_is_followed_or_retained(descendant, expected, missing):
    text = f"""Điều 1. Ông Nguyễn Văn An chịu trách nhiệm chuẩn bị.
Các cá nhân tại Điều 2 cùng tham gia đoàn công tác.
{descendant}
Điều 3. Các cá nhân tại Điều 1 chịu trách nhiệm thi hành.
Nơi nhận:
- Như Điều 3;"""
    mentions, reasons = extract_rule_mentions(pages(text))
    assert {m.raw for m in mentions if m.kind == "person"} == expected
    assert ("unsupported_reference" in reasons) == missing
    assert any(m.kind == "reference" for m in mentions) == missing


def test_police_and_inspectorate_in_responsibility_list_are_both_retained():
    text = """Điều 3. Giám đốc Công an tỉnh, Chánh Thanh tra tỉnh, Trưởng Thuế tỉnh chịu trách nhiệm thi hành.
Nơi nhận:
- Như Điều 3;"""
    mentions, reasons = extract_rule_mentions(pages(text))
    assert {m.raw for m in mentions} == {"Công an tỉnh", "Thanh tra tỉnh", "Thuế tỉnh"}
    assert not reasons


@pytest.mark.parametrize("unread_member", ["Trần Văn Bình, Thành viên.", ""])
def test_unparsed_attached_member_is_retained_alongside_recovered_people(unread_member):
    text = f"""Điều 1. Tổ chức đoàn (có danh sách kèm theo).
Điều 3. Các cá nhân tại Điều 1 chịu trách nhiệm thi hành.
Nơi nhận:
- Như Điều 3;
DANH SÁCH
1. Ông Nguyễn Văn An, Trưởng đoàn;
2. {unread_member}"""
    mentions, reasons = extract_rule_mentions(pages(text))
    assert any(m.raw == "Nguyễn Văn An" and m.kind == "person" for m in mentions)
    assert any(m.kind == "reference" for m in mentions)
    assert "unsupported_reference" in reasons


def test_full_page_ocr_preserves_existing_clean_recipient_column(settings):
    source = pages(DECISION)
    source[0]["recipient_text"] = "Nơi nhận:\n-Như Điều 3;\n- Lưu: VT, N4."
    source[0]["images"] = [{"bbox": [20, 570, 330, 800]}]
    ocr = DECISION.replace("-Như Điều 3;", "-Như Điều 3; PHÓ CHỦ TỊCH")
    provider = FakeProvider({"mentions": [], "status": "partial", "review_reasons": [],
                             "ocr_pages": [{"page": 1, "text": ocr}]})
    with patch("ai_document_sender.extraction._read_pages", return_value=source), patch(
        "ai_document_sender.extraction._render_pages", return_value=[{"page": 1, "data_url": "data:image/png;base64,AA=="}]
    ):
        result = asyncio.run(extract_document(Path("unused.pdf"), provider, DocumentMetadata(document_id="hybrid-article"), settings))
    assert any(m.raw == "Thuế tỉnh" for m in result.mentions)
    assert not any(m.kind == "reference" for m in result.mentions)


def test_3654_actual_ocr_follows_article_one_and_recovers_attached_members():
    source = json.loads((Path(__file__).parent / "fixtures/3654_vietocr_pages.json").read_text(encoding="utf-8"))
    mentions, reasons = extract_rule_mentions(source)
    people = {m.raw: m for m in mentions if m.kind == "person"}
    expected = {
        "Phạm Anh Tuấn", "Phạm Thị Tố Hải", "Trần Đình Hiệp", "Đỗ Thị Diệu Hạnh",
        "Đỗ Việt Hưng", "Nguyễn Hữu Hà", "Nguyễn Hữu Khúc", "Vũ Mạnh Định",
        "Võ Gia Nghĩa", "Nguyễn Bay", "Lê Đức Phương", "Trần Đức Hải", "Đoàn Đức Tùng",
        "Nguyễn Thanh Hồng", "Văn Bích Ngọc", "Hồ Thị Liên Hương", "Lê Văn Thảo",
        "Trần Việt Anh", "Trần Như Long", "Dương Quỳnh Hoa", "Nguyễn Tuấn Anh",
        "Ngô Hà Khánh Linh", "Nguyễn Thanh Phong", "Nguyễn Thanh Trang",
        "Đoàn Bảo Sang", "Hoàng Quý Thạch",
    }
    assert set(people) == expected
    for person in people.values():
        assert person.references == ["Như Điều 3", "Điều 3", "Điều 1", "Danh sách kèm theo"]
    assert any(e.page == 4 and "Hoàng Quý Thạch" in e.raw for e in people["Hoàng Quý Thạch"].evidence)
    # One OCR row lost its name; preserve it for review instead of guessing.
    assert any(m.kind == "reference" and m.raw.startswith("nn Thu nhi") for m in mentions)
    assert not any(m.raw in {"Điều 1", "Danh sách kèm theo", "Sở Nội vụ"} for m in mentions)
    assert "unsupported_reference" in reasons


def test_nested_section_and_point_references_are_followed():
    text = """Mục II. Các cá nhân được nêu tại Điểm a cùng tham gia đoàn công tác.
Điểm a. Ông Nguyễn Văn An chịu trách nhiệm tham gia.
Mục III. Trách nhiệm thi hành:
Điều 3. Chánh Văn phòng UBND tỉnh và các cá nhân quy định tại Mục II chịu trách nhiệm thi hành.
Nơi nhận:
- Như Điều 3;"""
    mentions, reasons = extract_rule_mentions(pages(text))
    assert {m.raw for m in mentions} == {"Chánh Văn phòng UBND tỉnh", "Nguyễn Văn An"}
    person = next(m for m in mentions if m.kind == "person")
    assert person.references == ["Như Điều 3", "Điều 3", "Mục II", "Điểm a"]
    assert not reasons


@pytest.mark.parametrize("target, heading", [("Mục II", "Mục II."), ("Điểm a", "Điểm a.")])
def test_reference_can_start_at_section_or_point(target, heading):
    text = f"""{heading} Ông Nguyễn Văn An chịu trách nhiệm thực hiện.
Nơi nhận:
- Như {target};"""
    mentions, reasons = extract_rule_mentions(pages(text))
    assert [(m.raw, m.kind) for m in mentions] == [("Nguyễn Văn An", "person")]
    assert not reasons


def test_cyclic_section_reference_retains_valid_recipient_and_unresolved_link():
    text = """Mục II. Các cá nhân tại Điểm a chịu trách nhiệm.
Điểm a. Các cá nhân tại Mục II chịu trách nhiệm.
Điều 3. Chánh Văn phòng UBND tỉnh và các cá nhân tại Mục II chịu trách nhiệm.
Nơi nhận:
- Như Điều 3;"""
    mentions, reasons = extract_rule_mentions(pages(text))
    assert any(m.raw == "Chánh Văn phòng UBND tỉnh" for m in mentions)
    assert any(m.kind == "reference" for m in mentions)
    assert "unsupported_reference" in reasons


def test_nested_numbered_point_uses_clause_and_article_context():
    text = """Điều 1. Thành phần đoàn công tác:
1. Thành phần chính thức:
a) Ông Nguyễn Văn An chịu trách nhiệm tham gia.
b) Bà Trần Thị Bình chịu trách nhiệm phục vụ.
Điều 2. Đoàn công tác khác:
1. Thành phần chính thức:
a) Ông Lê Văn Cường chịu trách nhiệm tham gia.
Điều 3. Các cá nhân quy định tại điểm a khoản 1 Điều 1 chịu trách nhiệm thi hành.
Nơi nhận:
- Như Điều 3;"""
    mentions, reasons = extract_rule_mentions(pages(text))
    assert {m.raw for m in mentions} == {"Nguyễn Văn An"}
    assert not reasons


def test_bare_point_reference_respects_its_containing_clause():
    text = """Điều 1. Thành phần đoàn công tác:
1. Các cá nhân tại điểm a cùng tham gia đoàn.
a) Ông Nguyễn Văn An chịu trách nhiệm tham gia.
2. Thành phần hỗ trợ:
a) Bà Trần Thị Bình chịu trách nhiệm phục vụ.
Điều 3. Các cá nhân tại khoản 1 Điều 1 chịu trách nhiệm thi hành.
Nơi nhận:
- Như Điều 3;"""
    mentions, reasons = extract_rule_mentions(pages(text))
    assert {m.raw for m in mentions} == {"Nguyễn Văn An"}
    assert any("Điểm a" in m.references for m in mentions)
    assert not reasons


def test_ambiguous_unqualified_point_is_not_expanded_from_another_article():
    text = """Điều 1. Thành phần đoàn:
1. Danh sách:
a) Ông Nguyễn Văn An chịu trách nhiệm tham gia.
Điều 2. Thành phần đoàn khác:
1. Danh sách:
a) Bà Trần Thị Bình chịu trách nhiệm tham gia.
Điều 3. Các cá nhân tại điểm a chịu trách nhiệm.
Nơi nhận:
- Như Điều 3;"""
    mentions, reasons = extract_rule_mentions(pages(text))
    assert all(m.kind == "reference" for m in mentions)
    assert "unsupported_reference" in reasons


@pytest.mark.parametrize("locator", ["điểm a", "điểm a khoản 1"])
def test_missing_relative_point_does_not_select_unique_point_in_another_article(locator):
    text = f"""Điều 1. Thành phần đoàn:
1. Danh sách:
a) Ông Nguyễn Văn An chịu trách nhiệm tham gia.
Điều 3. Các cá nhân tại {locator} chịu trách nhiệm.
Nơi nhận:
- Như Điều 3;"""
    mentions, reasons = extract_rule_mentions(pages(text))
    assert all(m.kind == "reference" for m in mentions)
    assert "unsupported_reference" in reasons


def test_model_member_is_grounded_in_actual_3654_reference_chain(settings):
    source = json.loads((Path(__file__).parent / "fixtures/3654_vietocr_pages.json").read_text(encoding="utf-8"))
    provider = FakeProvider({"mentions": [
        {"raw": "Điều 1", "kind": "unit", "evidence": [{"page": 2, "section": "noi_nhan", "raw": "Như Điều 3"}]},
        {"raw": "Hoàng Quý Thạch", "kind": "person", "references": ["Như Điều 3"],
         "evidence": [{"page": 4, "section": "body_reference", "raw": "Ống Hoàng Quý Thạch"}]},
    ], "status": "complete", "review_reasons": [], "ocr_pages": []})
    with patch("ai_document_sender.extraction._read_pages", return_value=source):
        result = asyncio.run(extract_document(Path("unused.pdf"), provider, DocumentMetadata(document_id="3654"), settings))
    assert not any(m.raw == "Điều 1" for m in result.mentions)
    assert "ungrounded_model_mention" not in result.review_reasons
    assert len([m for m in result.mentions if m.kind == "person"]) == 26
    person = next(m for m in result.mentions if m.raw == "Hoàng Quý Thạch")
    assert person.references == ["Như Điều 3", "Điều 3", "Điều 1", "Danh sách kèm theo"]


@pytest.mark.parametrize("target, body", [
    ("Điều 1", "Điều 1. Thành phần đoàn:\nKhoản 1. Ông Nguyễn Văn An chịu trách nhiệm tham gia."),
    ("Mục II", "Mục II. Thành phần đoàn:\nĐiều 1. Thành phần chính thức:\nKhoản 1. Ông Nguyễn Văn An chịu trách nhiệm tham gia.\nMục III. Thi hành:"),
])
def test_parent_reference_retains_recipients_in_explicit_child_sections(target, body):
    text = f"""{body}
Điều 3. Các cá nhân tại {target} chịu trách nhiệm thi hành.
Nơi nhận:
- Như Điều 3;"""
    mentions, reasons = extract_rule_mentions(pages(text))
    assert {m.raw for m in mentions} == {"Nguyễn Văn An"}
    assert not reasons


def test_parent_traversal_keeps_each_child_reference_in_its_own_scope():
    text = """Điều 1. Thành phần đoàn:
Khoản 1. Các cá nhân tại điểm a cùng tham gia đoàn.
a) Ông Nguyễn Văn An chịu trách nhiệm tham gia.
Khoản 2. Các cá nhân tại điểm a cùng tham gia đoàn.
a) Bà Trần Thị Bình chịu trách nhiệm phục vụ.
Khoản 3. Thời gian công tác là hai ngày.
Điều 3. Các cá nhân tại Điều 1 chịu trách nhiệm thi hành.
Nơi nhận:
- Như Điều 3;"""
    mentions, reasons = extract_rule_mentions(pages(text))
    assert {m.raw for m in mentions} == {"Nguyễn Văn An", "Trần Thị Bình"}
    assert not reasons
