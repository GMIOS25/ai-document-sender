import zipfile
import xml.etree.ElementTree as ET

def parse_sheet():
    with zipfile.ZipFile('test4_export.xlsx', 'r') as z:
        # Load shared strings
        sst_xml = z.read('xl/sharedStrings.xml')
        sst_root = ET.fromstring(sst_xml)
        ns = {'ns': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
        
        shared_strings = []
        for si in sst_root.findall('ns:si', ns):
            # could be t or r/t
            texts = [t.text for t in si.findall('.//ns:t', ns) if t.text]
            shared_strings.append("".join(texts))
            
        print(f"Total shared strings: {len(shared_strings)}")

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

        print("Fills:", fills)
        
        # Load sheet1.xml
        sheet_xml = z.read('xl/worksheets/sheet1.xml')
        sh_root = ET.fromstring(sheet_xml)
        
        # Get merge cells
        merge_cells = []
        for mc in sh_root.findall('.//ns:mergeCells/ns:mergeCell', ns):
            merge_cells.append(mc.get('ref'))
        print(f"Total merge cells: {len(merge_cells)}")
        
        # Check merge cells for Col H
        h_merges = [m for m in merge_cells if m.startswith('H') or ':H' in m or ('A' in m and 'H' in m)]
        print(f"Sample H merges: {h_merges[:10]}")
        
if __name__ == '__main__':
    parse_sheet()
