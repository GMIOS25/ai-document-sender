import zipfile
import xml.etree.ElementTree as ET
import re
from collections import Counter

def check_empty_green():
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
        
        empty_green_rows = []
        for row in sh_root.findall('.//ns:sheetData/ns:row', ns):
            r_idx = int(row.get('r'))
            if r_idx == 1: continue
            
            g_val, e_val, d_val, f_val = "", "", "", ""
            g_fill = None
            
            for c in row.findall('ns:c', ns):
                ref = c.get('r')
                col = re.match(r'([A-Z]+)', ref).group(1)
                s_idx = int(c.get('s', 0))
                t = c.get('t')
                v_elem = c.find('ns:v', ns)
                val = ""
                if v_elem is not None and v_elem.text:
                    val = shared_strings[int(v_elem.text)] if t == 's' else v_elem.text
                    
                if col == 'G':
                    g_val = val
                    g_fill = fills[cell_xfs[s_idx]['fillId']]
                elif col == 'E':
                    e_val = val
                elif col == 'D':
                    d_val = val
                elif col == 'F':
                    f_val = val
                    
            if g_fill == 'FFC6EFCE' and g_val.strip() == '':
                empty_green_rows.append((r_idx, d_val, e_val, f_val))

    print(f"Total empty green rows in Col G: {len(empty_green_rows)}")
    print("Sample 10 empty green rows (r, Col D, Col E, Col F):")
    for r, d, e, f in empty_green_rows[:10]:
        print(f"Row {r}: D='{d}' | E='{e}' | F='{f}'")
        
    e_counts = Counter([e for r, d, e, f in empty_green_rows])
    print("\nCounts of Column E for these empty green rows:")
    for e_v, cnt in e_counts.most_common(10):
        print(f"  '{e_v}': {cnt}")
        
    d_counts = Counter([d for r, d, e, f in empty_green_rows])
    print("\nCounts of Column D for these empty green rows:")
    for d_v, cnt in d_counts.most_common(10):
        print(f"  '{d_v}': {cnt}")

if __name__ == '__main__':
    check_empty_green()
