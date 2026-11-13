import zipfile
import xml.etree.ElementTree as ET

with zipfile.ZipFile('test4_export.xlsx', 'r') as z:
    sst_xml = z.read('xl/sharedStrings.xml')
    sst_root = ET.fromstring(sst_xml)
    ns = {'ns': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    shared_strings = [''.join([t.text for t in si.findall('.//ns:t', ns) if t.text]) for si in sst_root.findall('ns:si', ns)]
    
    sheet_xml = z.read('xl/worksheets/sheet1.xml')
    sh_root = ET.fromstring(sheet_xml)
    
    styles_xml = z.read('xl/styles.xml')
    s_root = ET.fromstring(styles_xml)
    fills = [f.find('ns:patternFill/ns:fgColor', ns).get('rgb') if f.find('ns:patternFill/ns:fgColor', ns) is not None else None for f in s_root.findall('.//ns:fills/ns:fill', ns)]
    cell_xfs = [{'fillId': int(xf.get('fillId', 0))} for xf in s_root.findall('.//ns:cellXfs/ns:xf', ns)]

    yellow_rows = []
    for r in sh_root.findall('.//ns:sheetData/ns:row', ns):
        r_num = int(r.get('r'))
        if 518 <= r_num <= 765:
            e_val, g_fill = '', ''
            for c in r.findall('ns:c', ns):
                col = ''.join([ch for ch in c.get('r') if ch.isalpha()])
                s = int(c.get('s', 0))
                fill = fills[cell_xfs[s]['fillId']] if s < len(cell_xfs) else None
                v = c.find('ns:v', ns)
                val = ''
                if v is not None and v.text:
                    val = shared_strings[int(v.text)] if c.get('t') == 's' else v.text
                if col == 'E':
                    e_val = val
                elif col == 'G':
                    g_fill = fill
            if g_fill == 'FFFFEB9C':
                yellow_rows.append((r_num, e_val))

print(f"Total yellow: {len(yellow_rows)}")
for i, (r_num, e_val) in enumerate(yellow_rows, 1):
    print(f"{i:2d} | Row {r_num} | {e_val}")
