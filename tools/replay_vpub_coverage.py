"""Replay archived extraction locally and compare recipient coverage by historical label."""
import argparse
import asyncio
from collections import Counter
from dataclasses import replace
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import unicodedata

from ai_document_sender.config import Settings
from ai_document_sender.contracts import DocumentMetadata, Extraction, PublicationContext
from ai_document_sender.registry import Registry
from ai_document_sender.resolver import resolve_mentions
from ai_document_sender.tenants import TenantManager


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def normalize_label(value):
    value = unicodedata.normalize("NFC", value).casefold()
    return re.sub(r"\s+", " ", re.sub(r"[,.;]", " ", value)).strip()


def labels(result, registry, verified_parents):
    keys = set()
    for r in [*result.people, *result.units]:
        members = registry.recipient_expansions.get(r.recipient_id)
        if members:
            keys.update("P:" + normalize_label(registry.by_id[rid].name) for rid in members)
        elif r.recipient_type in {"INTERNAL_DEPT", "INTERNAL_UNIT"} and r.name in verified_parents:
            keys.update("P:" + normalize_label(name) for name in verified_parents[r.name])
        else:
            keys.add(("P:" if r.sphere == "internal" else "U:") + normalize_label(r.name))
    return keys


def score(aggregate, target, predicted):
    aggregate.update(documents=1, target=len(target), predicted=len(predicted), matched=len(target & predicted),
                     missing=len(target - predicted), extra=len(predicted - target), exact=int(target == predicted))


async def replay(args):
    base = Settings.from_env()
    current = Registry(replace(base, lookup_db=TenantManager(base).get_db_path("vpub")))
    current.tenant_id = "vpub"
    archived = Registry.from_snapshot(base, read(args.archive / "registry-snapshot.json"))
    archived.tenant_id = "vpub"
    current_without_groups = Registry.from_snapshot(base, current.snapshot())
    current_without_groups.tenant_id = "vpub"
    current_without_groups.unit_groups = []
    ground = read(args.label_comparison)
    metrics, untruncated, reasons, documents = {}, {}, Counter(), []
    for doc in ground["details"]:
        stt = int(doc["stt"])
        record = read(args.archive / "documents" / f"{stt:04}.json")
        if doc["code"] != record["sign_number"]:
            raise ValueError(f"Document mismatch at {stt}")
        pdf = Path(record["pdf_path"])
        if hashlib.sha256(pdf.read_bytes()).hexdigest() != record["input_sha256"]:
            raise ValueError(f"PDF bytes changed at {stt}")
        source = read(pdf.with_name("view.cpx"))
        native = source["ed"]
        if native["signNumber"] != record["sign_number"]:
            raise ValueError(f"iDesk record mismatch at {stt}")
        book_receivers = (source.get("book") or {}).get("receiver") or ""
        incomplete_history = len(book_receivers) >= 4094 or book_receivers.rstrip().endswith(("...", "…"))
        metadata = DocumentMetadata.model_validate(record["metadata"])
        history = PublicationContext(mode="history",
            date=datetime.strptime(native["publishedDate"], "%b %d, %Y, %I:%M:%S %p").date(),
            external=int(native["externalTransfer"]) != 0)
        extraction = Extraction.model_validate(record["extraction"])
        target = set(doc["target"])
        predictions = {"test_1": set(doc["predicted"])}
        stages = (("same_extraction_old_directory", archived, metadata),
                  ("directory", current_without_groups, metadata),
                  ("native_groups", current, metadata),
                  ("publication", current, metadata.model_copy(update={"publication": history})))
        for label, registry, context in stages:
            result = await resolve_mentions(extraction, registry, context, f"replay-{stt}", record["input_sha256"])
            predictions[label] = labels(result, registry, ground["groupMembers"])
        reasons.update(item.reason for item in result.unresolved)
        for label, predicted in predictions.items():
            score(metrics.setdefault(label, Counter()), target, predicted)
            if not incomplete_history:
                score(untruncated.setdefault(label, Counter()), target, predicted)
        actual = predictions["publication"]
        documents.append({"stt": stt, "document_id": metadata.document_id, "sign_number": doc["code"],
                          "input_sha256": record["input_sha256"], "published_date": history.date.isoformat(),
                          "truncated_or_at_limit": incomplete_history, "matched": len(target & actual),
                          "missing": sorted(target - actual), "extra": sorted(actual - target),
                          "selection_plan": [g.model_dump() for g in result.selection_plan]})
    return {"basis": "historical_labels_archived_extraction_offline", "metrics": metrics,
            "excluding_truncated_or_at_limit": untruncated, "unresolved": reasons, "documents": documents,
            "snapshot_versions": {"archive": archived.registry_version, "current": current.registry_version}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--label-comparison", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = asyncio.run(replay(args))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "documents"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
