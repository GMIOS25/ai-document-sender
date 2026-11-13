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

test_stts = [16, 17, 46, 78, 99, 152, 308]
for r1, r2 in h_merges:
    stt_val = rows[r1]['A']['val']
    try:
        stt_num = int(float(stt_val))
    except:
        stt_num = -1
    if stt_num in test_stts:
        y_cells = [rows[r]['E']['val'].strip() for r in range(r1, r2 + 1) if rows[r]['G']['fill'] == 'FFFFEB9C']
        r_cells = [rows[r]['G']['val'].strip() for r in range(r1, r2 + 1) if rows[r]['G']['fill'] == 'FFFFC7CE']
        ex_cells = [rows[r]['G']['val'].strip() for r in range(r1, r2 + 1) if rows[r]['G']['font'] == 'FFFF0000']
        
        unique_y = list(dict.fromkeys([x for x in y_cells if x]))
        unique_r = list(dict.fromkeys([x for x in r_cells if x]))
        unique_ex = list(dict.fromkeys([x for x in ex_cells if x]))
        
        cur_h = rows[r1]['H']['val'].strip()
        new_h = construct_h_text(unique_y, unique_r, unique_ex)
        
        print(f"==================================================")
        print(f"STT {stt_num} (Rows {r1}-{r2}) - Cell H{r1}")
        print(f"==================================================")
        print("--- CURRENT H ---")
        print(cur_h)
        print("--- NEW H ---")
        print(new_h)
        print("\n")
