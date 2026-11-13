import zipfile
import xml.etree.ElementTree as ET
import re
import json

def run_audit():
    with zipfile.ZipFile('test4_export.xlsx', 'r') as z:
        # Load shared strings
        sst_xml = z.read('xl/sharedStrings.xml')
        sst_root = ET.fromstring(sst_xml)
        ns = {'ns': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
        
        shared_strings = []
        for si in sst_root.findall('ns:si', ns):
            texts = [t.text for t in si.findall('.//ns:t', ns) if t.text]
            shared_strings.append("".join(texts))
            
        # Load styles
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

        # Load sheet1.xml
        sheet_xml = z.read('xl/worksheets/sheet1.xml')
        sh_root = ET.fromstring(sheet_xml)
        
        # Get merge cells
        merge_cells = []
        for mc in sh_root.findall('.//ns:mergeCells/ns:mergeCell', ns):
            merge_cells.append(mc.get('ref'))
            
        # Parse rows
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

    # Map merges for Column A (Doc STT) or Column H
    # Let's inspect all merge ranges for H or A
    doc_ranges = []
    # Find all merge cells in column H or A
    for m in merge_cells:
        m_match = re.match(r'([A-Z]+)(\d+):([A-Z]+)(\d+)', m)
        if m_match:
            c1, r1, c2, r2 = m_match.groups()
            r1, r2 = int(r1), int(r2)
            if c1 == 'H' and c2 == 'H':
                doc_ranges.append((r1, r2))
            elif c1 == 'A' and c2 == 'A':
                # some might not have H merge if 1 row?
                pass

    # Sort doc ranges by start row
    doc_ranges = sorted(doc_ranges, key=lambda x: x[0])
    
    # Check if there are non-merged single row docs or if all rows 2..18321 are covered
    covered_rows = set()
    for r1, r2 in doc_ranges:
        for r in range(r1, r2 + 1):
            covered_rows.add(r)
            
    uncovered = []
    for r in range(2, 18322):
        if r not in covered_rows:
            uncovered.append(r)
            
    print(f"Total doc ranges from H merges: {len(doc_ranges)}")
    print(f"Uncovered rows in 2..18321: {len(uncovered)} (Sample: {uncovered[:10]})")
    
    # If uncovered rows exist, are they single-row docs?
    if uncovered:
        # Group contiguous uncovered rows
        single_docs = []
        curr = [uncovered[0]]
        for r in uncovered[1:]:
            if r == curr[-1] + 1:
                curr.append(r)
            else:
                single_docs.append(curr)
                curr = [r]
        single_docs.append(curr)
        print(f"Uncovered contiguous blocks: {len(single_docs)}")
        for b in single_docs[:5]:
            print(f"  Block {b[0]}..{b[-1]}: A='{rows.get(b[0], {}).get('A', {}).get('val')}', H='{rows.get(b[0], {}).get('H', {}).get('val')}'")

if __name__ == '__main__':
    run_audit()
