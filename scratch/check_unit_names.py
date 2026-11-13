import json
import zipfile
import xml.etree.ElementTree as ET
import re

def check_unit_name_mismatches():
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

    h_merges = []
    for m in merge_cells:
        m_match = re.match(r'^H(\d+):H(\d+)$', m)
        if m_match:
            r1, r2 = int(m_match.group(1)), int(m_match.group(2))
            h_merges.append((r1, r2))
    h_merges = sorted(h_merges, key=lambda x: x[0])

    content_mismatches = []
    
    for r1, r2 in h_merges:
        stt = rows.get(r1, {}).get('A', {}).get('val', '')
        so_hieu = rows.get(r1, {}).get('B', {}).get('val', '')
        h_text = rows.get(r1, {}).get('H', {}).get('val', '').strip()
        
        h_du_match = re.search(r'- Dư\s*\((\d+)\):', h_text)
        h_thieu_match = re.search(r'- Thiếu\s*\((\d+)\):', h_text)
        
        h_du_items = []
        if h_du_match:
            du_part = h_text[h_du_match.end():]
            if '- Thiếu' in du_part:
                du_part = du_part[:du_part.index('- Thiếu')]
            h_du_items = [line.strip()[2:].strip() for line in du_part.split('\n') if line.strip().startswith('+')]
            
        h_thieu_items = []
        if h_thieu_match:
            thieu_part = h_text[h_thieu_match.end():]
            if '- Ngoại lệ' in thieu_part:
                thieu_part = thieu_part[:thieu_part.index('- Ngoại lệ')]
            h_thieu_items = [line.strip()[2:].strip() for line in thieu_part.split('\n') if line.strip().startswith('+')]

        # Actual items from sheet
        yellow_e_vals = []
        red_g_vals = []
        exception_g_vals = []
        
        for r in range(r1, r2 + 1):
            g_cell = rows.get(r, {}).get('G', {})
            e_cell = rows.get(r, {}).get('E', {})
            fill = g_cell.get('fill')
            font = g_cell.get('font')
            g_val = g_cell.get('val', '').strip()
            e_val = e_cell.get('val', '').strip()
            
            if fill == 'FFFFEB9C':
                yellow_e_vals.append(e_val)
            elif fill == 'FFFFC7CE':
                red_g_vals.append(g_val)
            elif font == 'FFFF0000':
                exception_g_vals.append(g_val)
                
        # Compare set of unique yellow items vs h_du_items
        set_yellow = set(yellow_e_vals)
        set_h_du = set(h_du_items)
        
        set_red = set(red_g_vals)
        set_h_thieu = set(h_thieu_items)
        
        # Check differences
        du_in_h_not_in_yellow = set_h_du - set_yellow
        du_in_yellow_not_in_h = set_yellow - set_h_du
        
        thieu_in_h_not_in_red = set_h_thieu - set_red
        thieu_in_red_not_in_h = set_red - set_h_thieu
        
        if du_in_h_not_in_yellow or du_in_yellow_not_in_h or thieu_in_h_not_in_red or thieu_in_red_not_in_h:
            content_mismatches.append({
                'stt': stt,
                'so_hieu': so_hieu,
                'range': f"{r1}-{r2}",
                'h_du_count': len(h_du_items),
                'act_yellow_count': len(yellow_e_vals),
                'act_yellow_unique': len(set_yellow),
                'h_thieu_count': len(h_thieu_items),
                'act_red_count': len(red_g_vals),
                'act_exception_count': len(exception_g_vals),
                'du_in_h_not_in_yellow': list(du_in_h_not_in_yellow),
                'du_in_yellow_not_in_h': list(du_in_yellow_not_in_h),
                'thieu_in_h_not_in_red': list(thieu_in_h_not_in_red),
                'thieu_in_red_not_in_h': list(thieu_in_red_not_in_h)
            })

    print(f"Total content/set mismatches: {len(content_mismatches)}")
    
    # Check if there are any documents with content mismatch that were NOT in the 58
    # What are the STTs?
    with open('content_mismatches.json', 'w', encoding='utf-8') as f:
        json.dump(content_mismatches, f, ensure_ascii=False, indent=2)
        
    print("STTs of content mismatches:")
    for cm in content_mismatches:
        print(f"STT {cm['stt']} ({cm['so_hieu']}): H_du={cm['h_du_count']} vs Y={cm['act_yellow_count']} (uniq {cm['act_yellow_unique']}) | H_th={cm['h_thieu_count']} vs R={cm['act_red_count']} (Ex={cm['act_exception_count']})")
        if cm['du_in_h_not_in_yellow']:
            print(f"   Dư in H but NOT yellow: {cm['du_in_h_not_in_yellow']}")
        if cm['du_in_yellow_not_in_h']:
            print(f"   Dư in yellow but NOT H: {cm['du_in_yellow_not_in_h']}")
        if cm['thieu_in_h_not_in_red']:
            print(f"   Thiếu in H but NOT red: {cm['thieu_in_h_not_in_red']}")
        if cm['thieu_in_red_not_in_h']:
            print(f"   Thiếu in red but NOT H: {cm['thieu_in_red_not_in_h']}")

if __name__ == '__main__':
    check_unit_name_mismatches()
