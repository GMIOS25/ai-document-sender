import zipfile
import xml.etree.ElementTree as ET
import re

with zipfile.ZipFile(r'C:\Workspaces\Script-Idesk Sender\test4_export.xlsx', 'r') as z:
    sst_root = ET.fromstring(z.read('xl/sharedStrings.xml'))
    ns = {'ns': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    shared_strings = [''.join(t.text for t in si.findall('.//ns:t', ns) if t.text) for si in sst_root.findall('ns:si', ns)]
    styles_root = ET.fromstring(z.read('xl/styles.xml'))
    fills = [f.find('ns:patternFill/ns:fgColor', ns).get('rgb') if f.find('ns:patternFill/ns:fgColor', ns) is not None else None for f in styles_root.findall('.//ns:fills/ns:fill', ns)]
    fonts = [font.find('ns:color', ns).get('rgb') if font.find('ns:color', ns) is not None else None for font in styles_root.findall('.//ns:fonts/ns:font', ns)]
    cell_xfs = [{'fontId': int(xf.get('fontId', 0)), 'fillId': int(xf.get('fillId', 0))} for xf in styles_root.findall('.//ns:cellXfs/ns:xf', ns)]
    sh_root = ET.fromstring(z.read('xl/worksheets/sheet1.xml'))
    
    target_rows = set(range(342, 346)) | set(range(514, 518))
    for row in sh_root.findall('.//ns:sheetData/ns:row', ns):
        r_idx = int(row.get('r'))
        if r_idx in target_rows:
            row_data = {}
            for c in row.findall('ns:c', ns):
                ref = c.get('r')
                col = re.match(r'([A-Z]+)', ref).group(1)
                s_idx = int(c.get('s', 0))
                t = c.get('t')
                v_elem = c.find('ns:v', ns)
                val = shared_strings[int(v_elem.text)] if (v_elem is not None and t == 's') else (v_elem.text if v_elem is not None else '')
                row_data[col] = (val, fills[cell_xfs[s_idx]['fillId']], fonts[cell_xfs[s_idx]['fontId']])
            print(f'Row {r_idx}:')
            print('  E (Nơi nhận 2):', row_data.get('E'))
            print('  G (Đích):', row_data.get('G'))
