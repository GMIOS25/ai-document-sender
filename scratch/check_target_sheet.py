import zipfile
import xml.etree.ElementTree as ET
import re

def check_target_sheet():
    with zipfile.ZipFile('test4_export.xlsx', 'r') as z:
        sst_xml = z.read('xl/sharedStrings.xml')
        sst_root = ET.fromstring(sst_xml)
        ns = {'ns': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
        
        shared_strings = []
        for si in sst_root.findall('ns:si', ns):
            texts = [t.text for t in si.findall('.//ns:t', ns) if t.text]
            shared_strings.append("".join(texts))

        # Check sheet7.xml (Kết quả đích thực tế)
        sheet_xml = z.read('xl/worksheets/sheet7.xml')
        sh_root = ET.fromstring(sheet_xml)
        
        # Search for 13013/UBND-NC or row with 13013
        for row in sh_root.findall('.//ns:sheetData/ns:row', ns):
            r_idx = int(row.get('r'))
            row_text = []
            for c in row.findall('ns:c', ns):
                t = c.get('t')
                v_elem = c.find('ns:v', ns)
                val = ""
                if v_elem is not None and v_elem.text:
                    val = shared_strings[int(v_elem.text)] if t == 's' else v_elem.text
                row_text.append(val)
            full_row = " | ".join(row_text)
            if '13013' in full_row:
                print(f"Sheet7 Row {r_idx}: {full_row}")

if __name__ == '__main__':
    check_target_sheet()
