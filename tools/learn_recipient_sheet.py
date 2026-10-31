"""Compile a Google Sheets CellData snapshot into reviewed tenant aliases.

Preview by default. --apply installs the policy and refreshes derived search text.
No network calls, new recipient IDs, or changes to the source spreadsheet.
"""
import argparse
from collections import Counter, defaultdict
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import sqlite3

from ai_document_sender.config import Settings
from ai_document_sender.learning import FILENAME, bind_targets
from ai_document_sender.registry import Registry, normalize
from ai_document_sender.sync import refresh_search_index
from ai_document_sender.tenants import TenantManager


SCOPE = 'UBND tỉnh Gia Lai'


def sheet_rows(snapshot):
    snapshot = snapshot.get('structuredContent', snapshot)
    sheet = next(s for s in snapshot['sheets'] if s['properties']['title'] == 'Thống kê')
    document = ''
    for block in sheet['data']:
        for number, row in enumerate(block.get('rowData', []), block.get('startRow', 0) + 1):
            cells = row.get('values', []) + [{}] * 6
            value = lambda i: cells[i].get('formattedValue', '').strip()
            if value(1):
                document = value(1)
            if number == 1 or not (value(3) or value(4)):
                continue
            fmt = cells[4].get('effectiveFormat', {}).get('textFormat', {})
            color = fmt.get('foregroundColorStyle', {}).get('rgbColor', fmt.get('foregroundColor', {}))
            note = cells[3].get('note', '')
            qualifier = re.search(r'^qualifier: (.+)$', note, re.M)
            section = re.search(r'Bằng chứng: trang \d+ / (\w+)', note)
            yield {'row': number, 'document': document, 'raw': value(3), 'target': value(4),
                   'red': color.get('red', 0) > .7 and color.get('green', 0) < .4 and color.get('blue', 0) < .4,
                   'rich_text': bool(cells[4].get('textFormatRuns')),
                   'qualifier': qualifier[1] if qualifier else None,
                   'section': section[1] if section else None, 'note': note, 'target_note': cells[4].get('note', '')}


def target_spec(label, registry):
    # Strip only explicit routing codes. A code alone never proves an identity.
    codes = re.findall(r'\(([A-Z][0-9]+(?:\.[A-Z0-9]+)*)\)', label)
    clean = re.sub(r'\([A-Z][0-9]+(?:\.[A-Z0-9]+)*\)', '', label).strip()
    personal = re.fullmatch(r'(.+?)\s*\(([^()]+)\)', clean)
    if personal and registry.exact_name(personal[2]):
        spec = {'name': personal[2].strip(), 'role': personal[1].strip()}
    else:
        # Display labels may carry department/email annotations after a full name.
        prefix = clean.split(' - ', 1)[0]
        people = [r for r in registry.exact_name(prefix) if r.recipient_type == 'INTERNAL_PERSON']
        spec = {'name': prefix, 'role': people[0].role} if len(people) == 1 else {'name': clean}
    if codes:
        spec['code'] = codes[-1]
    members, reason = bind_targets({'verification_status': 'verified', 'targets': [spec]}, registry)
    if reason and not personal and not codes:
        # An omitted province suffix is lexical; require a unique exact local name.
        local = [r for suffix in (' - tỉnh Gia Lai', ' tỉnh Gia Lai')
                 for r in registry.exact_name(clean + suffix)]
        if len(local) == 1:
            members, reason = local, None
    if not reason:
        item = members[0]
        spec = {'name': item.name, 'recipient_type': item.recipient_type, 'sphere': item.sphere}
        if item.role:
            spec['role'] = item.role
        if item.code:
            spec['code'] = item.code
    return spec


def compile_learning(rows, registry):
    buckets = defaultdict(list)
    skipped = []
    for row in rows:
        if not row.get('red') or row['target'] in {'', '-'}:
            continue
        raw = row['raw'].strip(' ;:-')
        reason = None
        if row.get('rich_text'):
            reason = 'mixed_text_format_requires_review'
        elif (not raw or len(raw) > 256 or
              re.search(r'(?:nhận được|có ý kiến như sau|Theo đề nghị|báo cáo tình hình)', raw, re.I) or
              re.fullmatch(r'[A-Za-z](?:\s+[A-Za-z])*', raw) and all(len(t) == 1 for t in raw.split())):
            reason = 'extraction_or_missing_raw'
        elif re.fullmatch(r'[A-Za-z]{1,3}\s*\d{1,3}', raw):
            reason = 'staff_code_uses_current_directory'
        elif normalize(raw) in {'nhu tren', 'nhu kinh gui', 'vt'} or re.match(r'^(?:Như\s+(?:trên|Điều|Mục)|Lưu\b)', raw, re.I):
            reason = 'reference_requires_document_context'
        if reason:
            skipped.append({**row, 'status': reason})
            continue
        buckets[(normalize(raw), normalize(row.get('qualifier')))].append(row)
    rules, decisions = [], []
    for group in buckets.values():
        variants = {}
        warnings = []
        for row in group:
            specs = [target_spec(label.strip(), registry) for label in row['target'].split(';') if label.strip()]
            signature = lambda t: tuple(normalize(t.get(k)) for k in ('name', 'role', 'sphere', 'recipient_type'))
            specs.sort(key=signature)
            key = tuple(signature(t) for t in specs)
            if key in variants:
                for old, new in zip(variants[key], specs):
                    if old.get('code') and new.get('code') and old['code'] != new['code']:
                        warnings.append('conflicting_target_codes')
                    if new.get('code'):
                        old['code'] = new['code']
            else:
                variants[key] = specs
            if normalize(row.get('qualifier')) == 'so' and any(normalize(t['name']).startswith('bo ') for t in specs):
                warnings.append('qualifier_target_mismatch')
            # Explicit named enumerations cannot acquire unrelated recipients.
            if ':' in row['raw'] and len(specs) > 1:
                raw_words = set(normalize(row['raw']).split())
                generic = set('ubnd uy ban nhan dan so tinh gia lai xa phuong thanh pho van phong'.split())
                if any(set(normalize(t['name']).split()) - generic - raw_words for t in specs):
                    warnings.append('enumeration_target_mismatch')
            if normalize(row['raw']) in {'pct ubnd tinh', 'ban qlda'}:
                warnings.append('generic_selector_requires_context')
        conflicting = len(variants) != 1 or bool(warnings)
        rule = {'raw_alias': group[0]['raw'].strip(' ;:-'), 'verification_status': 'conflicting' if conflicting else 'verified',
                'targets': next(iter(variants.values())) if not conflicting else [],
                'source_rows': sorted(r['row'] for r in group)}
        if group[0].get('qualifier'):
            rule['qualifier'] = group[0]['qualifier']
        sections = {r.get('section') for r in group}
        rule['sections'] = sorted(sections - {None}) if None not in sections else ['kinh_gui', 'noi_nhan', 'body_reference']
        if conflicting:
            rule['review_reasons'] = sorted(set(warnings + (['inconsistent_targets'] if len(variants) != 1 else [])))
        rules.append(rule)
        members, reason = bind_targets(rule, registry)
        decisions.append({'raw': rule['raw_alias'], 'qualifier': rule.get('qualifier'), 'rows': rule['source_rows'],
                          'status': reason or 'active', 'targets': sorted({r['target'] for r in group}),
                          'recipient_ids': [m.recipient_id for m in members], 'review_reasons': rule.get('review_reasons', [])})
    policy = {'version': 1, 'organization_scope': SCOPE, 'rules': rules}
    routes = registry.policy.get('learning', {}).get('target_routes')
    if routes:
        policy['target_routes'] = routes
    return policy, {'decisions': decisions, 'skipped': skipped}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True, help='JSON from Google Sheets get_spreadsheet_cells A1:F...')
    parser.add_argument('--tenant', default='vpub', choices=['vpub'], help='This source schema and scope belong to VPUB')
    parser.add_argument('--output', type=Path, default=Path('var/recipient-learning'))
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    settings = Settings.from_env()
    manager = TenantManager(settings)
    db = manager.get_db_path(args.tenant)
    local = replace(settings, lookup_db=db)
    source_bytes = args.source.read_bytes()
    snapshot = json.loads(source_bytes)
    rows = list(sheet_rows(snapshot))
    policy, report = compile_learning(rows, Registry(local))
    body = snapshot.get('structuredContent', snapshot)
    end_row = max(d.get('startRow', 0) + len(d.get('rowData', [])) for s in body['sheets'] for d in s.get('data', []))
    policy['source'] = {'url': body['spreadsheetUrl'], 'sheet': 'Thống kê', 'range': f'A1:F{end_row}',
                        'snapshot_sha256': hashlib.sha256(source_bytes).hexdigest(),
                        'reviewed_on': datetime.now(timezone(timedelta(hours=7))).date().isoformat(),
                        'basis': 'User-authorized red clerical corrections; exact current-directory validation'}
    report['source'] = policy['source']
    report['counts'] = {'data_rows': len(rows), 'documents': len({r['document'] for r in rows}),
                        'red_rows': sum(r['red'] for r in rows), 'rules': len(policy['rules']),
                        'rule_statuses': dict(Counter(d['status'] for d in report['decisions'])),
                        'row_statuses': dict(Counter(d['status'] for d in report['decisions'] for _ in d['rows'])),
                        'skipped_rows': len(report['skipped'])}
    args.output.mkdir(parents=True, exist_ok=True)
    policy_text = json.dumps(policy, ensure_ascii=False, indent=2) + '\n'
    (args.output / FILENAME).write_text(policy_text, encoding='utf-8')
    if args.apply:
        # SQLite's backup API includes committed WAL data and produces a usable rollback copy.
        with sqlite3.connect(db) as conn, sqlite3.connect(args.output / 'lookup.before-learning.db') as backup:
            conn.backup(backup)
        destination = db.parent / FILENAME
        if destination.exists():
            (args.output / 'previous-learning.json').write_bytes(destination.read_bytes())
        temporary = destination.with_suffix('.json.tmp')
        temporary.write_text(policy_text, encoding='utf-8')
        temporary.replace(destination)
        with sqlite3.connect(db) as conn:
            with conn:
                report['search_rows_refreshed'] = refresh_search_index(conn, Registry(local))
            conn.execute('PRAGMA wal_checkpoint(TRUNCATE)')
        manager.invalidate_registry(args.tenant)
        report['alias_policy_version'] = manager.get_registry(args.tenant).alias_policy_version
    (args.output / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report['counts'], ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
