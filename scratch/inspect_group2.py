import zipfile
import xml.etree.ElementTree as ET
import re
import json

def inspect_group2():
    with zipfile.ZipFile('test4_export.xlsx', 'r') as z:
        sst_xml = z.read('xl/sharedStrings.xml')
        sst_root = ET.fromstring(sst_xml)
        ns = {'ns': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
        
        shared_strings = []
        for si in sst_root.findall('ns:si', ns):
            texts = [t.text for t in si.findall('.//ns:t', ns) if t.text]
            shared_strings.append("".join(texts))
            
        styles_xml = z.read('xl/styles.xml')
        s_root = ET.fromstring(styles_xml)
        
        fills = []
        for f in s_root.findall('.//ns:fills/ns:fill', ns):
            pat = f.find('ns:patternFill', ns)
            if pat is not None:
                fg = pat.find('ns:fgColor', ns)
                fg_rgb = fg.get('rgb') if fg is not None else None
                fills.append(fg_rgb)
            else:
                fills.append(None)
                
        fonts = []
        for font in s_root.findall('.//ns:fonts/ns:font', ns):
            color = font.find('ns:color', ns)
            c_rgb = color.get('rgb') if color is not None else None
            fonts.append(c_rgb)
            
        cell_xfs = []
        for xf in s_root.findall('.//ns:cellXfs/ns:xf', ns):
            cell_xfs.append({
                'fontId': int(xf.get('fontId', 0)),
                'fillId': int(xf.get('fillId', 0))
            })

        sheet_xml = z.read('xl/worksheets/sheet1.xml')
        sh_root = ET.fromstring(sheet_xml)
        
        merge_cells = []
        for mc in sh_root.findall('.//ns:mergeCells/ns:mergeCell', ns):
            merge_cells.append(mc.get('ref'))
            
        rows = {}
        for row in sh_root.findall('.//ns:sheetData/ns:row', ns):
            r_idx = int(row.get('r'))
            row_data = {}
            for c in row.findall('ns:c', ns):
                ref = c.get('r')
                col_letter = re.match(r'([A-Z]+)', ref).group(1)
                s_idx = int(c.get('s', 0))
                t = c.get('t')
                v_elem = c.find('ns:v', ns)
                val = ""
                if v_elem is not None and v_elem.text:
                    if t == 's':
                        val = shared_strings[int(v_elem.text)]
                    else:
                        val = v_elem.text
                row_data[col_letter] = {
                    'val': val,
                    's': s_idx,
                    'fill': fills[cell_xfs[s_idx]['fillId']],
                    'font': fonts[cell_xfs[s_idx]['fontId']]
                }
            rows[r_idx] = row_data

    # Map merges for H
    h_merges = {}
    for m in merge_cells:
        m_match = re.match(r'^H(\d+):H(\d+)$', m)
        if m_match:
            r1, r2 = int(m_match.group(1)), int(m_match.group(2))
            stt_val = rows.get(r1, {}).get('A', {}).get('val', '')
            try:
                stt_num = int(float(stt_val))
                h_merges[stt_num] = (r1, r2)
            except:
                pass

    group2_stts = [16, 25, 46, 78, 81, 86, 98]
    print("=== INSPECTING GROUP 2 (7 DOCS) ===")
    for stt in group2_stts:
        r1, r2 = h_merges[stt]
        so_hieu = rows.get(r1, {}).get('B', {}).get('val', '')
        h_text = rows.get(r1, {}).get('H', {}).get('val', '')
        
        # parse H text
        h_du_match = re.search(r'- Dư\s*\((\d+)\):', h_text)
        h_thieu_match = re.search(r'- Thiếu\s*\((\d+)\):', h_text)
        h_du = int(h_du_match.group(1)) if h_du_match else 0
        h_thieu = int(h_thieu_match.group(1)) if h_thieu_match else 0
        
        # extract items in H
        du_part = ""
        if h_du_match:
            du_part = h_text[h_du_match.end():]
            if '- Thiếu' in du_part:
                du_part = du_part[:du_part.index('- Thiếu')]
        h_du_items = [l.strip()[2:].strip() for l in du_part.split('\n') if l.strip().startswith('+')]
        
        thieu_part = ""
        if h_thieu_match:
            thieu_part = h_text[h_thieu_match.end():]
        h_thieu_items = [l.strip()[2:].strip() for l in thieu_part.split('\n') if l.strip().startswith('+')]

        # Sheet rows
        yellow_rows = []
        red_rows = []
        exc_rows = []
        for r in range(r1, r2 + 1):
            g = rows.get(r, {}).get('G', {})
            e = rows.get(r, {}).get('E', {})
            if g.get('fill') == 'FFFFEB9C':
                yellow_rows.append((r, e.get('val', '')))
            elif g.get('fill') == 'FFFFC7CE':
                red_rows.append((r, g.get('val', '')))
            elif g.get('font') == 'FFFF0000':
                exc_rows.append((r, g.get('val', '')))
                
        print(f"\n--- STT {stt} ({so_hieu}, R:{r1}-{r2}) ---")
        print(f"H reported: Dư={h_du} (items: {len(h_du_items)}), Thiếu={h_thieu} (items: {len(h_thieu_items)})")
        print(f"Sheet actual: Yellow={len(yellow_rows)}, Red={len(red_rows)}, Exc={len(exc_rows)}")
        
        # Check Yellow not in H
        y_names = [y[1] for y in yellow_rows]
        y_diff = set(y_names) - set(h_du_items)
        print(f"Yellow not in H: {y_diff}")
        print(f"Exceptions: {exc_rows}")
        
        # Check duplicate yellow names
        from collections import Counter
        c_y = Counter(y_names)
        dups = {k: v for k, v in c_y.items() if v > 1}
        if dups:
            print(f"Duplicate Yellow names: {dups}")

if __name__ == '__main__':
    inspect_group2()
