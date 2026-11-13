import zipfile
import xml.etree.ElementTree as ET
import re

def verify_doc_metadata():
    with zipfile.ZipFile('test4_export.xlsx', 'r') as z:
        sst_xml = z.read('xl/sharedStrings.xml')
        sst_root = ET.fromstring(sst_xml)
        ns = {'ns': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
        
        shared_strings = []
        for si in sst_root.findall('ns:si', ns):
            texts = [t.text for t in si.findall('.//ns:t', ns) if t.text]
            shared_strings.append("".join(texts))
            
        sheet_xml = z.read('xl/worksheets/sheet1.xml')
        sh_root = ET.fromstring(sheet_xml)
        
        test_rows = [342, 518, 4746, 5867, 6154, 6628, 6905, 7085, 7266, 7590, 7836, 8017, 8902, 9334, 9673, 9839, 12973, 13163, 13318, 13499, 13845, 14002, 14301, 14468, 15003, 15541, 15811, 18147]
        
        for row in sh_root.findall('.//ns:sheetData/ns:row', ns):
            r_idx = int(row.get('r'))
            if r_idx in test_rows:
                a_val, b_val, c_val = "", "", ""
                for c in row.findall('ns:c', ns):
                    ref = c.get('r')
                    t = c.get('t')
                    v_elem = c.find('ns:v', ns)
                    val = ""
                    if v_elem is not None and v_elem.text:
                        val = shared_strings[int(v_elem.text)] if t == 's' else v_elem.text
                    if ref.startswith(f'A{r_idx}'): a_val = val
                    elif ref.startswith(f'B{r_idx}'): b_val = val
                    elif ref.startswith(f'C{r_idx}'): c_val = val
                print(f"Row {r_idx}: STT(A)='{a_val}', Số hiệu(B)='{b_val}', Trích yếu(C)='{c_val[:40]}...'")

if __name__ == '__main__':
    verify_doc_metadata()
