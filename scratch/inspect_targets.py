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

for target_stt in [16, 25, 46, 78, 81, 86, 98, 99, 308]:
    for r1, r2 in h_merges:
        stt = rows.get(r1, {}).get('A', {}).get('val', '')
        try:
            stt_num = int(float(stt))
        except:
            stt_num = -1
        if stt_num == target_stt:
            y_cells = [rows[r]['E']['val'].strip() for r in range(r1, r2 + 1) if rows[r]['G']['fill'] == 'FFFFEB9C']
            r_cells = [rows[r]['G']['val'].strip() for r in range(r1, r2 + 1) if rows[r]['G']['fill'] == 'FFFFC7CE']
            ex_cells = [rows[r]['G']['val'].strip() for r in range(r1, r2 + 1) if rows[r]['G']['font'] == 'FFFF0000']
            unique_y = list(dict.fromkeys(y_cells))
            unique_r = list(dict.fromkeys(r_cells))
            unique_ex = list(dict.fromkeys(ex_cells))
            h_text = rows[r1]['H']['val'].strip()
            print(f'=== STT {target_stt} (Rows {r1}-{r2}) ===')
            print(f'  Yellow cells: {len(y_cells)}, Unique yellow: {len(unique_y)}')
            print(f'  Red cells: {len(r_cells)}, Unique red: {len(unique_r)}')
            print(f'  Exc cells: {len(ex_cells)}, Unique exc: {len(unique_ex)}')
            m_du = re.search(r'- Dư\s*\((\d+)\):', h_text)
            m_th = re.search(r'- Thiếu\s*\((\d+)\):', h_text)
            du_c = m_du.group(1) if m_du else ('0' if '- Dư: Không' in h_text else 'N/A')
            th_c = m_th.group(1) if m_th else ('0' if '- Thiếu: Không' in h_text else 'N/A')
            print(f'  Current H: Du={du_c}, Thieu={th_c}')
            # If unique_y count differs from Current H Du:
            current_du_items = []
            if m_du:
                part = h_text[m_du.end():]
                if '- Thiếu' in part:
                    part = part[:part.index('- Thiếu')]
                current_du_items = [l.strip()[2:].strip() for l in part.splitlines() if l.strip().startswith('+')]
            missing_in_h = set(unique_y) - set(current_du_items)
            extra_in_h = set(current_du_items) - set(unique_y)
            if missing_in_h:
                print('  Unique yellow missing in current H:', missing_in_h)
            if extra_in_h:
                print('  In current H but not in unique yellow:', extra_in_h)
