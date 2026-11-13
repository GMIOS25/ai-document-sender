import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

def check_ranges():
    xlsx_path = Path(r"C:\Workspaces\Script-Idesk Sender\test4_export.xlsx")
    with zipfile.ZipFile(xlsx_path, 'r') as z:
        sst_xml = z.read('xl/sharedStrings.xml')
        sst_root = ET.fromstring(sst_xml)
        ns = {'ns': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
        shared_strings = [''.join([t.text for t in si.findall('.//ns:t', ns) if t.text]) for si in sst_root.findall('ns:si', ns)]
        sheet_xml = z.read('xl/worksheets/sheet1.xml')
        sh_root = ET.fromstring(sheet_xml)

        print("=== ROWS 758 to 765 DETAILS ===")
        for r in sh_root.findall('.//ns:sheetData/ns:row', ns):
            r_num = int(r.get('r'))
            if 758 <= r_num <= 765:
                row_vals = {}
                for c in r.findall('ns:c', ns):
                    ref = c.get('r')
                    col = ''.join([ch for ch in ref if ch.isalpha()])
                    v_elem = c.find('ns:v', ns)
                    val = ''
                    if v_elem is not None and v_elem.text:
                        val = shared_strings[int(v_elem.text)] if c.get('t') == 's' else v_elem.text
                    row_vals[col] = val
                print(f"Row {r_num}: D='{row_vals.get('D','')}', E='{row_vals.get('E','')}', F='{row_vals.get('F','')}', G='{row_vals.get('G','')}'")

        print("\n=== ROWS 518 to 522 DETAILS ===")
        for r in sh_root.findall('.//ns:sheetData/ns:row', ns):
            r_num = int(r.get('r'))
            if 518 <= r_num <= 522:
                row_vals = {}
                for c in r.findall('ns:c', ns):
                    ref = c.get('r')
                    col = ''.join([ch for ch in ref if ch.isalpha()])
                    v_elem = c.find('ns:v', ns)
                    val = ''
                    if v_elem is not None and v_elem.text:
                        val = shared_strings[int(v_elem.text)] if c.get('t') == 's' else v_elem.text
                    row_vals[col] = val
                print(f"Row {r_num}: A='{row_vals.get('A','')}', B='{row_vals.get('B','')}', D='{row_vals.get('D','')}', E='{row_vals.get('E','')}', G='{row_vals.get('G','')}'")

if __name__ == '__main__':
    check_ranges()
