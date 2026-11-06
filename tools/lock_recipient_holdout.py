"""Validate independently reviewed VPUB labels and lock a reproducible ID benchmark."""
import argparse
from datetime import date
import json
from pathlib import Path
import re

if __package__:
    from .evaluate_outgoing import _read, manifest_checksum, project_ids
else:
    from evaluate_outgoing import _read, manifest_checksum, project_ids


def lock_holdout(reviewed, development, snapshot, processing_version, minimum=500):
    if minimum < 1 or not development or not processing_version:
        raise ValueError("A positive sample size, development manifest and processing version are required")
    if len(reviewed) < minimum:
        raise ValueError(f"Need at least {minimum} reviewed documents, got {len(reviewed)}")
    dev_ids = {str(row["document_id"]) for row in development}
    dev_hashes = {row["input_sha256"] for row in development}
    dev_templates = {row["template_family"] for row in development}
    newest_development = max(date.fromisoformat(row["published_date"]) for row in development)
    ids, hashes, documents = set(), set(), []
    for source in reviewed:
        row = dict(source)
        doc_id = str(row["document_id"])
        pdf_hash = row["input_sha256"]
        if not re.fullmatch("[a-f0-9]{64}", pdf_hash):
            raise ValueError(f"Invalid PDF SHA-256 for {doc_id}")
        if not doc_id or doc_id in ids | dev_ids or pdf_hash in hashes | dev_hashes:
            raise ValueError(f"Duplicate or development document: {doc_id}")
        family = row.get("template_family")
        if not family or family in dev_templates or date.fromisoformat(row["published_date"]) <= newest_development:
            raise ValueError(f"Template overlap or non-new publication date: {doc_id}")
        if (row.get("annotation_complete") is not True or row.get("gold_reviewed") is not True
                or row.get("extraction_annotation_complete", True) is not True
                or row.get("resolution_annotation_complete", True) is not True
                or row.get("exclude_reason") or not row.get("pdf_evidence_source") or not row.get("recipient_evidence_source")):
            raise ValueError(f"Missing independent reviewed labels for {doc_id}")
        if any(not isinstance(row.get(field), list) for field in ("mentions", "pdf_recipient_ids", "recipient_ids")):
            raise ValueError(f"Missing extraction or ID annotation for {doc_id}")
        for field in ("recipient_ids", "pdf_recipient_ids"):
            if project_ids(row[field], snapshot)[1]:
                raise ValueError(f"Unverified {field} for {doc_id}")
        for field in ("registry_version", "alias_policy_version"):
            if row.get(field, snapshot[field]) != snapshot[field]:
                raise ValueError(f"Snapshot mismatch for {doc_id}")
            row[field] = snapshot[field]
        ids.add(doc_id)
        hashes.add(pdf_hash)
        documents.append(row)
    manifest = {"format": "vpub-holdout-v1", "documents": documents,
                "processing_version": processing_version,
                "snapshot_sha256": manifest_checksum(snapshot),
                "registry_version": snapshot["registry_version"], "alias_policy_version": snapshot["alias_policy_version"]}
    manifest["manifest_sha256"] = manifest_checksum(manifest)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reviewed", type=Path, required=True)
    parser.add_argument("--development", type=Path, required=True, help="All development/validation documents with IDs, hashes, dates and template families")
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--processing-version", required=True)
    parser.add_argument("--minimum", type=int, default=500, help="Smaller values create a pilot only")
    args = parser.parse_args()
    manifest = lock_holdout(_read(args.reviewed), _read(args.development),
                            json.loads(args.snapshot.read_text(encoding="utf-8-sig")), args.processing_version, args.minimum)
    with args.output.open("x", encoding="utf-8") as file:
        json.dump(manifest, file, ensure_ascii=False, indent=2)
    print(f"Locked {len(manifest['documents'])} reviewed documents: {manifest['manifest_sha256']}")


if __name__ == "__main__":
    main()
