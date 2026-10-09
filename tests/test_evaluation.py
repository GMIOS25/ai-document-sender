from tools.evaluate_outgoing import evaluate


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
