"""Evaluate reviewed extraction and resolution gold without provider calls.

Historical display strings, truncated lists and unreviewed annotations are not gold.
Missing/failed predictions stay in the denominator of reviewed cases.
"""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re
import statistics
import unicodedata


def _mention_key(mention):
    value = mention if isinstance(mention, str) else mention.get("raw", "")
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", value)).strip(" ;.").casefold()


def _wilson(successes, total):
    if not total:
        return None
    z = 1.959963984540054
    p = successes / total
    denom = 1 + z*z/total
    center = (p+z*z/(2*total))/denom
    radius = z*math.sqrt(p*(1-p)/total+z*z/(4*total*total))/denom
    return [max(0, center-radius), min(1, center+radius)]


def _metrics(counters):
    tp, fp, fn, n = (counters[key] for key in ("tp", "fp", "fn", "documents"))
    exact = counters["exact_documents"]
    return {"scored_documents": n, "exact_set_match": exact/n if n else None,
            "exact_set_match_95ci": _wilson(exact, n), "precision": tp/(tp+fp) if tp+fp else None,
            "recall": tp/(tp+fn) if tp+fn else None, "true_positive": tp, "false_positive": fp, "false_negative": fn}


def _score(counters, expected, actual, valid_prediction):
    counters.update(documents=1, tp=len(expected & actual), fp=len(actual-expected), fn=len(expected-actual), exact_documents=int(valid_prediction and expected == actual))


def project_ids(ids, snapshot):
    if snapshot is None:
        return set(ids), None
    recipients = snapshot["recipients"]
    projected, reason = set(), None
    for rid in ids:
        identity = recipients.get(rid)
        if identity is None:
            reason = "unknown_snapshot_identity"
        elif identity["recipient_type"] in {"INTERNAL_DEPT", "INTERNAL_UNIT", "INTERNAL_GROUP"}:
            members = snapshot.get("recipient_expansions", {}).get(rid)
            if not members or any(recipients.get(member, {}).get("recipient_type") != "INTERNAL_PERSON" for member in members):
                reason = "unverified_membership"
            else:
                projected.update(members)
        else:
            projected.add(rid)
    return projected, reason


def _verify_selection_plan(prediction, snapshot, ids):
    units = {(r["sphere"], r.get("code")) for rid, r in snapshot["recipients"].items() if rid in ids}
    groups = {(g["sphere"], g["id"]): g for g in snapshot.get("unit_groups", []) if g["complete"]}
    for selection in prediction.get("selection_plan", []):
        key = selection["sphere"], selection["group_id"]
        codes = set(selection["member_codes"])
        if (selection["registry_version"] != snapshot["registry_version"] or key not in groups
                or len(codes) != len(selection["member_codes"])
                or codes != set(groups[key]["member_codes"]) or any((key[0], code) not in units for code in codes)):
            return "unverified_selection_plan"
    return None


def manifest_checksum(manifest):
    body = {key: value for key, value in manifest.items() if key != "manifest_sha256"}
    return hashlib.sha256(json.dumps(body, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def evaluate(gold, predictions, snapshot=None, processing_version=None):
    ids = [str(item["document_id"]) for item in gold]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate document_id in gold")
    prediction_ids = [str(item.get("document_id", (item.get("result") or {}).get("document_id", ""))) for item in predictions]
    if any(not item for item in prediction_ids) or len(prediction_ids) != len(set(prediction_ids)):
        raise ValueError("Missing or duplicate document_id in predictions")
    prediction_by_id = dict(zip(prediction_ids, predictions))
    counts, extraction, resolution, exclusion_reasons = Counter(), Counter(), Counter(), Counter()
    rows, timings, eligible_mentions, annotated_mentions = [], [], 0, 0
    pdf_resolution, macro_recall = Counter(), []
    by_sphere = {s: Counter() for s in ("internal", "int_province_comm", "ext_province_comm")} if snapshot else {}
    for document in gold:
        doc_id = str(document["document_id"])
        counts["gold_documents"] += 1
        historical = document.get("historical_labels", "")
        truncated = bool(re.search(r"\.\.\.|…", str(historical)))
        counts["truncated_label_documents"] += truncated
        incomplete = not document.get("annotation_complete", False) or (truncated and not document.get("gold_reviewed", False)) or bool(document.get("exclude_reason"))
        if incomplete:
            counts["excluded_incomplete_documents"] += 1
            reason = document.get("exclude_reason") or ("truncated_historical_labels" if truncated else "incomplete_annotation")
            exclusion_reasons[reason] += 1
            rows.append({"document_id": doc_id, "scored": False, "reason": reason})
            continue
        raw_prediction = prediction_by_id.get(doc_id)
        counts["missing_predictions"] += raw_prediction is None
        prediction = (raw_prediction.get("result") or raw_prediction) if raw_prediction else {}
        failed = bool(raw_prediction and raw_prediction.get("status") == "failed")
        counts["failed_predictions"] += failed
        envelope = bool(raw_prediction and "status" in raw_prediction)
        nonterminal = bool(envelope and raw_prediction["status"] in {"queued", "extracting", "resolving"})
        invalid_completed = bool(envelope and raw_prediction["status"] == "completed" and not isinstance(raw_prediction.get("result"), dict))
        counts["nonterminal_predictions"] += nonterminal
        counts["invalid_completed_predictions"] += invalid_completed
        terminal_prediction = raw_prediction is not None and (not envelope or (raw_prediction["status"] == "completed" and isinstance(raw_prediction.get("result"), dict)))
        if terminal_prediction and document.get("input_sha256") and prediction.get("input_sha256") != document["input_sha256"]:
            counts["prediction_input_mismatches"] += 1
            terminal_prediction = False
        stamped_version = (raw_prediction or {}).get("processing_version") or prediction.get("audit", {}).get("processing_version")
        if raw_prediction and processing_version and stamped_version != processing_version:
            counts["prediction_processing_version_mismatches"] += 1
            terminal_prediction = False
        version_mismatch = any(document.get(field) and document[field] != prediction.get(field) for field in ("registry_version", "alias_policy_version")) if raw_prediction and not failed else False
        if snapshot is not None:
            for field in ("registry_version", "alias_policy_version"):
                if document.get(field, snapshot[field]) != snapshot[field]:
                    raise ValueError(f"Gold snapshot mismatch for {doc_id}")
                if terminal_prediction and prediction.get(field) != snapshot[field]:
                    version_mismatch = True
        counts["prediction_version_mismatches"] += version_mismatch
        valid_prediction = terminal_prediction and not version_mismatch
        reasons = prediction.get("review_reasons", [])
        error_code = ((raw_prediction or {}).get("error") or {}).get("code", "")
        counts["provider_failure_documents"] += bool(error_code.startswith("provider_") or any(str(reason).startswith("provider_") for reason in reasons))
        review = not valid_prediction or bool(prediction.get("needs_review") or prediction.get("unresolved") or reasons)
        expected_mentions = {_mention_key(mention) for mention in document.get("mentions", []) if _mention_key(mention)}
        actual_mentions = {_mention_key(mention) for mention in prediction.get("mentions", []) if _mention_key(mention)} if terminal_prediction else set()
        expected_ids, gold_error = project_ids([str(item) for item in document.get("recipient_ids", [])], snapshot)
        if gold_error:
            raise ValueError(f"Gold identity projection failed for {doc_id}: {gold_error}")
        selected = prediction.get("people", []) + prediction.get("units", []) if valid_prediction else []
        verified = selected
        identity_mismatch = False
        if snapshot:
            verified = []
            for r in selected:
                expected = snapshot["recipients"].get(r.get("recipient_id"), {})
                if any(field in expected and r.get(field) != expected[field]
                       for field in ("source_id", "recipient_type", "sphere", "code")):
                    identity_mismatch = True
                else:
                    verified.append(r)
        actual_ids, projection_error = project_ids([str(r["recipient_id"]) for r in verified if r.get("recipient_id")], snapshot)
        if identity_mismatch:
            projection_error = "snapshot_identity_mismatch"
        if snapshot and valid_prediction and not projection_error:
            projection_error = _verify_selection_plan(prediction, snapshot, actual_ids)
        if projection_error:
            counts["unverified_prediction_membership"] += 1
            review, valid_prediction = True, False
        extraction_complete = document.get("extraction_annotation_complete", True) and "mentions" in document
        resolution_complete = document.get("resolution_annotation_complete", True) and "recipient_ids" in document
        if extraction_complete:
            _score(extraction, expected_mentions, actual_mentions, terminal_prediction)
            counts["extraction_scored_documents"] += 1
        if resolution_complete:
            _score(resolution, expected_ids, actual_ids, valid_prediction)
            macro_recall.append(len(expected_ids & actual_ids) / len(expected_ids) if expected_ids else int(valid_prediction and not actual_ids))
            for sphere, counters in by_sphere.items():
                identity = snapshot["recipients"]
                _score(counters, {rid for rid in expected_ids if identity[rid]["sphere"] == sphere},
                       {rid for rid in actual_ids if identity[rid]["sphere"] == sphere}, valid_prediction)
            counts["resolution_scored_documents"] += 1
            resolution["review_documents"] += review
            resolution["unresolved_mentions"] += len(prediction.get("unresolved", []))
            resolution["predicted_mentions"] += len(prediction.get("mentions", []))
        if "pdf_recipient_ids" in document:
            expected_pdf, error = project_ids(document["pdf_recipient_ids"], snapshot)
            if error:
                raise ValueError(f"Gold PDF identity projection failed for {doc_id}: {error}")
            publication = prediction.get("audit", {}).get("publication", {})
            policy_version = publication.get("policy_version")
            policy_ids = set(publication.get("recipients", []))
            actual_pdf, error = project_ids([r["recipient_id"] for r in verified if r.get("recipient_id")
                and not (policy_version and r["recipient_id"] in policy_ids and r.get("match_method") == policy_version)], snapshot)
            _score(pdf_resolution, expected_pdf, actual_pdf, terminal_prediction and not version_mismatch and not error and not identity_mismatch)
        counts["excluded_missing_extraction_annotation"] += not extraction_complete
        counts["excluded_missing_resolution_annotation"] += not resolution_complete
        if "registry_eligible_mention_count" in document:
            eligible_mentions += document["registry_eligible_mention_count"]
            annotated_mentions += document.get("recipient_mention_count", len(document.get("mentions", [])))
        timing = prediction.get("timings_ms", {}).get("total")
        if isinstance(timing, (int, float)):
            timings.append(timing)
        rows.append({"document_id": doc_id, "scored": True, "review": review, "version_mismatch": version_mismatch,
                     "projection_error": projection_error,
                     "extraction_exact": terminal_prediction and expected_mentions == actual_mentions if extraction_complete else None,
                     "resolution_exact": valid_prediction and expected_ids == actual_ids if resolution_complete else None,
                     "missing_ids": sorted(expected_ids-actual_ids), "extra_ids": sorted(actual_ids-expected_ids)})
    counts["unmatched_prediction_documents"] = len(set(prediction_ids)-set(ids))
    # Stable report shape, including zero counts; no difficult-case deletion.
    for key in ("gold_documents", "excluded_incomplete_documents", "truncated_label_documents", "missing_predictions", "failed_predictions", "nonterminal_predictions", "invalid_completed_predictions", "provider_failure_documents", "prediction_version_mismatches", "extraction_scored_documents", "resolution_scored_documents"):
        counts.setdefault(key, 0)
    extraction_metrics, resolution_metrics = _metrics(extraction), _metrics(resolution)
    resolution_metrics.update(review_document_rate=resolution["review_documents"]/resolution["documents"] if resolution["documents"] else None,
                              macro_recall=statistics.mean(macro_recall) if macro_recall else None,
                              unresolved_mention_rate=resolution["unresolved_mentions"]/resolution["predicted_mentions"] if resolution["predicted_mentions"] else None,
                              registry_coverage=eligible_mentions/annotated_mentions if annotated_mentions else None)
    return {"evaluation_version": "outgoing-eval-v1", "prediction_stage": "backend_before_manual_edits", "counts": dict(counts),
            "exclusion_reasons": dict(exclusion_reasons), "extraction": extraction_metrics, "resolution": resolution_metrics,
            "pdf_resolution": _metrics(pdf_resolution), "resolution_by_sphere": {s: _metrics(c) for s, c in by_sphere.items()},
            "latency_ms": {"median": statistics.median(timings) if timings else None, "maximum": max(timings) if timings else None},
            "quality_note": "Metrics describe this reviewed dataset only. Production quality requires a locked holdout with fixed registry/policy; no 95-99% claim follows from deterministic fixtures.", "documents": rows}


def _read(path):
    text = Path(path).read_text(encoding="utf-8-sig")
    if Path(path).suffix == ".jsonl":
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    value = json.loads(text)
    return value["documents"] if isinstance(value, dict) else value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold", type=Path, required=True)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--snapshot", type=Path, help="Pinned registry snapshot with recipient expansions")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    snapshot = json.loads(args.snapshot.read_text(encoding="utf-8-sig")) if args.snapshot else None
    raw_gold = json.loads(args.gold.read_text(encoding="utf-8-sig")) if args.gold.suffix != ".jsonl" else None
    locked = isinstance(raw_gold, dict) and raw_gold.get("format") == "vpub-holdout-v1"
    version = None
    if locked:
        if (not snapshot or raw_gold.get("manifest_sha256") != manifest_checksum(raw_gold)
                or raw_gold.get("snapshot_sha256") != manifest_checksum(snapshot)):
            parser.error("A locked holdout requires an intact manifest and the pinned --snapshot.")
        if any(raw_gold.get(field) != snapshot.get(field) for field in ("registry_version", "alias_policy_version")):
            parser.error("Holdout and snapshot versions differ.")
        version = raw_gold.get("processing_version")
        if not version:
            parser.error("The locked holdout must pin a processing version.")
    report = evaluate(raw_gold["documents"] if locked else _read(args.gold), _read(args.predictions), snapshot, version)
    if locked:
        scores = report["resolution"]
        eligible = (scores["scored_documents"] == len(raw_gold["documents"]) >= 500
                    and not any(report["counts"].get(key) for key in ("prediction_version_mismatches",
                                "prediction_processing_version_mismatches", "prediction_input_mismatches")))
        report["acceptance"] = {"manifest_sha256": raw_gold["manifest_sha256"], "processing_version": version,
                                "eligible": eligible, "meets_95": eligible and scores["exact_set_match"] >= .95,
                                "meets_99": eligible and scores["exact_set_match"] >= .99}
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text+"\n", encoding="utf-8")
    else:
        print(text)


if __name__ == "__main__":
    main()
