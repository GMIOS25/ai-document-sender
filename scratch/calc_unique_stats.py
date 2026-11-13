import zipfile
import xml.etree.ElementTree as ET
import re
from collections import Counter, defaultdict

with zipfile.ZipFile(r'C:\Workspaces\Script-Idesk Sender\test4_export.xlsx', 'r') as z:
    sst_root = ET.fromstring(z.read('xl/sharedStrings.xml'))
    ns = {'ns': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    shared_strings = [''.join(t.text for t in si.findall('.//ns:t', ns) if t.text) for si in sst_root.findall('ns:si', ns)]
    styles_root = ET.fromstring(z.read('xl/styles.xml'))
    fills = [f.find('ns:patternFill/ns:fgColor', ns).get('rgb') if f.find('ns:patternFill/ns:fgColor', ns) is not None else None for f in styles_root.findall('.//ns:fills/ns:fill', ns)]
    fonts = [font.find('ns:color', ns).get('rgb') if font.find('ns:color', ns) is not None else None for font in styles_root.findall('.//ns:fonts/ns:font', ns)]
    cell_xfs = [{'fontId': int(xf.get('fontId', 0)), 'fillId': int(xf.get('fillId', 0))} for xf in styles_root.findall('.//ns:cellXfs/ns:xf', ns)]
    sh_root = ET.fromstring(z.read('xl/worksheets/sheet1.xml'))
    merge_cells = [mc.get('ref') for mc in sh_root.findall('.//ns:mergeCells/ns:mergeCell', ns)]
    
    rows = {}
    for row in sh_root.findall('.//ns:sheetData/ns:row', ns):
        r_idx = int(row.get('r'))
        row_data = {}
        for c in row.findall('ns:c', ns):
            ref = c.get('r')
            col = re.match(r'([A-Z]+)', ref).group(1)
            s_idx = int(c.get('s', 0))
            t = c.get('t')
            v_elem = c.find('ns:v', ns)
            val = shared_strings[int(v_elem.text)] if (v_elem is not None and t == 's') else (v_elem.text if v_elem is not None else '')
            row_data[col] = {
                'val': val,
                'fill': fills[cell_xfs[s_idx]['fillId']],
                'font': fonts[cell_xfs[s_idx]['fontId']]
            }
        rows[r_idx] = row_data

h_merges = sorted([tuple(map(int, re.match(r'^H(\d+):H(\d+)$', m).groups())) for m in merge_cells if re.match(r'^H(\d+):H(\d+)$', m)], key=lambda x: x[0])

# Metrics
total_docs = len(h_merges)
total_raw_rows = 18320

total_raw_green = 0
total_raw_yellow = 0
total_raw_red = 0
total_raw_exc = 0

sum_unique_green = 0
sum_unique_yellow = 0
sum_unique_red = 0
sum_unique_exc = 0

docs_100_green = 0
docs_with_yellow = 0
docs_with_red = 0
docs_with_exc = 0

# Also track document categories:
# Exact (100% green)
# Yellow only
# Red only
# Exc only
# Mixed combinations
doc_combos = Counter()

for r1, r2 in h_merges:
    y_cells = [rows[r]['E']['val'].strip() for r in range(r1, r2 + 1) if rows[r]['G']['fill'] == 'FFFFEB9C']
    r_cells = [rows[r]['G']['val'].strip() for r in range(r1, r2 + 1) if rows[r]['G']['fill'] == 'FFFFC7CE']
    ex_cells = [rows[r]['G']['val'].strip() for r in range(r1, r2 + 1) if rows[r]['G']['font'] == 'FFFF0000']
    g_cells = [rows[r]['G']['val'].strip() for r in range(r1, r2 + 1) if rows[r]['G']['fill'] == 'FFC6EFCE' and rows[r]['G']['val'].strip() and rows[r]['G']['val'].strip() != '-']

    total_raw_yellow += len(y_cells)
    total_raw_red += len(r_cells)
    total_raw_exc += len(ex_cells)
    total_raw_green += sum(1 for r in range(r1, r2 + 1) if rows[r]['G']['fill'] == 'FFC6EFCE')

    u_y = set(y_cells) - {''}
    u_r = set(r_cells) - {''}
    u_ex = set(ex_cells) - {''}
    u_g = set(g_cells)

    sum_unique_yellow += len(u_y)
    sum_unique_red += len(u_r)
    sum_unique_exc += len(u_ex)
    sum_unique_green += len(u_g)

    has_y = len(u_y) > 0
    has_r = len(u_r) > 0
    has_ex = len(u_ex) > 0

    if not has_y and not has_r and not has_ex:
        docs_100_green += 1
    if has_y: docs_with_yellow += 1
    if has_r: docs_with_red += 1
    if has_ex: docs_with_exc += 1

    combo = []
    if has_y: combo.append("Dư")
    if has_r: combo.append("Thiếu")
    if has_ex: combo.append("Ngoại lệ")
    if not combo: combo.append("Khớp 100%")
    doc_combos[" + ".join(combo)] += 1

print(f"=== RAW ROWS vs SUM OF UNIQUE ENTITIES PER DOC ===")
print(f"Total documents: {total_docs}")
print(f"Total raw rows: {total_raw_rows}")
print(f"Raw Green cells: {total_raw_green} | Sum of Unique Green: {sum_unique_green}")
print(f"Raw Yellow cells: {total_raw_yellow} | Sum of Unique Yellow (Dư): {sum_unique_yellow}")
print(f"Raw Red cells: {total_raw_red} | Sum of Unique Red (Thiếu): {sum_unique_red}")
print(f"Raw Exception cells: {total_raw_exc} | Sum of Unique Exception (Ngoại lệ): {sum_unique_exc}")

print(f"\n=== DOCUMENT BREAKDOWN ===")
print(f"Docs 100% Green (Khớp hoàn toàn): {docs_100_green} ({docs_100_green/total_docs*100:.2f}%)")
print(f"Docs with Dư: {docs_with_yellow} ({docs_with_yellow/total_docs*100:.2f}%)")
print(f"Docs with Thiếu: {docs_with_red} ({docs_with_red/total_docs*100:.2f}%)")
print(f"Docs with Ngoại lệ: {docs_with_exc} ({docs_with_exc/total_docs*100:.2f}%)")

print(f"\n=== DOCUMENT COMBINATION BREAKDOWN ===")
for combo, cnt in doc_combos.most_common():
    print(f"  {combo}: {cnt} docs ({cnt/total_docs*100:.2f}%)")
