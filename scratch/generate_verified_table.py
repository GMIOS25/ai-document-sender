import zipfile
import xml.etree.ElementTree as ET
import re
import json

def generate_verified_58_table():
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

    mismatched = []
    for r1, r2 in h_merges:
        stt_val = rows.get(r1, {}).get('A', {}).get('val', '')
        try:
            stt = int(float(stt_val))
        except:
            stt = stt_val
            
        so_hieu = rows.get(r1, {}).get('B', {}).get('val', '')
        trich_yeu = rows.get(r1, {}).get('C', {}).get('val', '')
        h_text = rows.get(r1, {}).get('H', {}).get('val', '').strip()
        
        h_du_match = re.search(r'- Dư\s*\((\d+)\):', h_text)
        h_thieu_match = re.search(r'- Thiếu\s*\((\d+)\):', h_text)
        h_ngoai_le_match = re.search(r'- Ngoại lệ\s*\((\d+)\):', h_text, re.IGNORECASE)
        
        h_du = int(h_du_match.group(1)) if h_du_match else 0
        h_thieu = int(h_thieu_match.group(1)) if h_thieu_match else 0
        h_ngoai_le = int(h_ngoai_le_match.group(1)) if h_ngoai_le_match else 0
        
        # Actuals
        yellow_rows = []
        red_rows = []
        exc_rows = []
        for r in range(r1, r2 + 1):
            g = rows.get(r, {}).get('G', {})
            e = rows.get(r, {}).get('E', {})
            if g.get('fill') == 'FFFFEB9C':
                yellow_rows.append((r, e.get('val', '').strip()))
            elif g.get('fill') == 'FFFFC7CE':
                red_rows.append((r, g.get('val', '').strip()))
            elif g.get('font') == 'FFFF0000':
                exc_rows.append((r, g.get('val', '').strip()))

        is_mismatch = (h_du != len(yellow_rows)) or (h_thieu != len(red_rows)) or (h_ngoai_le != len(exc_rows))
        if is_mismatch:
            # Determine group
            # Group 1: Only exception lumped into Thiếu (Act_ex == 1, H_thieu == Act_r + 1, H_du == Act_y)
            # Group 2: Fuzzy match dropped both (Act_ex == 1, Yellow missing in H matches Exc)
            # Group 3: Deduplication in Yellow
            # Group 4: STT 99 (H_du == 1, Act_y == 0)
            
            # Check duplicate yellow items
            from collections import Counter
            c_y = Counter([y[1] for y in yellow_rows])
            dups = {k: v for k, v in c_y.items() if v > 1}
            num_dup_rows = sum(v - 1 for v in dups.values())
            
            grp = ""
            details = {}
            if stt == 99:
                grp = "Nhóm 4 (Ghi sai Dư dù bảng tính 100% xanh)"
            elif len(exc_rows) > 0 and h_thieu == len(red_rows) + 1 and h_du == len(yellow_rows):
                grp = "Nhóm 1 (Gom ô Ngoại lệ vào Thiếu)"
            elif len(exc_rows) > 0 and h_du < len(yellow_rows) and h_thieu == len(red_rows):
                grp = "Nhóm 2 (Khớp mờ bỏ sót Dư & Ngoại lệ)"
            elif len(exc_rows) == 0 and num_dup_rows > 0 and h_du == len(yellow_rows) - num_dup_rows:
                grp = "Nhóm 3 (Khử trùng lặp dòng Vàng)"
            elif stt == 308:
                grp = "Hỗn hợp: Nhóm 1 + Nhóm 3 (Gom Ngoại lệ vào Thiếu VÀ Khử trùng lặp dòng Vàng)"
            else:
                grp = "Khác"
                
            mismatched.append({
                'stt': stt,
                'so_hieu': so_hieu,
                'range': f"{r1}-{r2}",
                'r1': r1,
                'r2': r2,
                'group': grp,
                'h_du': h_du,
                'act_y': len(yellow_rows),
                'h_thieu': h_thieu,
                'act_r': len(red_rows),
                'act_ex': len(exc_rows),
                'exc_item': exc_rows[0] if exc_rows else None,
                'dup_items': dups,
                'num_dup_rows': num_dup_rows
            })

    print(f"Total mismatched docs: {len(mismatched)}")
    group_counts = Counter([m['group'] for m in mismatched])
    for grp, cnt in group_counts.items():
        print(f"  {grp}: {cnt}")
        
    with open('verified_58_docs.json', 'w', encoding='utf-8') as f:
        json.dump(mismatched, f, ensure_ascii=False, indent=2)

if __name__ == '__main__':
    generate_verified_58_table()
