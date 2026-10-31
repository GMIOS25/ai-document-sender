import csv
import json
import os
import sys
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')

pop_path = r'c:\Workspaces\ai-document-sender\.agents\teamwork\explorer_survey_2\populated_rows.csv'
root = r'c:\Workspaces\ai-document-sender\resources\văn bản mẫu\vpub\Hợp lệ'
human_corrections_path = r'c:\Workspaces\ai-document-sender\.agents\teamwork\explorer_survey_3\human_red_corrections.json'

with open(pop_path, 'r', encoding='utf-8') as f:
    rows = list(csv.DictReader(f))

by_nn1 = defaultdict(list)
for r in rows:
    by_nn1[r['NoiNhan1']].append(r)

print('=== Breakdown of 82 Populated Rows by Raw NN1 ===')
for nn1, items in sorted(by_nn1.items(), key=lambda x: -len(x[1])):
    target = items[0]['TargetNoiNhan2']
    src = items[0]['Source']
    rows_str = ', '.join([x['Row'] for x in items[:5]])
    if len(items) > 5:
        rows_str += f'... (+{len(items)-5} more)'
    print(f'Count: {len(items):2d} | NN1: "{nn1}"')
    print(f'         Target: "{target[:70]}" ({src})')
    print(f'         Rows: {rows_str}')
