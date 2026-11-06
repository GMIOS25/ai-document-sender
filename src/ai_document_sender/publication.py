"""VPUB publication recipients with provenance distinct from PDF evidence."""
from datetime import date

from .contracts import FieldAssignment
from .registry import normalize


VERSION = "vpub-publication-v1"
START = date(2026, 10, 17)
PVHCC_CODE = "H21.21.04"
PVHCC_NAMES = {
    "trung tam phuc vu hanh chinh cong", "trung tam phuc vu hanh chinh cong tinh",
    "trung tam phuc vu hanh chinh cong tinh gia lai", "trung tam pvhcc", "trung tam pvhcc tinh",
    "ttpvhcc", "pvhcc kstt",
}


def explicit_service_center(mention, registry):
    name = normalize(mention.raw).strip(".")
    grounded_archive = name == "pvhcc" and any(
        e.section == "luu" and "pvhcc kstt" in normalize(e.raw) for e in mention.evidence)
    if (getattr(registry, "tenant_id", None) != "vpub" or mention.kind == "reference"
            or (name not in PVHCC_NAMES and not grounded_archive)
            or not any(e.section in {"kinh_gui", "noi_nhan", "luu"} for e in mention.evidence)):
        return None
    candidates = [r for r in registry.exact_code(PVHCC_CODE) if r.sphere == "int_province_comm"]
    return candidates if len(candidates) == 1 else []


def apply_publication_policy(result, registry, metadata):
    context = metadata.publication
    if (getattr(registry, "tenant_id", None) != "vpub" or context is None
            or context.date < START or not context.external):
        return
    audit = {"policy_version": VERSION, "source": context.mode, "date": context.date.isoformat(),
             "external": context.external, "recipients": [], "missing": []}
    result.audit["publication"] = audit
    for code, sphere, kind, field, recipients in (
        ("tct@vpub.gialai.gov.vn", "internal", "INTERNAL_PERSON", "responsible", result.people),
        (PVHCC_CODE, "int_province_comm", "INT_PROVINCE_UNIT", "inside_unit", result.units),
    ):
        matches = [r for r in registry.exact_code(code) if r.sphere == sphere and r.recipient_type == kind]
        if len(matches) != 1:
            audit["missing"].append({"code": code, "sphere": sphere, "matches": len(matches)})
            continue
        recipient = matches[0]
        existing = next((r for r in recipients if r.recipient_id == recipient.recipient_id), None)
        if existing:
            recipients.remove(existing)
        recipients.insert(0, existing or recipient.model_copy(update={"match_method": VERSION}, deep=True))
        result.field_suggestions.append(FieldAssignment(recipient_id=recipient.recipient_id, field=field))
        audit["recipients"].append(recipient.recipient_id)
    if audit["missing"]:
        result.review_reasons.append("publication_policy_identity_unverified")
