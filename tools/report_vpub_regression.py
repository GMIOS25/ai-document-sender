"""Build auditable sheet rows and comparisons from a completed 500-PDF run."""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re
import sys

from ai_document_sender.config import Settings
from ai_document_sender.learning import bind_targets
from ai_document_sender.registry import Registry, normalize
from tools.learn_recipient_sheet import sheet_rows, target_spec


def label(recipient):
    text = recipient['display_name'] or recipient['name']
    if recipient.get('code') and recipient['code'] not in text:
        text += ' (' + recipient['code'] + ')'
    return text


def cell(value='', note=None, fill=None):
    result = {'userEnteredValue': {'numberValue': value} if isinstance(value, (int, float)) else {'stringValue': str(value)}}
    if note:
        result['note'] = note
    if fill:
        result['userEnteredFormat'] = {'backgroundColor': fill}
    return result


def build(run_dir):
    info = json.loads((run_dir / 'run.json').read_text(encoding='utf-8'))
    source = json.loads((run_dir / 'source.json').read_text(encoding='utf-8'))
    old_rows = list(sheet_rows(source))
    snapshot = json.loads((run_dir / 'registry-snapshot.json').read_text(encoding='utf-8'))
    registry = Registry.from_snapshot(Settings(), snapshot)
    records = [json.loads(p.read_text(encoding='utf-8')) for p in sorted((run_dir / 'documents').glob('*.json'))]
    assert len(records) == 500 and {r['stt'] for r in records} == set(range(1, 501)), 'Run is incomplete'
    assert all(r['registry_version'] == info['registry_version'] and r['alias_policy_version'] == info['alias_policy_version']
               and r['processing_version'] == info['processing_version'] for r in records)
    by_sign = {r['sign_number']: r for r in records}
    baseline = defaultdict(set)
    unannotated_black = []
    old_by_sign = defaultdict(list)
    conflicts = {n for rule in registry.policy.get('learning', {}).get('rules', [])
                 if rule.get('verification_status') != 'verified' for n in rule.get('source_rows', [])}
    for row in old_rows:
        old_by_sign[row['document']].append(row)
        found = re.search(r'^recipient_id: (.+)$', row['target_note'], re.M)
        if found:
            baseline[row['document']].add(found[1])
        elif not row['red'] and row['target'] not in {'', '-'}:
            unannotated_black.append({'row': row['row'], 'document': row['document'], 'raw': row['raw'], 'label': row['target']})
    # Keep the exact existing Drive URLs, matched by sign number, never by row offset.
    links, old_extraction = {}, {}
    for block in source['sheets'][0]['data']:
        sign = None
        for raw_row in block.get('rowData', []):
            values = raw_row.get('values', []) + [{}] * 6
            if values[1].get('formattedValue') and values[1]['formattedValue'] != 'Số hiệu văn bản':
                sign = values[1]['formattedValue']
                old_extraction[sign] = values[0].get('note', '')
            if sign and values[5].get('formattedValue', '').startswith('https://drive.google.com/'):
                links[sign] = values[5]['formattedValue']
    assert set(links) == set(by_sign), 'Missing original PDF link'
    counts = Counter()
    reasons = Counter()
    comparisons, recipient_losses, additions, document_groups = [], [], [], []
    rows = [{'values': [cell(v) for v in ['STT', 'Số hiệu văn bản', 'Trích yếu',
        'Nơi nhận 1 (Trích xuất lại từ PDF)', 'Nơi nhận 2 (Backend hiện tại đã lookup)',
        'Link tài liệu chính']]}]
    counts['source_rows'] = len(old_rows)
    counts['source_red_rows'] = sum(r['red'] for r in old_rows)
    counts['old_provider_http_error_documents'] = sum('provider_http_error' in n for n in old_extraction.values())
    for record in records:
        sign = record['sign_number']
        result = record.get('result', {})
        recipients = {r['recipient_id']: r for r in result.get('people', []) + result.get('units', [])}
        actual = set(recipients)
        old_ids = baseline[sign]
        counts['documents'] += 1
        counts['pipeline_completed'] += record['status'] == 'completed'
        counts['pipeline_failed'] += record['status'] != 'completed'
        counts['extraction_complete'] += result.get('extraction_status') == 'complete'
        counts['extraction_partial'] += result.get('extraction_status') == 'partial'
        counts['needs_review_documents'] += result.get('needs_review', True)
        counts['provider_used_documents'] += record.get('extraction', {}).get('audit', {}).get('provider_used', False)
        counts['provider_http_error_documents'] += 'provider_http_error' in result.get('review_reasons', [])
        counts['old_selected_document_identities'] += len(old_ids)
        counts['new_selected_document_identities'] += len(actual)
        counts['old_identities_preserved'] += len(old_ids & actual)
        counts['old_identities_lost'] += len(old_ids - actual)
        counts['new_identities_added'] += len(actual - old_ids)
        counts['new_mentions'] += len(result.get('mentions', []))
        counts['unresolved_mentions'] += len(result.get('unresolved', []))
        counts['excluded_mentions'] += len(result.get('excluded', []))
        for missing in sorted(old_ids - actual):
            recipient_losses.append({'document': sign, 'recipient_id': missing, 'in_current_directory': missing in registry.by_id})
        by_mid = defaultdict(set)
        for rid, recipient in recipients.items():
            for mid in recipient['mention_ids']:
                by_mid[mid].add(rid)
        by_raw = defaultdict(set)
        mention_keys = set()
        for m in result.get('mentions', []):
            key = (normalize(m['raw']), normalize(m.get('qualifier')))
            mention_keys.add(key)
            by_raw[key].update(by_mid[m['mention_id']])
        red_expected = set()
        for old in old_by_sign[sign]:
            key = (normalize(old['raw']), normalize(old.get('qualifier')))
            old_id = re.search(r'^recipient_id: (.+)$', old['target_note'], re.M)
            if not old['red'] and old_id:
                counts['black_annotated_rows'] += 1
                counts['black_id_preserved_in_document'] += old_id[1] in actual
            if not old['red'] or old['target'] in {'', '-'}:
                continue
            if old['row'] in conflicts:
                counts['red_conflicting_rows_excluded'] += 1
                continue
            specs = [target_spec(t.strip(), registry) for t in old['target'].split(';') if t.strip()]
            members, reason = bind_targets({'targets': specs, 'verification_status': 'verified'}, registry)
            if reason:
                counts['red_missing_or_ambiguous_targets'] += 1
                continue
            expected = {r.recipient_id for r in members}
            red_expected.update(expected)
            selected = by_raw[key]
            exact = expected == selected
            covered = expected <= actual
            counts['red_evaluable_rows'] += 1
            counts['red_exact_raw_after'] += exact
            counts['red_targets_covered_after'] += covered
            counts['red_targets_covered_before'] += expected <= old_ids
            counts['red_raw_not_reproduced'] += key not in mention_keys
            counts['red_wrong_nonempty_same_raw'] += bool(selected) and not exact
            comparisons.append({'row': old['row'], 'document': sign, 'raw': old['raw'], 'qualifier': old.get('qualifier'),
                                'expected_ids': sorted(expected), 'same_raw_actual_ids': sorted(selected),
                                'raw_reproduced': key in mention_keys, 'exact_same_raw': exact,
                                'covered_in_document_before': expected <= old_ids, 'covered_in_document_after': covered})
        confirmed = (actual - old_ids) & red_expected
        counts['new_identities_matching_reviewed_red_targets'] += len(confirmed)
        additions.extend({'document': sign, 'recipient_id': rid, 'matches_reviewed_red_target': rid in confirmed,
                          'name': recipients[rid]['display_name'], 'method': recipients[rid]['match_method']}
                         for rid in sorted(actual - old_ids))
        unresolved = {u['mention_id']: u for u in result.get('unresolved', [])}
        excluded = {e['mention_id']: e for e in result.get('excluded', [])}
        reasons.update(u['reason'] for u in unresolved.values())
        doc_rows = []
        for m in result.get('mentions', []):
            mid = m['mention_id']
            note = f"mention_id: {mid}\nTrích xuất: {result['extraction_status']}\n" + '\n'.join(
                f"Bằng chứng: trang {e['page']} / {e['section']}\n{e['raw']}" for e in m['evidence'])
            if m.get('qualifier'):
                note += '\nqualifier: ' + m['qualifier']
            if m.get('references'):
                note += '\nreferences: ' + json.dumps(m['references'], ensure_ascii=False)
            selected_ids = sorted(by_mid[mid])
            if selected_ids:
                for rid in selected_ids:
                    recipient = recipients[rid]
                    outcome = f"Đã resolve: {recipient['match_method']}\nrecipient_id: {rid}\nsource_id: {recipient['source_id']}\nrecipient_type: {recipient['recipient_type']}\nsphere: {recipient['sphere']}\ncode: {recipient.get('code', '')}"
                    outcome += '\nĐã có trong kết quả backend cũ.' if rid in old_ids else '\nBackend hiện tại chọn thêm so với kết quả cũ.'
                    doc_rows.append([cell(), cell(), cell(), cell(m['raw'], note),
                                     cell(label(recipient), outcome, None if rid in old_ids else {'red': .89, 'green': .96, 'blue': .91}), cell()])
            else:
                pending = unresolved.get(mid) or excluded.get(mid)
                assert pending is not None, 'Mention has no resolution outcome'
                outcome = ('Cần rà soát: ' if mid in unresolved else 'Đã loại trừ: ') + pending['reason']
                outcome += '\nỨng viên chưa được chọn không phải kết quả lookup.'
                if pending.get('candidates'):
                    outcome += '\nỨng viên: ' + '; '.join(f"{r['name']} [{r.get('code', '')}; {r['sphere']}]" for r in pending['candidates'])
                doc_rows.append([cell(), cell(), cell(), cell(m['raw'], note), cell('-', outcome, {'red': 1, 'green': .96, 'blue': .85}), cell()])
        if not doc_rows:
            doc_rows.append([cell(), cell(), cell(), cell('-', 'Không trích xuất được mention; xem trạng thái văn bản.'), cell('-', str(record.get('error') or result.get('review_reasons'))), cell()])
        status_note = f"Lượt hồi quy: {info['started_at']}\nTrích xuất: {result.get('extraction_status', 'failed')}\nneeds_review: {result.get('needs_review', True)}\nreview_reasons: {', '.join(result.get('review_reasons', []))}\nSHA256: {record['input_sha256']}\nOpenRouter đã nhận kết quả model: {record.get('extraction', {}).get('audit', {}).get('provider_used', False)}\nThời gian: {record['duration_seconds']} giây"
        doc_rows[0][0] = cell(record['stt'], status_note)
        doc_rows[0][1] = cell(sign)
        doc_rows[0][2] = cell(record.get('metadata', {}).get('subject', ''))
        doc_rows[0][5] = cell(links[sign], 'Giữ nguyên link PDF chính từ tab Thống kê.')
        document_groups.append({'stt': record['stt'], 'start': len(rows), 'end': len(rows) + len(doc_rows)})
        rows.extend({'values': r} for r in doc_rows)
    counts['output_data_rows'] = len(rows)-1
    assert counts['documents'] == 500
    assert counts['old_identities_preserved'] + counts['old_identities_lost'] == counts['old_selected_document_identities']
    assert counts['red_targets_covered_after'] <= counts['red_evaluable_rows']
    for loss in recipient_losses:
        record = by_sign[loss['document']]
        result = record.get('result', {})
        old = [r for r in old_by_sign[loss['document']]
               if re.search(r'^recipient_id: ' + re.escape(loss['recipient_id']) + r'$', r['target_note'], re.M)]
        keys = {(normalize(r['raw']), normalize(r.get('qualifier'))) for r in old}
        matching = {m['mention_id'] for m in result.get('mentions', [])
                    if (normalize(m['raw']), normalize(m.get('qualifier'))) in keys}
        loss['old_raws'] = sorted({r['raw'] for r in old})
        loss['new_unresolved_reasons'] = sorted({u['reason'] for u in result.get('unresolved', []) if u['mention_id'] in matching})
        loss['cause'] = ('pipeline_failed' if record['status'] != 'completed' else
                         'not_in_current_directory' if not loss['in_current_directory'] else
                         'raw_missing_or_changed' if not matching else 'raw_present_but_not_resolved')
    report = {'run': info, 'counts': dict(counts), 'unresolved_reasons': dict(reasons),
              'baseline_basis': 'Only explicit recipient_id annotations prove old backend identities. Black labels without an ID annotation are kept separately, not guessed into the baseline.',
              'black_rows_without_identity_annotation': unannotated_black,
              'old_loss_cause_counts': dict(Counter(loss['cause'] for loss in recipient_losses)),
              'recipient_losses': recipient_losses, 'new_identity_details': additions, 'red_comparisons': comparisons,
              'interpretation': 'Same reviewed training set. Model extraction errors are retained. Raw changes and routing outcomes are measured separately; unannotated outputs are not assumed wrong or correct.'}
    (run_dir / 'comparison.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    rows[0]['values'][0]['note'] = 'Chạy lại đủ 500 PDF gốc; bảng tổng hợp ở H1:I22. Ô E xanh nhạt = backend chọn thêm; vàng nhạt = chưa resolve/đã loại trừ. Chữ đen là kết quả backend, không có sửa tay.'
    rows[0]['values'][3]['note'] = 'Raw mới từ extract_document. Không sao chép raw cũ để giả lập kiểm thử. Xem ghi chú từng ô để biết bằng chứng/section/references.'
    rows[0]['values'][4]['note'] = f"Chỉ ghi identity thực sự được resolve_mentions trả trong people/units và có mention_id tương ứng. Candidates không được ghi làm kết quả.\nregistry_version: {info['registry_version']}\nalias_policy_version: {info['alias_policy_version']}\nprocessing_version: {info['processing_version']}"
    (run_dir / 'sheet-rows.json').write_text(json.dumps(rows, ensure_ascii=False), encoding='utf-8')
    (run_dir / 'sheet-document-groups.json').write_text(json.dumps(document_groups), encoding='utf-8')
    c = counts
    summary = [
        ['HỒI QUY 500 VĂN BẢN VPUB', 'Kết quả'],
        ['PDF gốc đã chạy lại', f"{c['documents']}/500"],
        ['Lỗi làm dừng xử lý', c['pipeline_failed']],
        ['Trích xuất hoàn chỉnh', c['extraction_complete']],
        ['Văn bản cần rà soát', c['needs_review_documents']],
        ['Phản hồi model hợp schema', c['provider_used_documents']],
        ['Lỗi HTTP OpenRouter: cũ → mới', f"{c['old_provider_http_error_documents']} → {c['provider_http_error_documents']}"],
        ['Người/đơn vị được chọn: cũ → mới', f"{c['old_selected_document_identities']} → {c['new_selected_document_identities']}"],
        ['Identity cũ được giữ', f"{c['old_identities_preserved']}/{c['old_selected_document_identities']}"],
        ['Identity cũ không còn được chọn', c['old_identities_lost']],
        ['Identity mới khớp sửa văn thư', c['new_identities_matching_reviewed_red_targets']],
        ['Dòng đỏ đủ điều kiện đối chiếu', c['red_evaluable_rows']],
        ['Đích sửa đỏ có trong danh sách: cũ → mới', f"{c['red_targets_covered_before']} → {c['red_targets_covered_after']}"],
        ['Dòng đỏ khớp đúng raw + đích', c['red_exact_raw_after']],
        ['Dòng đỏ có raw thay đổi/mất', c['red_raw_not_reproduced']],
        ['Dòng đỏ loại vì mâu thuẫn', c['red_conflicting_rows_excluded']],
        ['Dòng đỏ thiếu/trùng đích danh bạ', c['red_missing_or_ambiguous_targets']],
        ['Tổng mentions chưa resolve', c['unresolved_mentions']],
        ['Cách đọc màu nền', 'Xanh: chọn thêm; vàng: chưa resolve/loại trừ. Chữ đen: backend.'],
        ['Giới hạn kết luận', 'Đối soát lại tập đã dùng để học; không phải độ chính xác trên văn bản mới.'],
        ['Trạng thái cloud', 'HTTP 404 còn xảy ra; cần rà soát trích xuất partial.'],
        ['Lượt chạy', info['started_at']],
    ]
    summary_rows = [{'values': [cell(x) for x in r]} for r in summary]
    summary_rows[7]['values'][0]['note'] = 'Mỗi ID được đếm một lần trong từng văn bản. Cũ: recipient_id ghi trong ghi chú nguồn. Mới: IDs thực sự nằm trong result.people/units. Các ô cũ không có ghi chú ID không được tự suy ra identity.'
    summary_rows[10]['values'][0]['note'] = 'Chỉ tính identity mới so với ID cũ đã ghi nhận và khớp một đích sửa đỏ xác định duy nhất. Các ID mới khác chưa được coi là khớp chuẩn văn thư.'
    (run_dir / 'sheet-summary.json').write_text(json.dumps(summary_rows, ensure_ascii=False), encoding='utf-8')
    lines = ['# Hồi quy 500 văn bản VPUB — 31/10/2026', '',
             f"Đã chạy lại {c['documents']} PDF gốc qua extract_document và resolve_mentions hiện tại. Tab kết quả: **Thống kê 2**, Google Sheets gốc. SHA-256 được đối chiếu với ghi chú nguồn; không dùng kết quả gửi thực tế làm đầu vào resolver.", '',
             '| Chỉ số | Trước | Sau |', '|---|---:|---:|',
             f"| Identity được chọn, mỗi ID một lần trong từng văn bản | {c['old_selected_document_identities']} | {c['new_selected_document_identities']} |",
             f"| Dòng sửa đỏ có đủ đích trong danh sách cuối ({c['red_evaluable_rows']} dòng đối chiếu được) | {c['red_targets_covered_before']} | {c['red_targets_covered_after']} |",
             f"| Văn bản có lỗi HTTP OpenRouter | {c['old_provider_http_error_documents']} | {c['provider_http_error_documents']} |", '',
             f"Giữ được {c['old_identities_preserved']}/{c['old_selected_document_identities']} identity cũ; {c['old_identities_lost']} identity không còn được chọn. Trong các identity mới, {c['new_identities_matching_reviewed_red_targets']} khớp đích đã được văn thư sửa. Còn {c['unresolved_mentions']} mentions chưa resolve, {c['needs_review_documents']} văn bản cần rà soát và {c['extraction_complete']} văn bản có extraction_status complete.", '',
             f"Loại {c['red_conflicting_rows_excluded']} dòng đỏ mâu thuẫn khỏi đánh giá; {c['red_missing_or_ambiguous_targets']} dòng khác còn thiếu hoặc trùng identity trong danh bạ. Có {c['red_raw_not_reproduced']} dòng đỏ đủ đích nhưng raw đã thay đổi hoặc không trích xuất lại được. Không xem ứng viên search là identity đã chọn.", '',
             'Các số trên mô tả tập đã dùng để đối soát/học. Chúng không phải độ chính xác trên văn bản mới. Lỗi cloud và trích xuất partial được giữ nguyên trong kết quả; lượt hồi quy không thay đổi cấu hình model hay sửa backend giữa chừng.', '',
             f"Mốc cũ được chốt bằng recipient_id có trong ghi chú nguồn. Có {len(unannotated_black)} ô đen có nhãn nhưng thiếu ghi chú ID; chúng được lưu riêng để rà soát, không được suy ra thành identity backend cũ. Vì vậy số chọn thêm được tính so với các ID cũ có thể chứng minh; phần khớp sửa đỏ được thống kê riêng.", '',
             f"Registry: `{info['registry_version']}`. Policy: `{info['alias_policy_version']}`. Processing: `{info['processing_version']}`.", '',
             'Chi tiết và bằng chứng được lưu ở comparison.json, documents/*.json và registry-snapshot.json trong thư mục chạy. Ô E xanh nhạt: backend chọn thêm so với kết quả cũ; vàng nhạt: chưa resolve hoặc đã loại trừ. Mọi kết quả tự động dùng chữ đen.', '',
             'Các identity cũ không còn được chọn:', '', '| Văn bản | Identity | Raw cũ | Phân loại |', '|---|---|---|---|']
    for loss in recipient_losses:
        raw = '; '.join(loss['old_raws']).replace('|', '\\|').replace('\n', ' ')[:220]
        lines.append(f"| {loss['document']} | {loss['recipient_id']} | {raw} | {loss['cause']}: {', '.join(loss['new_unresolved_reasons'])} |")
    (run_dir / 'report.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(json.dumps({'counts': dict(counts), 'unresolved_reasons': dict(reasons)}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run_dir', type=Path)
    build(parser.parse_args().run_dir)
