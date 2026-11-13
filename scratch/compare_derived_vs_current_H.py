import zipfile
import xml.etree.ElementTree as ET
import re
from collections import Counter

def run():
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
                val = ''
                if v_elem is not None and v_elem.text:
                    val = shared_strings[int(v_elem.text)] if t == 's' else v_elem.text
                row_data[col] = {
                    'val': val,
                    'fill': fills[cell_xfs[s_idx]['fillId']],
                    'font': fonts[cell_xfs[s_idx]['fontId']]
                }
            rows[r_idx] = row_data

    # Parse merges for H
    h_merges = []
    for m in merge_cells:
        m_match = re.match(r'^H(\d+):H(\d+)$', m)
        if m_match:
            r1, r2 = int(m_match.group(1)), int(m_match.group(2))
            h_merges.append((r1, r2))
    h_merges = sorted(h_merges, key=lambda x: x[0])
    print(f'Total H merges: {len(h_merges)}')

    # For each doc, extract from sheet formatting:
    # 1. unique yellow from Col E
    # 2. unique red from Col G
    # 3. unique red-font from Col G
    # Compare with H parsed lists
    
    perfect_match_count = 0
    mismatch_docs = []

    for r1, r2 in h_merges:
        stt_val = rows.get(r1, {}).get('A', {}).get('val', '')
        so_hieu = rows.get(r1, {}).get('B', {}).get('val', '')
        h_text = rows.get(r1, {}).get('H', {}).get('val', '').strip()

        # Parse current H text items
        current_du_items = []
        current_thieu_items = []
        current_ngoai_le_items = []
        
        # parse lines
        mode = None
        for line in h_text.splitlines():
            line_str = line.strip()
            if line_str.startswith('- Dư'):
                mode = 'du'
            elif line_str.startswith('- Thiếu'):
                mode = 'thieu'
            elif line_str.startswith('- Ngoại lệ'):
                mode = 'ngoai_le'
            elif line_str.startswith('+ '):
                item = line_str[2:].strip()
                if mode == 'du':
                    current_du_items.append(item)
                elif mode == 'thieu':
                    current_thieu_items.append(item)
                elif mode == 'ngoai_le':
                    current_ngoai_le_items.append(item)

        # Extract from sheet cells
        sheet_yellow_cells = []
        sheet_red_cells = []
        sheet_exc_cells = []
        sheet_green_cells = []

        for r in range(r1, r2 + 1):
            g = rows.get(r, {}).get('G', {})
            e = rows.get(r, {}).get('E', {})
            g_fill = g.get('fill')
            g_font = g.get('font')
            e_val = e.get('val', '').strip()
            g_val = g.get('val', '').strip()

            if g_fill == 'FFFFEB9C': # Yellow -> Dư
                sheet_yellow_cells.append(e_val)
            elif g_fill == 'FFFFC7CE': # Red -> Thiếu
                sheet_red_cells.append(g_val)
            elif g_font == 'FFFF0000': # Red font -> Ngoại lệ
                sheet_exc_cells.append(g_val)
            elif g_fill == 'FFC6EFCE': # Green -> Trùng khớp
                sheet_green_cells.append((e_val, g_val))

        # Unique entities (preserving order of appearance)
        sheet_unique_yellow = list(dict.fromkeys([x for x in sheet_yellow_cells if x]))
        sheet_unique_red = list(dict.fromkeys([x for x in sheet_red_cells if x]))
        sheet_unique_exc = list(dict.fromkeys([x for x in sheet_exc_cells if x]))

        # Compare sets
        du_diff = set(sheet_unique_yellow) ^ set(current_du_items)
        thieu_diff = set(sheet_unique_red) ^ set(current_thieu_items)
        exc_diff = set(sheet_unique_exc) ^ set(current_ngoai_le_items)

        if not du_diff and not thieu_diff and not exc_diff:
            perfect_match_count += 1
        else:
            mismatch_docs.append({
                'stt': stt_val,
                'so_hieu': so_hieu,
                'r1': r1, 'r2': r2,
                'sheet_y': sheet_unique_yellow,
                'h_y': current_du_items,
                'sheet_r': sheet_unique_red,
                'h_r': current_thieu_items,
                'sheet_ex': sheet_unique_exc,
                'h_ex': current_ngoai_le_items,
            })

    print(f'Docs where current H exactly matches unique sheet items (excluding exceptions/gom thieu): {perfect_match_count}')
    print(f'Mismatch docs count: {len(mismatch_docs)}')

if __name__ == '__main__':
    run()
