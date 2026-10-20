"""Resolve only identities supported by text, verified policies and current directory."""
import re
import unicodedata
from time import perf_counter
from .contracts import OutgoingResult, Unresolved, Excluded
from .registry import normalize, words, department_context


VERSION = "recipient-selectable-parent-nodes-v3"


def expand_lexical(raw):
    raw = unicodedata.normalize("NFC", raw)
    raw = re.sub(r"\s+", " ", raw).strip()
    raw = re.sub(r"^(?:Đ\s*/\s*c\.?|Đồng\s+chí|Ông|Bà)\s+", "", raw, flags=re.I)
    raw = re.sub(r"\s*\((?:để\s+)?(?:b/c|báo\s+cáo|biết|thực\s+hiện|phối\s+hợp)\)\s*$", "", raw, flags=re.I)
    raw = re.sub(r"Ủy\s+ban\s+nhân\s+dân", "UBND", raw, flags=re.I)
    expansions = [
        (r"^PCT\b", "Phó Chủ tịch UBND tỉnh"), (r"^CT\s+UBND\s+tỉnh\b", "Chủ tịch UBND tỉnh"),
        (r"^CVP\b", "Chánh Văn phòng UBND tỉnh"), (r"^PCVP\b", "Phó Chánh Văn phòng"),
        (r"^Sở\s+VH\s*[,.-]?\s*TT\s*[&,. -]*\s*DL\b", "Sở Văn hóa Thể thao và Du lịch"),
        (r"^Sở\s+VHTTDL\b", "Sở Văn hóa Thể thao và Du lịch"),
        (r"^Sở\s+NN\s*[&,. -]*\s*MT\b", "Sở Nông nghiệp và Môi trường"),
        (r"^Sở\s+NNMT\b", "Sở Nông nghiệp và Môi trường"), (r"^Sở\s+XD\b", "Sở Xây dựng"),
        (r"^Sở\s+GD\s*[&,. -]*\s*ĐT\b", "Sở Giáo dục và Đào tạo"),
    ]
    for pattern, full in expansions:
        raw = re.sub(pattern, full, raw, flags=re.I)
    # PCT UBND tỉnh must not produce duplicated jurisdiction text.
    return re.sub(r"(UBND tỉnh)\s+UBND tỉnh", r"\1", raw, flags=re.I).strip(" ;:-")


async def resolve_mentions(extraction, registry, metadata, job_id, input_sha256, provider=None):
    started = perf_counter()
    department, department_source = department_context(metadata)
    metadata = metadata.model_copy(update={"department_code": department})
    result = OutgoingResult(job_id=job_id,document_id=metadata.document_id,input_sha256=input_sha256,
        registry_version=registry.registry_version, alias_policy_version=registry.alias_policy_version,
        resolution_as_of=registry.resolution_as_of, extraction_status=extraction.status,
        mentions=extraction.mentions, review_reasons=list(extraction.review_reasons),
        audit={"extraction":extraction.audit,"resolution_context":{"department_code":department,"department_source":department_source}})
    chosen = {}
    for mention in extraction.mentions:
        raw = unicodedata.normalize("NFC", mention.raw).strip(" ;:-")
        combined = raw
        if mention.qualifier and not normalize(raw).startswith(normalize(mention.qualifier)):
            combined = mention.qualifier + " " + raw
        pending = registry.alias(raw, metadata) or registry.alias(combined, metadata)
        if pending is None:
            # Jurisdiction suffixes do not make an unverified portfolio alias safe.
            prefix = re.match(r"^(PVPQT|PVPVX|PCVP\s*XD)\b", combined, re.I)
            if prefix:
                pending = registry.alias(prefix.group(1),metadata)
        query = pending.get("canonical_role") or pending.get("canonical_name") or combined if pending else combined
        query = expand_lexical(query)
        node_candidates = registry.internal_node_candidates(query)
        candidates, reason, method = [], None, ""
        if not mention.evidence:
            reason = "unreadable_region"
        elif pending and pending.get("verification_status") != "verified":
            reason = pending.get("pending_reason", "unverified_business_alias")
            conflicting = {}
            for alias in pending.get("conflicting_aliases",[]):
                if alias.get("canonical_role"):
                    matches=registry.exact_role(alias["canonical_role"])
                elif alias.get("recipient_id"):
                    matches=[registry.by_id[alias["recipient_id"]]] if alias["recipient_id"] in registry.by_id else []
                else:
                    matches=[]
                for item in matches:
                    conflicting[item.recipient_id]=item
            candidates=list(conflicting.values())
            if normalize(raw) == "vt" and not any(e.section == "luu" for e in mention.evidence):
                reason = "ambiguous_abbreviation"
        elif pending and pending.get("action") == "exclude":
            result.excluded.append(Excluded(mention_id=mention.mention_id,raw=mention.raw,evidence=mention.evidence,reason=pending.get("reason","archival_reference")))
            continue
        elif all(e.section == "luu" for e in mention.evidence) and not re.fullmatch(r"[A-Za-z]{1,3}\d{1,3}", raw) and not pending:
            reason = "policy_unknown"
        elif normalize(raw) in {"nhu tren", "nhu kinh gui"} or mention.kind == "reference":
            reason = "unsupported_reference"
        elif not node_candidates and (mention.kind == "group" or mention.quantifier in {"all", "plural"} or normalize(raw).startswith(("cac ", "toan bo ", "lanh dao "))):
            members = registry.group_members(combined)
            if members:
                candidates, method = members, "verified_group_membership"
            else:
                reason = "missing_group_membership"
        else:
            if pending and pending.get("recipient_id"):
                item = registry.by_id.get(pending["recipient_id"])
                candidates = [item] if item else []
                method = "verified_alias"
            elif node_candidates:
                candidates, method = node_candidates, "exact_internal_node"
            elif re.fullmatch(r"[A-Za-z]{1,3}\d{1,3}", raw):
                candidates = registry.staff_code(raw)
                method = "current_staff_code"
            else:
                candidates = registry.exact_code(query)
                method = "exact_code"
                if not candidates:
                    candidates = registry.exact_name(query)
                    method = "exact_name"
                if not candidates:
                    candidates = registry.exact_role(query)
                    method = "exact_unique_role"
                if not candidates:
                    candidates = registry.local_unit_name(query, mention.organization_scope or metadata.issuer)
                    method = "exact_local_unit"
                if not candidates:
                    # Initials after a role prefix must respect that exact role.
                    role, name = None, query
                    for r in registry.by_id.values():
                        if r.role and normalize(query).startswith(normalize(r.role) + " "):
                            role = r.role
                            name = query[len(r.role):].strip(" :,-()")
                            break
                    if not role:
                        suffix=re.match(r"^(.+?)\s*[–—:-]\s*(.+)$",query)
                        if suffix:
                            expanded_role=expand_lexical(suffix.group(2))
                            if registry.exact_role(expanded_role):
                                role,name=expanded_role,suffix.group(1).strip()
                    candidates = registry.initials(name, role)
                    method = "exact_initials"
                    if not candidates and role:
                        candidates = registry.exact_name(name)
                        candidates = [r for r in candidates if normalize(r.role) == normalize(role)]
                        method = "exact_name_with_role"
                    if not candidates and role:
                        candidates=registry.short_name(name,role)
                        method="exact_short_name_with_role"
            if mention.organization_scope:
                candidates = [r for r in candidates if r.recipient_type != "INTERNAL_PERSON"
                              or normalize(mention.organization_scope) in normalize(r.parent_name + " " + r.name)
                              or (r.sphere == "internal" and normalize(mention.organization_scope) == normalize(metadata.issuer))]
            local_province = "gia lai" in normalize(query) or (
                re.search(r"(?:^| )tinh$", normalize(query)) and "gia lai" in normalize(metadata.issuer))
            def within_jurisdiction(item):
                # A generic "... tỉnh" cannot point at a different provincial directory.
                return (not local_province or item.sphere == "internal" or "gia lai" in normalize(item.name)
                        or item.code.startswith(("H21", "A21", "K21")))
            candidates = [r for r in candidates if within_jurisdiction(r)]
            if len(candidates) > 1:
                reason = "ambiguous_role" if method == "exact_unique_role" else "ambiguous_registry_identity"
            if not candidates and not reason:
                candidates = [r for r in registry.search(query) if within_jurisdiction(r)]
                # Generic role/known portfolio never delegates identity guessing to LLM.
                roleish = mention.kind == "role" or normalize(query).startswith(("chu tich ", "pho chu tich ", "pho chanh ", "chanh van "))
                if roleish:
                    reason = "ambiguous_role" if candidates else "not_in_registry"
                elif provider and candidates:
                    try:
                        selected = await provider.choose_candidate(mention, [r.model_dump(mode="json") for r in candidates], metadata.model_dump(mode="json"))
                        if selected and selected in {r.recipient_id for r in candidates}:
                            candidates = [registry.by_id[selected]]
                            method = "constrained_model"
                            if "model_suggestion_requires_review" not in result.review_reasons:
                                result.review_reasons.append("model_suggestion_requires_review")
                        else:
                            reason = "invalid_model_output" if selected else "not_in_registry"
                    except Exception as error:
                        reason = "invalid_model_output" if getattr(error,"code",None) == "invalid_model_output" else "provider_unavailable"
                else:
                    reason = "not_in_registry"
        if not candidates and not reason:
            reason = "not_in_registry"
        if candidates and not reason:
            if any(r.recipient_type == "INTERNAL_GROUP" and r.recipient_id not in registry.selectable_groups for r in candidates):
                reason = "missing_group_membership"
        if reason:
            result.unresolved.append(Unresolved(mention_id=mention.mention_id,raw=mention.raw,kind=mention.kind,evidence=mention.evidence,reason=reason,candidates=candidates))
            continue
        for candidate in candidates:
            # Clone registry objects; evidence never mutates the pinned snapshot.
            key = candidate.recipient_id
            if key not in chosen:
                chosen[key] = candidate.model_copy(deep=True)
                chosen[key].match_method = method
            recipient = chosen[key]
            recipient.mention_ids.append(mention.mention_id)
            recipient.evidence.extend(mention.evidence)
    result.people = [r for r in chosen.values() if r.recipient_type == "INTERNAL_PERSON"]
    result.units = [r for r in chosen.values() if r.recipient_type != "INTERNAL_PERSON"]
    result.timings_ms["resolution"] = round((perf_counter()-started)*1000,2)
    # Revalidate after filling lists so needs_review invariant is always enforced.
    return OutgoingResult.model_validate(result.model_dump())
