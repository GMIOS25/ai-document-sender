"""Replay sheet mentions without cloud calls; compare learning off/on, not PDF extraction."""
import argparse
import asyncio
from collections import Counter
from dataclasses import replace
import json
from pathlib import Path
import re
from time import perf_counter

from ai_document_sender.config import Settings
from ai_document_sender.contracts import DocumentMetadata, Extraction
from ai_document_sender.learning import bind_targets
from ai_document_sender.mentions import make_mention
from ai_document_sender.registry import Registry
from ai_document_sender.resolver import resolve_mentions
from ai_document_sender.tenants import TenantManager
from tools.learn_recipient_sheet import SCOPE, sheet_rows, target_spec


async def evaluate(source, policy, settings):
    baseline = Registry(settings)
    baseline.policy.pop('learning', None)
    baseline._build_indexes()
    snapshot = baseline.snapshot()
    snapshot['policy'] = {**snapshot['policy'], 'learning': policy}
    learned = Registry.from_snapshot(settings, snapshot)
    rows = list(sheet_rows(source))
    counts = Counter()
    timings = Counter()
    regressions, changed_black, red_failures = [], [], []
    for row in rows:
        if not row['raw']:
            continue
        section = row.get('section') or 'noi_nhan'
        raw = row['raw']
        group = 'missing_group_membership' in row['target_note'] or bool(re.search(r'\b(?:các|toàn bộ|lãnh đạo)\b', raw, re.I))
        kind = 'group' if group else ('role' if re.match(r'^(?:PCT|PVP|PCVP|CVP|CT\b|Chủ tịch)', raw, re.I) else 'unknown')
        mention = make_mention(raw, kind, 1, section, qualifier=row.get('qualifier'), organization_scope=SCOPE)
        extraction = Extraction(mentions=[mention], status='complete')
        metadata = DocumentMetadata(document_id=row['document'], sign_number=row['document'], issuer=SCOPE)
        results = []
        for name, registry in [('baseline', baseline), ('learned', learned)]:
            started = perf_counter()
            result = await resolve_mentions(extraction, registry, metadata, 'replay', 'sha')
            timings[name] += perf_counter() - started
            results.append({r.recipient_id for r in [*result.people, *result.units]})
        before, after = results
        if row['red']:
            specs = [target_spec(t.strip(), learned) for t in row['target'].split(';') if t.strip()]
            members, reason = bind_targets({'targets': specs, 'verification_status': 'verified'}, learned)
            if reason:
                counts['red_not_uniquely_bindable'] += 1
                continue
            expected = {r.recipient_id for r in members}
            counts['red_evaluable'] += 1
            counts['red_exact_before'] += before == expected
            counts['red_exact_after'] += after == expected
            if after and after != expected:
                red_failures.append({'row': row['row'], 'raw': raw, 'expected': sorted(expected), 'actual': sorted(after)})
        elif row['target'] != '-':
            expected = re.search(r'^recipient_id: (.+)$', row['target_note'], re.M)
            if expected:
                counts['black_with_identity_note'] += 1
                counts['black_identity_before'] += expected[1] in before
                counts['black_identity_after'] += expected[1] in after
                if expected[1] in before and expected[1] not in after:
                    regressions.append({'row': row['row'], 'raw': raw, 'expected': expected[1], 'actual': sorted(after)})
            if before != after:
                changed_black.append({'row': row['row'], 'raw': raw, 'before': sorted(before), 'after': sorted(after)})
        if before and not before <= after:
            counts['rows_losing_baseline_selection'] += 1
    return {'method': f'Replay {len(rows)} sheet rows, reconstructed mentions and recorded qualifier/section; no provider. This is a learning replay, not an independent accuracy test or a PDF/LLM extraction rerun.',
            'counts': dict(counts), 'resolution_seconds': dict(timings), 'black_regressions': regressions,
            'black_changed': changed_black, 'red_wrong_nonempty': red_failures}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--policy', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    settings = Settings.from_env()
    db = TenantManager(settings).get_db_path('vpub')
    result = asyncio.run(evaluate(json.loads(args.source.read_text(encoding='utf-8')),
                                 json.loads(args.policy.read_text(encoding='utf-8')), replace(settings, lookup_db=db)))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k not in {'black_changed', 'black_regressions', 'red_wrong_nonempty'}}, ensure_ascii=False, indent=2))
    print('black_regressions:', len(result['black_regressions']), 'red_wrong_nonempty:', len(result['red_wrong_nonempty']))


if __name__ == '__main__':
    main()
