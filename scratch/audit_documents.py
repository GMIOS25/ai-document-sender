import zipfile
import xml.etree.ElementTree as ET
import re
from collections import Counter
import json

def audit_documents():
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
        
        # Merge cells
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

    # Parse merges for H
    h_merges = []
    for m in merge_cells:
        m_match = re.match(r'^H(\d+):H(\d+)$', m)
        if m_match:
            r1, r2 = int(m_match.group(1)), int(m_match.group(2))
            h_merges.append((r1, r2))
    h_merges = sorted(h_merges, key=lambda x: x[0])

    print(f"Total documents (H merges): {len(h_merges)}")
    
    docs = []
    total_h_reported_du = 0
    total_h_reported_thieu = 0
    total_h_reported_ngoai_le = 0
    
    total_actual_green = 0
    total_actual_yellow = 0
    total_actual_red = 0
    total_actual_exception = 0
    
    mismatched_docs = []
    
    for r1, r2 in h_merges:
        stt = rows.get(r1, {}).get('A', {}).get('val', '')
        so_hieu = rows.get(r1, {}).get('B', {}).get('val', '')
        h_text = rows.get(r1, {}).get('H', {}).get('val', '').strip()
        
        # Parse H text
        # Format can be:
        # "Đầy đủ (Khớp hoàn toàn như kết quả đích)"
        # Or:
        # - Dư (26):
        #   + ...
        # - Thiếu (2):
        #   + ...
        h_du_match = re.search(r'- Dư\s*\((\d+)\):', h_text)
        h_thieu_match = re.search(r'- Thiếu\s*\((\d+)\):', h_text)
        h_ngoai_le_match = re.search(r'- Ngoại lệ\s*\((\d+)\):', h_text, re.IGNORECASE)
        
        h_du_count = int(h_du_match.group(1)) if h_du_match else 0
        h_thieu_count = int(h_thieu_match.group(1)) if h_thieu_match else 0
        h_ngoai_le_count = int(h_ngoai_le_match.group(1)) if h_ngoai_le_match else 0
        
        # Extract items listed in H
        # For Dư
        h_du_items = []
        if h_du_match:
            # find text between Dư and Thiếu or end
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

        total_h_reported_du += h_du_count
        total_h_reported_thieu += h_thieu_count
        total_h_reported_ngoai_le += h_ngoai_le_count
        
        # Actual styles in range r1..r2
        actual_green = 0
        actual_yellow = 0
        actual_red = 0
        actual_exception = 0
        
        yellow_rows = []
        red_rows = []
        exception_rows = []
        green_rows = []
        
        for r in range(r1, r2 + 1):
            g_cell = rows.get(r, {}).get('G', {})
            e_cell = rows.get(r, {}).get('E', {})
            fill = g_cell.get('fill')
            font = g_cell.get('font')
            g_val = g_cell.get('val', '')
            e_val = e_cell.get('val', '')
            
            if fill == 'FFC6EFCE':
                actual_green += 1
                green_rows.append((r, e_val, g_val))
            elif fill == 'FFFFEB9C':
                actual_yellow += 1
                yellow_rows.append((r, e_val, g_val))
            elif fill == 'FFFFC7CE':
                actual_red += 1
                red_rows.append((r, e_val, g_val))
            elif font == 'FFFF0000':
                actual_exception += 1
                exception_rows.append((r, e_val, g_val))
            else:
                print(f"UNKNOWN STYLE at row {r}: fill={fill}, font={font}")
                
        total_actual_green += actual_green
        total_actual_yellow += actual_yellow
        total_actual_red += actual_red
        total_actual_exception += actual_exception
        
        is_mismatch = (h_du_count != actual_yellow) or (h_thieu_count != actual_red) or (h_ngoai_le_count != actual_exception)
        
        doc_info = {
            'stt': stt,
            'so_hieu': so_hieu,
            'range': f"{r1}-{r2}",
            'r1': r1,
            'r2': r2,
            'h_text': h_text,
            'h_du': h_du_count,
            'h_thieu': h_thieu_count,
            'h_ngoai_le': h_ngoai_le_count,
            'h_du_items': h_du_items,
            'h_thieu_items': h_thieu_items,
            'actual_green': actual_green,
            'actual_yellow': actual_yellow,
            'actual_red': actual_red,
            'actual_exception': actual_exception,
            'yellow_rows': yellow_rows,
            'red_rows': red_rows,
            'exception_rows': exception_rows,
            'is_mismatch': is_mismatch
        }
        docs.append(doc_info)
        if is_mismatch:
            mismatched_docs.append(doc_info)

    print("\n--- OVERALL TOTALS ---")
    print(f"Total Actual Green:     {total_actual_green}")
    print(f"Total Actual Yellow:    {total_actual_yellow}")
    print(f"Total Actual Red:       {total_actual_red}")
    print(f"Total Actual Exception: {total_actual_exception}")
    print(f"Sum Actual:             {total_actual_green + total_actual_yellow + total_actual_red + total_actual_exception}")
    print(f"Total H Reported Dư:        {total_h_reported_du}")
    print(f"Total H Reported Thiếu:     {total_h_reported_thieu}")
    print(f"Total H Reported Ngoại lệ:  {total_h_reported_ngoai_le}")
    print(f"Delta Dư (Actual - H):      {total_actual_yellow - total_h_reported_du}")
    print(f"Delta Thiếu (H - Actual):   {total_h_reported_thieu - total_actual_red}")
    print(f"Delta Ngoại lệ (Actual - H):{total_actual_exception - total_h_reported_ngoai_le}")
    print(f"Total Mismatched Documents: {len(mismatched_docs)}")
    
    # Save mismatched docs details to json for detailed analysis
    with open('mismatched_docs.json', 'w', encoding='utf-8') as f:
        # Simplify rows before dump
        dump_data = []
        for d in mismatched_docs:
            dump_data.append({
                'stt': d['stt'],
                'so_hieu': d['so_hieu'],
                'range': d['range'],
                'h_du': d['h_du'],
                'act_yellow': d['actual_yellow'],
                'h_thieu': d['h_thieu'],
                'act_red': d['actual_red'],
                'h_ngoai_le': d['h_ngoai_le'],
                'act_exception': d['actual_exception'],
                'yellow_diff': d['actual_yellow'] - d['h_du'],
                'thieu_diff': d['h_thieu'] - d['actual_red'],
                'exception_diff': d['actual_exception'] - d['h_ngoai_le'],
                'h_du_items_len': len(d['h_du_items']),
                'h_thieu_items_len': len(d['h_thieu_items']),
                'yellow_units': [y[1] for y in d['yellow_rows']],
                'red_units': [r[2] for r in d['red_rows']],
                'exception_units': [(e[0], e[2]) for e in d['exception_rows']]
            })
        json.dump(dump_data, f, ensure_ascii=False, indent=2)

if __name__ == '__main__':
    audit_documents()
