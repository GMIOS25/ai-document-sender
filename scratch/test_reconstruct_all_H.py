import zipfile
import xml.etree.ElementTree as ET
import re

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

# Function to construct H text for unique entities
def construct_h_text(unique_y, unique_r, unique_ex):
    if not unique_y and not unique_r and not unique_ex:
        return "Đầy đủ (Khớp hoàn toàn như kết quả đích)"
    lines = []
    # Dư
    if unique_y:
        lines.append(f"- Dư ({len(unique_y)}):")
        for it in unique_y:
            lines.append(f"  + {it}")
    else:
        lines.append("- Dư: Không")
    # Thiếu
    if unique_r:
        lines.append(f"- Thiếu ({len(unique_r)}):")
        for it in unique_r:
            lines.append(f"  + {it}")
    else:
        lines.append("- Thiếu: Không")
    # Ngoại lệ (only if > 0)
    if unique_ex:
        lines.append(f"- Ngoại lệ ({len(unique_ex)}):")
        for it in unique_ex:
            lines.append(f"  + {it}")
    return "\n".join(lines)

# Compare reconstructed H with current H across all 500 docs
changed_docs = []
unchanged_docs = []

for r1, r2 in h_merges:
    stt = rows.get(r1, {}).get('A', {}).get('val', '')
    so_hieu = rows.get(r1, {}).get('B', {}).get('val', '')
    current_h = rows[r1].get('H', {}).get('val', '').strip()
    
    y_cells = [rows[r]['E']['val'].strip() for r in range(r1, r2 + 1) if rows[r]['G']['fill'] == 'FFFFEB9C']
    r_cells = [rows[r]['G']['val'].strip() for r in range(r1, r2 + 1) if rows[r]['G']['fill'] == 'FFFFC7CE']
    ex_cells = [rows[r]['G']['val'].strip() for r in range(r1, r2 + 1) if rows[r]['G']['font'] == 'FFFF0000']
    
    unique_y = list(dict.fromkeys([x for x in y_cells if x]))
    unique_r = list(dict.fromkeys([x for x in r_cells if x]))
    unique_ex = list(dict.fromkeys([x for x in ex_cells if x]))
    
    new_h = construct_h_text(unique_y, unique_r, unique_ex)
    
    # Normalize line endings and whitespace for comparison
    cur_norm = "\n".join(l.strip() for l in current_h.splitlines() if l.strip())
    new_norm = "\n".join(l.strip() for l in new_h.splitlines() if l.strip())
    
    if cur_norm == new_norm:
        unchanged_docs.append((stt, so_hieu, r1, r2))
    else:
        changed_docs.append((stt, so_hieu, r1, r2, current_h, new_h, len(unique_y), len(unique_r), len(unique_ex)))

print(f"Total docs: {len(h_merges)}")
print(f"Unchanged docs: {len(unchanged_docs)}")
print(f"Changed docs: {len(changed_docs)}")
print("\nList of changed docs (STT, So Hieu, Row):")
for d in changed_docs:
    print(f"STT {d[0]} ({d[1]}) at H{d[2]}: Y={d[6]}, R={d[7]}, Ex={d[8]}")
