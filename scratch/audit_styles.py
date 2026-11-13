import zipfile
import xml.etree.ElementTree as ET
import re
from collections import Counter

def run_styles_audit():
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

    # Check row 1 (header)
    print("Row 1 Header:")
    for col in ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']:
        print(f"  Col {col}: {rows.get(1, {}).get(col, {}).get('val')}")

    # Styles in Column G across rows 2..18321
    g_styles = Counter()
    style_samples = {}
    for r in range(2, 18322):
        g_cell = rows.get(r, {}).get('G', {})
        fill = g_cell.get('fill')
        font = g_cell.get('font')
        val = g_cell.get('val', '')
        key = (fill, font)
        g_styles[key] += 1
        if key not in style_samples:
            style_samples[key] = (r, val, rows.get(r, {}).get('E', {}).get('val', ''))

    print("\nDistinct Column G styles across rows 2..18321:")
    for key, count in g_styles.most_common():
        sample = style_samples[key]
        print(f"Style (Fill: {key[0]}, Font: {key[1]}): {count} cells | Sample row {sample[0]}: G='{sample[1]}', E='{sample[2]}'")

if __name__ == '__main__':
    run_styles_audit()
