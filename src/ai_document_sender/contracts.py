"""Pinned outgoing.v1 models shared by extraction, resolution and HTTP."""
from datetime import date, datetime, timezone
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DocumentMetadata(Model):
    document_id: str = Field(min_length=1, max_length=256)
    sign_number: str | None = None
    subject: str | None = None
    document_date: date | None = None
    issuer: str | None = None
    department_code: str | None = None
    attachment_content_uid: str | None = None
    attachment_name: str | None = None


class Evidence(Model):
    page: int = Field(ge=1)
    section: str
    raw: str = Field(min_length=1)
    bbox: list[float] | None = None
    span: list[int] | None = None


class Mention(Model):
    mention_id: str = Field(min_length=1)
    raw: str = Field(min_length=1)
    kind: str = "unknown"
    evidence: list[Evidence] = Field(default_factory=list)
    references: list[str] = Field(default_factory=list)
    qualifier: str | None = None
    quantifier: str | None = None
    organization_scope: str | None = None
    department_context: str | None = None


class Extraction(Model):
    mentions: list[Mention] = Field(default_factory=list)
    status: Literal["complete", "partial", "failed"] = "partial"
    review_reasons: list[str] = Field(default_factory=list)
    pages: list[dict[str, Any]] = Field(default_factory=list)
    audit: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def unique_mentions(self):
        ids = [m.mention_id for m in self.mentions]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate mention_id")
        return self


RecipientType = Literal["INTERNAL_PERSON", "INTERNAL_DEPT", "INTERNAL_GROUP", "INTERNAL_UNIT", "INT_PROVINCE_UNIT", "EXT_PROVINCE_UNIT"]
Sphere = Literal["internal", "int_province_comm", "ext_province_comm"]


class Recipient(Model):
    recipient_id: str
    source_id: str
    recipient_type: RecipientType
    name: str
    role: str | None = None
    sphere: Sphere
    code: str = ""
    display_name: str = ""
    parent_name: str = ""
    match_method: str = ""
    evidence: list[Evidence] = Field(default_factory=list)
    mention_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def identity_sphere(self):
        expected = ("internal" if self.recipient_type.startswith("INTERNAL_") else
                    "int_province_comm" if self.recipient_type == "INT_PROVINCE_UNIT" else "ext_province_comm")
        if self.sphere != expected:
            raise ValueError("recipient_type and sphere do not match")
        return self


class Unresolved(Model):
    mention_id: str
    raw: str
    kind: str
    evidence: list[Evidence] = Field(default_factory=list)
    reason: str
    candidates: list[Recipient] = Field(default_factory=list)


class Excluded(Model):
    mention_id: str
    raw: str
    evidence: list[Evidence] = Field(default_factory=list)
    reason: str


class OutgoingResult(Model):
    schema_version: Literal["outgoing.v1"] = "outgoing.v1"
    job_id: str
    document_id: str
    input_sha256: str
    registry_version: str
    alias_policy_version: str
    resolution_as_of: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    snapshot_basis: str = "current_directory_snapshot"
    extraction_status: Literal["complete", "partial", "failed"]
    mentions: list[Mention] = Field(default_factory=list)
    people: list[Recipient] = Field(default_factory=list)
    units: list[Recipient] = Field(default_factory=list)
    unresolved: list[Unresolved] = Field(default_factory=list)
    excluded: list[Excluded] = Field(default_factory=list)
    needs_review: bool = False
    review_reasons: list[str] = Field(default_factory=list)
    timings_ms: dict[str, float] = Field(default_factory=dict)
    audit: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def enforce_review(self):
        if self.extraction_status != "complete":
            reason = "extraction_" + self.extraction_status
            if reason not in self.review_reasons:
                self.review_reasons.append(reason)
        if self.extraction_status != "complete" or self.unresolved or self.review_reasons:
            self.needs_review = True
        return self


class FinalRecipient(Model):
    recipient_id: str
    recipient_type: RecipientType
    sphere: Sphere
    code: str = ""


class FieldAssignment(Model):
    recipient_id: str
    field: Literal["responsible", "save", "participants", "follow", "inside_unit", "outside_unit"]


class ReviewDecision(Model):
    mention_id: str
    action: Literal["resolve", "exclude", "accept_missing"]
    note: str = ""
    recipient_ids: list[str] = Field(default_factory=list)


class Feedback(Model):
    registry_version: str
    alias_policy_version: str
    final_recipients: list[FinalRecipient]
    field_assignments: list[FieldAssignment] = Field(default_factory=list)
    review_decisions: list[ReviewDecision] = Field(default_factory=list)
    edits: list[dict[str, Any]] = Field(default_factory=list)
    confirmed: bool


class JobError(Model):
    code: str
    message: str
    retryable: bool = False


class JobEnvelope(Model):
    job_id: str
    status: Literal["queued", "extracting", "resolving", "completed", "failed"]
    result: OutgoingResult | None = None
    error: JobError | None = None


class OrganizationNode(BaseModel):
    # Native fields vary between iDesk directory and search responses.
    model_config = ConfigDict(extra="allow", str_strip_whitespace=True)
    code: str = Field(strict=True, min_length=1, max_length=256)
    name: str = Field(strict=True, min_length=1, max_length=2048)
    sphere: Literal["int_province_comm", "ext_province_comm"]
    uuid: str | None = Field(default=None, max_length=512)
    identifier: str | None = Field(default=None, max_length=512)
    parentIdentifier: str | None = Field(default=None, max_length=512)
    centerCode: str | None = Field(default=None, max_length=512)


class OrganizationBatch(Model):
    source: Literal["directory", "search"]
    elements: list[OrganizationNode] = Field(max_length=10000)
