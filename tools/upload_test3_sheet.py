import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE_DIR = ROOT / 'var' / 'test3-red-corrections-2026-11-07' / 'source'
BATCH_DIR = ROOT / '.tmp' / 'test3_upload_batches'
BATCH_DIR.mkdir(parents=True, exist_ok=True)

SPREADSHEET_ID = '1FTx3IDxfaOadbXmY6BB9pRkRqCdnCter12poQ1txu9s'
SHEET_ID = 1658595127  # Sheet ID for Test 3

# Load test2 data rows
t2_files = sorted(SOURCE_DIR.glob('test2-*.json'))
t2_rows = []
for p in t2_files:
    b = json.loads(p.read_text(encoding='utf-8'))
    for s in b['sheets']:
        for d in s.get('data', []):
            start = d.get('startRow', 0)
            for i, r in enumerate(d.get('rowData', [])):
                row_idx = start + i + 1
                vals = [c.get('formattedValue', c.get('userEnteredValue', {}).get('stringValue', '')) for c in r.get('values', [])]
                t2_rows.append((row_idx, vals))

data_rows = t2_rows[1:]  # skip header row
total_data_rows = len(data_rows)
print(f'Total data rows to upload: {total_data_rows}')

chunk_size = 500
batches = []
for chunk_start in range(0, total_data_rows, chunk_size):
    chunk = data_rows[chunk_start:chunk_start + chunk_size]
    start_row_idx = chunk_start + 1  # 0-indexed row index in sheet (header is row 0)
    end_row_idx = start_row_idx + len(chunk)
    
    rows_payload = []
    for row_num, vals in chunk:
        target_val = vals[4] if len(vals) > 4 else ''
        note_val = vals[5] if len(vals) > 5 else ''
        rows_payload.append({
            'values': [
                {'userEnteredValue': {'stringValue': target_val}},
                {'userEnteredValue': {'stringValue': note_val}}
            ]
        })
    
    req = {
        'requests': [
            {
                'updateCells': {
                    'range': {
                        'sheetId': SHEET_ID,
                        'startRowIndex': start_row_idx,
                        'endRowIndex': end_row_idx,
                        'startColumnIndex': 4,
                        'endColumnIndex': 6
                    },
                    'rows': rows_payload,
                    'fields': 'userEnteredValue'
                }
            }
        ]
    }
    
    batch_file = BATCH_DIR / f'batch_{chunk_start:04d}.json'
    batch_file.write_text(json.dumps(req, ensure_ascii=False), encoding='utf-8')
    batches.append(batch_file)

print(f'Prepared {len(batches)} batches.')

# Execute batches
for i, batch_file in enumerate(batches):
    cmd = ['gsheets', 'mutate', 'raw-batch', SPREADSHEET_ID, '-f', str(batch_file)]
    res = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', shell=True)
    if res.returncode != 0:
        print(f'Batch {i} failed: {res.stderr}')
        sys.exit(1)
    print(f'Batch {i+1}/{len(batches)} uploaded successfully (rows {chunk_size*i + 1} to {min(chunk_size*(i+1), total_data_rows)}).')

print('All batches uploaded successfully!')
