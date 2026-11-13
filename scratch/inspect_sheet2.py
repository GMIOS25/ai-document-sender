import zipfile
import xml.etree.ElementTree as ET

def inspect_sheet2():
    with zipfile.ZipFile('test4_export.xlsx', 'r') as z:
        sst_xml = z.read('xl/sharedStrings.xml')
        sst_root = ET.fromstring(sst_xml)
        ns = {'ns': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
        
        shared_strings = []
        for si in sst_root.findall('ns:si', ns):
            texts = [t.text for t in si.findall('.//ns:t', ns) if t.text]
            shared_strings.append("".join(texts))

        sheet2_xml = z.read('xl/worksheets/sheet2.xml')
        sh2_root = ET.fromstring(sheet2_xml)
        
        rows = []
        for row in sh2_root.findall('.//ns:sheetData/ns:row', ns):
            r_idx = int(row.get('r'))
            if r_idx > 5: break
            row_text = []
            for c in row.findall('ns:c', ns):
                t = c.get('t')
                v_elem = c.find('ns:v', ns)
                val = ""
                if v_elem is not None and v_elem.text:
                    val = shared_strings[int(v_elem.text)] if t == 's' else v_elem.text
                row_text.append(f"{c.get('r')}: {val}")
            print(f"Sheet 2 Row {r_idx}: {row_text[:6]}")

if __name__ == '__main__':
    inspect_sheet2()
