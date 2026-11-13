import zipfile
import xml.etree.ElementTree as ET
import re
from collections import Counter

def check_red_duplicates():
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

    red_dup_docs = []
    for r1, r2 in h_merges:
        red_vals = []
        for r in range(r1, r2 + 1):
            g = rows.get(r, {}).get('G', {})
            if g.get('fill') == 'FFFFC7CE':
                red_vals.append(g.get('val', '').strip())
        c = Counter(red_vals)
        dups = {k: v for k, v in c.items() if v > 1}
        if dups:
            red_dup_docs.append((r1, r2, dups))
            
    print(f"Docs with duplicate RED cells: {len(red_dup_docs)}")
    for r1, r2, dups in red_dup_docs:
        print(f"  Range {r1}-{r2}: {dups}")

if __name__ == '__main__':
    check_red_duplicates()
