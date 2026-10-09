"""Evaluate reviewed extraction and resolution gold without provider calls.

Historical display strings, truncated lists and unreviewed annotations are not gold.
Missing/failed predictions stay in the denominator of reviewed cases.
"""
import argparse
from collections import Counter
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


def evaluate(gold, predictions):
    ids = [str(item["document_id"]) for item in gold]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate document_id in gold")
    prediction_ids = [str(item.get("document_id", (item.get("result") or {}).get("document_id", ""))) for item in predictions]
    if any(not item for item in prediction_ids) or len(prediction_ids) != len(set(prediction_ids)):
        raise ValueError("Missing or duplicate document_id in predictions")
    prediction_by_id = dict(zip(prediction_ids, predictions))
    counts, extraction, resolution, exclusion_reasons = Counter(), Counter(), Counter(), Counter()
    rows, timings, eligible_mentions, annotated_mentions = [], [], 0, 0
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
        version_mismatch = any(document.get(field) and document[field] != prediction.get(field) for field in ("registry_version", "alias_policy_version")) if raw_prediction and not failed else False
        counts["prediction_version_mismatches"] += version_mismatch
        valid_prediction = terminal_prediction and not version_mismatch
        reasons = prediction.get("review_reasons", [])
        error_code = ((raw_prediction or {}).get("error") or {}).get("code", "")
        counts["provider_failure_documents"] += bool(error_code.startswith("provider_") or any(str(reason).startswith("provider_") for reason in reasons))
        review = not valid_prediction or bool(prediction.get("needs_review") or prediction.get("unresolved") or reasons)
        expected_mentions = {_mention_key(mention) for mention in document.get("mentions", []) if _mention_key(mention)}
        actual_mentions = {_mention_key(mention) for mention in prediction.get("mentions", []) if _mention_key(mention)} if terminal_prediction else set()
        expected_ids = {str(item) for item in document.get("recipient_ids", [])}
        actual_ids = {str(item["recipient_id"]) for item in prediction.get("people", [])+prediction.get("units", []) if item.get("recipient_id")} if valid_prediction else set()
        extraction_complete = document.get("extraction_annotation_complete", True) and "mentions" in document
        resolution_complete = document.get("resolution_annotation_complete", True) and "recipient_ids" in document
        if extraction_complete:
            _score(extraction, expected_mentions, actual_mentions, terminal_prediction)
            counts["extraction_scored_documents"] += 1
        if resolution_complete:
            _score(resolution, expected_ids, actual_ids, valid_prediction)
            counts["resolution_scored_documents"] += 1
            resolution["review_documents"] += review
            resolution["unresolved_mentions"] += len(prediction.get("unresolved", []))
            resolution["predicted_mentions"] += len(prediction.get("mentions", []))
        counts["excluded_missing_extraction_annotation"] += not extraction_complete
        counts["excluded_missing_resolution_annotation"] += not resolution_complete
        if "registry_eligible_mention_count" in document:
            eligible_mentions += document["registry_eligible_mention_count"]
            annotated_mentions += document.get("recipient_mention_count", len(document.get("mentions", [])))
        timing = prediction.get("timings_ms", {}).get("total")
        if isinstance(timing, (int, float)):
            timings.append(timing)
        rows.append({"document_id": doc_id, "scored": True, "review": review, "version_mismatch": version_mismatch,
                     "extraction_exact": terminal_prediction and expected_mentions == actual_mentions if extraction_complete else None,
                     "resolution_exact": valid_prediction and expected_ids == actual_ids if resolution_complete else None,
                     "missing_ids": sorted(expected_ids-actual_ids), "extra_ids": sorted(actual_ids-expected_ids)})
    counts["unmatched_prediction_documents"] = len(set(prediction_ids)-set(ids))
    # Stable report shape, including zero counts; no difficult-case deletion.
    for key in ("gold_documents", "excluded_incomplete_documents", "truncated_label_documents", "missing_predictions", "failed_predictions", "nonterminal_predictions", "invalid_completed_predictions", "provider_failure_documents", "prediction_version_mismatches", "extraction_scored_documents", "resolution_scored_documents"):
        counts.setdefault(key, 0)
    extraction_metrics, resolution_metrics = _metrics(extraction), _metrics(resolution)
    resolution_metrics.update(review_document_rate=resolution["review_documents"]/resolution["documents"] if resolution["documents"] else None,
                              unresolved_mention_rate=resolution["unresolved_mentions"]/resolution["predicted_mentions"] if resolution["predicted_mentions"] else None,
                              registry_coverage=eligible_mentions/annotated_mentions if annotated_mentions else None)
    return {"evaluation_version": "outgoing-eval-v1", "prediction_stage": "backend_before_manual_edits", "counts": dict(counts),
            "exclusion_reasons": dict(exclusion_reasons), "extraction": extraction_metrics, "resolution": resolution_metrics,
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
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = evaluate(_read(args.gold), _read(args.predictions))
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text+"\n", encoding="utf-8")
    else:
        print(text)


if __name__ == "__main__":
    main()
