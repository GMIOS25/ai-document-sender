"""Reviewed, tenant-local aliases; names are rebound to the current directory."""
import json

from .registry import normalize


FILENAME = 'recipient_learning.v1.json'
REVIEW_FILENAME = 'recipient_review_candidates.v1.json'


def read_learning(db_path):
    path = db_path.parent / FILENAME
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding='utf-8-sig'))
    if data.get('version') != 1 or not data.get('organization_scope') or not isinstance(data.get('rules'), list):
        raise ValueError('Invalid recipient learning policy')
    review_path = db_path.parent / REVIEW_FILENAME
    if review_path.exists():
        try:
            r_data = json.loads(review_path.read_text(encoding='utf-8-sig'))
            if r_data.get('version') == 1 and isinstance(r_data.get('rules'), list):
                data['review_candidates'] = r_data.get('rules', [])
        except Exception:
            pass
    return data


def bind_targets(rule, registry):
    """Return all members only when each target has one current identity."""
    if rule.get('verification_status') not in ('verified', 'review_required'):
        return [], 'ambiguous_learned_alias'
    members = {}
    for target in rule.get('targets', []):
        if not target.get('code') and not target.get('sphere'):
            routes = [route for route in registry.policy.get('learning', {}).get('target_routes', [])
                      if route.get('verification_status') == 'verified'
                      and normalize(route.get('name')) == normalize(target['name'])]
            if len(routes) > 1:
                return [], 'learned_target_ambiguous'
            if routes:
                target = {**routes[0], **target}
        matches = registry.exact_name(target['name'])
        for field in ('role', 'code', 'sphere', 'recipient_type'):
            if target.get(field):
                matches = [r for r in matches if normalize(getattr(r, field)) == normalize(target[field])]
        if len(matches) != 1:
            return [], 'learned_target_missing' if not matches else 'learned_target_ambiguous'
        members[matches[0].recipient_id] = matches[0]
    return (list(members.values()), None) if members else ([], 'learned_target_missing')


def index_learning(registry):
    registry._learned_aliases = {}
    for rule in registry.policy.get('learning', {}).get('rules', []):
        registry._learned_aliases.setdefault(normalize(rule['raw_alias']), []).append(rule)
    registry._review_candidates = {}
    for rule in registry.policy.get('learning', {}).get('review_candidates', []):
        registry._review_candidates.setdefault(normalize(rule['raw_alias']), []).append(rule)


def learned_alias(registry, raw, metadata, mention):
    policy = registry.policy.get('learning', {})
    scope = metadata.issuer or mention.organization_scope
    if not scope or normalize(scope) != normalize(policy.get('organization_scope')):
        return None
    if mention.organization_scope and normalize(mention.organization_scope) != normalize(scope):
        return None
    matches = []
    sign_number = normalize(getattr(metadata, 'sign_number', '') or getattr(metadata, 'document_id', '') or '')
    for rule in registry._learned_aliases.get(normalize(raw), []):
        if rule.get('document_context'):
            rule_sign = normalize(rule['document_context'].get('sign_number', ''))
            if rule_sign and rule_sign != sign_number:
                continue
        if rule.get('qualifier') and normalize(rule['qualifier']) != normalize(mention.qualifier):
            continue
        if rule.get('sections'):
            allowed = set(rule['sections'])
            # A validated article expansion retains the originating Nơi nhận
            # evidence and its reference chain alongside the referenced body.
            references = {normalize(ref) for ref in mention.references}
            if 'noi_nhan' in allowed and any(
                    e.section == 'noi_nhan' and normalize(e.raw) in references for e in mention.evidence):
                allowed.add('body_reference')
            if any(e.section not in allowed for e in mention.evidence):
                continue
        matches.append(rule)
    if not matches:
        return None
    doc_matches = [r for r in matches if r.get('document_context') and r['document_context'].get('sign_number')]
    if len(doc_matches) == 1:
        matches = doc_matches
    elif len(matches) > 1:
        verified = [r for r in matches if r.get('verification_status') == 'verified']
        if len(verified) == 1:
            matches = verified
    if len(matches) != 1:
        return {'verification_status': 'conflicting', 'pending_reason': 'ambiguous_learned_alias'}
    rule = matches[0]
    members, reason = bind_targets(rule, registry)
    if reason:
        return {'verification_status': 'pending', 'pending_reason': reason}
    return {'verification_status': 'verified', 'member_ids': [r.recipient_id for r in members],
            'source_rows': rule.get('source_rows', []), 'source': policy.get('source')}


def get_review_candidate(registry, raw, metadata, mention):
    """Retrieve provisional review suggestion without adding to verified result."""
    policy = registry.policy.get('learning', {})
    scope = metadata.issuer or mention.organization_scope
    if not scope or normalize(scope) != normalize(policy.get('organization_scope')):
        return None
    sign_number = normalize(getattr(metadata, 'sign_number', '') or getattr(metadata, 'document_id', '') or '')
    rules = getattr(registry, '_review_candidates', {}).get(normalize(raw), [])
    matches = []
    for rule in rules:
        if rule.get('document_context'):
            rule_sign = normalize(rule['document_context'].get('sign_number', ''))
            if rule_sign and rule_sign != sign_number:
                continue
        if rule.get('qualifier') and normalize(rule['qualifier']) != normalize(mention.qualifier):
            continue
        matches.append(rule)
    if not matches:
        return None
    doc_matches = [r for r in matches if r.get('document_context') and r['document_context'].get('sign_number')]
    rule = doc_matches[0] if len(doc_matches) == 1 else matches[0]
    members, _ = bind_targets(rule, registry)
    return {
        'verification_status': 'review_required',
        'rule': rule,
        'members': members,
        'review_reasons': rule.get('review_reasons', ['source_marked_prediction'])
    }
