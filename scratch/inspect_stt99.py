import zipfile
import xml.etree.ElementTree as ET
import re

def inspect_stt_99():
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
        
        print("=== ROWS 4019 - 4032 (STT 99) ===")
        for row in sh_root.findall('.//ns:sheetData/ns:row', ns):
            r_idx = int(row.get('r'))
            if 4019 <= r_idx <= 4032:
                r_data = {}
                for c in row.findall('ns:c', ns):
                    ref = c.get('r')
                    col = re.match(r'([A-Z]+)', ref).group(1)
                    s_idx = int(c.get('s', 0))
                    t = c.get('t')
                    v_elem = c.find('ns:v', ns)
                    val = ""
                    if v_elem is not None and v_elem.text:
                        val = shared_strings[int(v_elem.text)] if t == 's' else v_elem.text
                    fill = fills[cell_xfs[s_idx]['fillId']]
                    font = fonts[cell_xfs[s_idx]['fontId']]
                    r_data[col] = (val, fill, font)
                print(f"Row {r_idx}:")
                for col in ['D', 'E', 'F', 'G', 'H']:
                    if col in r_data:
                        print(f"  Col {col}: val='{r_data[col][0]}', fill={r_data[col][1]}, font={r_data[col][2]}")

if __name__ == '__main__':
    inspect_stt_99()
