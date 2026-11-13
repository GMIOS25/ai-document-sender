import zipfile
import xml.etree.ElementTree as ET
import re

def check_truncated_origins():
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

        sheet1_xml = z.read('xl/worksheets/sheet1.xml')
        sh1_root = ET.fromstring(sheet1_xml)
        
        # Find all 53 exception cells in sheet 1
        exceptions = []
        for row in sh1_root.findall('.//ns:sheetData/ns:row', ns):
            r_idx = int(row.get('r'))
            for c in row.findall('ns:c', ns):
                ref = c.get('r')
                if ref.startswith(f'G{r_idx}'):
                    s_idx = int(c.get('s', 0))
                    font = fonts[cell_xfs[s_idx]['fontId']]
                    if font == 'FFFF0000':
                        t = c.get('t')
                        v_elem = c.find('ns:v', ns)
                        val = ""
                        if v_elem is not None and v_elem.text:
                            val = shared_strings[int(v_elem.text)] if t == 's' else v_elem.text
                        exceptions.append((r_idx, val))

        print(f"Total exception cells in Sheet 1: {len(exceptions)}")
        print("Sample 10 exceptions:")
        for r, val in exceptions[:10]:
            print(f"  Row {r}: '{val}'")

        # Now check Sheet 7 (Kết quả đích thực tế)
        sheet7_xml = z.read('xl/worksheets/sheet7.xml')
        sh7_root = ET.fromstring(sheet7_xml)
        
        # Collect all text in Sheet 7
        sheet7_text = []
        for row in sh7_root.findall('.//ns:sheetData/ns:row', ns):
            r_idx = int(row.get('r'))
            for c in row.findall('ns:c', ns):
                t = c.get('t')
                v_elem = c.find('ns:v', ns)
                val = ""
                if v_elem is not None and v_elem.text:
                    val = shared_strings[int(v_elem.text)] if t == 's' else v_elem.text
                if val:
                    sheet7_text.append((r_idx, c.get('r'), val))

        print(f"Total text cells in Sheet 7: {len(sheet7_text)}")
        
        # Check how many of the 53 exceptions exist verbatim in Sheet 7!
        matched_in_sheet7 = 0
        for r, exc_val in exceptions:
            found = False
            for r7, cell_ref, text7 in sheet7_text:
                if exc_val in text7:
                    found = True
                    break
            if found:
                matched_in_sheet7 += 1
            else:
                print(f"Not found in Sheet 7: Row {r} '{exc_val}'")
                
        print(f"Exceptions found verbatim in Sheet 7: {matched_in_sheet7} / {len(exceptions)}")

if __name__ == '__main__':
    check_truncated_origins()
