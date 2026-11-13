import zipfile
import xml.etree.ElementTree as ET
import re

def analyze():
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
        
        # Parse rows
        rows = {}
        for row in sh_root.findall('.//ns:sheetData/ns:row', ns):
            r_idx = int(row.get('r'))
            row_data = {}
            for c in row.findall('ns:c', ns):
                ref = c.get('r') # e.g. "G342"
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

        print(f"Total rows parsed: {len(rows)}")

        # Check H342 - H517
        print("=== Checking H342 - H517 ===")
        h342_text = rows[342].get('H', {}).get('val', '')
        print("H342 text:")
        print(h342_text)
        
        g_styles_342 = {}
        for r in range(342, 518):
            g_cell = rows.get(r, {}).get('G', {})
            fill = g_cell.get('fill')
            font = g_cell.get('font')
            val = g_cell.get('val', '')
            e_val = rows.get(r, {}).get('E', {}).get('val', '')
            key = (fill, font)
            g_styles_342[key] = g_styles_342.get(key, 0) + 1
            if fill in ['FFFFEB9C', 'FFFFF4D8']: # Yellow
                pass
            elif fill in ['FFFFC7CE']: # Red
                print(f"Row {r} RED: G='{val}' | E='{e_val}'")
            elif font in ['FFFF0000']: # Red font
                print(f"Row {r} RED FONT: fill={fill}, G='{val}' | E='{e_val}'")
                
        print("G styles count in 342-517:", g_styles_342)

        # Check H518 - H765
        print("\n=== Checking H518 - H765 ===")
        h518_text = rows[518].get('H', {}).get('val', '')
        print("H518 text:")
        print(h518_text)
        
        g_styles_518 = {}
        for r in range(518, 766):
            g_cell = rows.get(r, {}).get('G', {})
            fill = g_cell.get('fill')
            font = g_cell.get('font')
            val = g_cell.get('val', '')
            e_val = rows.get(r, {}).get('E', {}).get('val', '')
            key = (fill, font)
            g_styles_518[key] = g_styles_518.get(key, 0) + 1
            if fill in ['FFFFC7CE']: # Red
                print(f"Row {r} RED: G='{val}' | E='{e_val}'")
            elif font in ['FFFF0000']: # Red font
                print(f"Row {r} RED FONT: fill={fill}, G='{val}' | E='{e_val}'")
                
        print("G styles count in 518-765:", g_styles_518)

if __name__ == '__main__':
    analyze()
