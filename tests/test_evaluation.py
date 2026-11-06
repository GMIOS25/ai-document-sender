import pytest

from tools.evaluate_outgoing import evaluate, manifest_checksum
from tools.lock_recipient_holdout import lock_holdout


def test_separate_extraction_and_registry_id_metrics():
    gold = [{"document_id": "1", "annotation_complete": True, "mentions": ["Chủ tịch UBND tỉnh", "Sở Y tế"], "recipient_ids": ["person-1", "unit-1"]}]
    predictions = [{"document_id": "1", "mentions": [{"raw": "Chủ tịch UBND tỉnh"}, {"raw": "Sở Y tế"}], "people": [{"recipient_id": "person-1"}], "units": [], "unresolved": [{"raw": "Sở Y tế"}], "needs_review": True}]
    report = evaluate(gold, predictions)
    assert report["extraction"]["recall"] == 1
    assert report["resolution"]["recall"] == 0.5
    assert report["resolution"]["exact_set_match"] == 0
    assert report["resolution"]["review_document_rate"] == 1


def test_missing_predictions_count_as_errors_not_excluded_hard_cases():
    report = evaluate([{"document_id": "1", "annotation_complete": True, "mentions": ["CVP"], "recipient_ids": ["person-1"]}], [])
    assert report["resolution"]["recall"] == 0
    assert report["counts"]["missing_predictions"] == 1
    assert report["counts"]["resolution_scored_documents"] == 1


def test_truncated_historical_labels_and_incomplete_annotations_are_explicit():
    gold = [{"document_id": "1", "annotation_complete": False, "mentions": [], "recipient_ids": []}, {"document_id": "2", "annotation_complete": True, "historical_labels": "Đơn vị nhận: Xã Đak P...", "mentions": [], "recipient_ids": ["id-1"]}]
    report = evaluate(gold, [])
    assert report["counts"]["excluded_incomplete_documents"] == 2
    assert report["counts"]["truncated_label_documents"] == 1
    assert report["resolution"]["exact_set_match"] is None


def test_duplicates_do_not_inflate_precision_and_provider_failures_remain_denominator():
    gold = [{"document_id": "1", "annotation_complete": True, "mentions": ["CVP"], "recipient_ids": ["id-1"]}, {"document_id": "2", "annotation_complete": True, "mentions": ["CVP"], "recipient_ids": ["id-2"]}]
    predicted = [{"document_id": "1", "mentions": [{"raw": "CVP"}], "people": [{"recipient_id": "id-1"}, {"recipient_id": "id-1"}], "units": []}, {"document_id": "2", "status": "failed", "error": {"code": "provider_timeout"}}]
    report = evaluate(gold, predicted)
    assert report["resolution"]["exact_set_match"] == 0.5
    assert report["counts"]["failed_predictions"] == 1
    assert report["resolution"]["exact_set_match_95ci"][0] < 0.5


def test_nonterminal_or_empty_completed_job_cannot_pass_empty_gold():
    gold = [{"document_id": str(i), "annotation_complete": True, "mentions": [], "recipient_ids": []} for i in range(4)]
    predicted = [{"document_id": str(i), "status": status, "result": None} for i, status in enumerate(["queued", "extracting", "resolving", "completed"])]
    report = evaluate(gold, predicted)
    assert report["extraction"]["scored_documents"] == 4
    assert report["extraction"]["exact_set_match"] == 0
    assert report["resolution"]["exact_set_match"] == 0
    assert report["counts"]["nonterminal_predictions"] == 3
    assert report["counts"]["invalid_completed_predictions"] == 1


def test_registry_mismatch_invalidates_resolution_but_not_raw_extraction():
    gold = [{"document_id": "1", "annotation_complete": True, "mentions": ["CVP"], "recipient_ids": ["id-1"], "registry_version": "new"}]
    predicted = [{"status": "completed", "result": {"document_id": "1", "registry_version": "old", "mentions": [{"raw": "CVP"}], "people": [{"recipient_id": "id-1"}], "units": []}}]
    report = evaluate(gold, predicted)
    assert report["extraction"]["exact_set_match"] == 1
    assert report["resolution"]["exact_set_match"] == 0
    assert report["counts"]["prediction_version_mismatches"] == 1


def test_pinned_parent_projection_and_unknown_membership():
    snapshot = {
        "registry_version": "r", "alias_policy_version": "p",
        "recipients": {
            "parent": {"recipient_type": "INTERNAL_DEPT", "sphere": "internal"},
            "unknown": {"recipient_type": "INTERNAL_DEPT", "sphere": "internal"},
            "one": {"recipient_type": "INTERNAL_PERSON", "sphere": "internal"},
            "two": {"recipient_type": "INTERNAL_PERSON", "sphere": "internal"},
        },
        "recipient_expansions": {"parent": ["one", "two"]},
    }
    gold = [{"document_id": "1", "annotation_complete": True, "recipient_ids": ["one", "two"]}]
    result = {"document_id": "1", "registry_version": "r", "alias_policy_version": "p",
              "units": [{"recipient_id": "parent", **snapshot["recipients"]["parent"]}],
              "people": [{"recipient_id": "one", **snapshot["recipients"]["one"]}]}
    assert evaluate(gold, [result], snapshot)["resolution"]["exact_set_match"] == 1
    result["units"].append({"recipient_id": "unknown", **snapshot["recipients"]["unknown"]})
    report = evaluate(gold, [result], snapshot)
    assert report["resolution"]["exact_set_match"] == 0
    assert report["documents"][0]["projection_error"] == "unverified_membership"
    result["units"].pop()
    result["people"][0]["sphere"] = "ext_province_comm"
    report = evaluate(gold, [result], snapshot)
    assert report["resolution"]["exact_set_match"] == 0
    assert report["documents"][0]["projection_error"] == "snapshot_identity_mismatch"


def test_holdout_requires_reviewed_annotations_and_excludes_development_documents():
    snapshot = {"registry_version": "r", "alias_policy_version": "p",
                "recipients": {"one": {"recipient_type": "INTERNAL_PERSON"}}}
    old = {"document_id": "old", "input_sha256": "a" * 64, "published_date": "2026-10-26",
           "template_family": "family A"}
    new = {"document_id": "new", "input_sha256": "b" * 64, "published_date": "2026-11-06",
           "template_family": "family B", "annotation_complete": True, "gold_reviewed": True,
           "pdf_evidence_source": "PDF page 1", "recipient_evidence_source": "reviewed iDesk history",
           "mentions": ["name"], "pdf_recipient_ids": ["one"], "recipient_ids": ["one"]}
    manifest = lock_holdout([new], [old], snapshot, "processing", minimum=1)
    assert manifest["manifest_sha256"] == manifest_checksum(manifest)
    with pytest.raises(ValueError, match="reviewed labels"):
        lock_holdout([{**new, "resolution_annotation_complete": False}], [old], snapshot, "processing", minimum=1)
    with pytest.raises(ValueError, match="development document"):
        lock_holdout([{**new, "input_sha256": old["input_sha256"]}], [old], snapshot, "processing", minimum=1)
