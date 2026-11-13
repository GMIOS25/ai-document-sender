import zipfile
import xml.etree.ElementTree as ET

def main():
    with zipfile.ZipFile('test4_export.xlsx', 'r') as z:
        styles_xml = z.read('xl/styles.xml')
        root = ET.fromstring(styles_xml)
        ns = {'ns': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
        
        print('--- FILLS ---')
        fills = root.findall('.//ns:fills/ns:fill', ns)
        for i, f in enumerate(fills):
            pat = f.find('ns:patternFill', ns)
            if pat is not None:
                fg = pat.find('ns:fgColor', ns)
                bg = pat.find('ns:bgColor', ns)
                fg_str = fg.attrib if fg is not None else None
                bg_str = bg.attrib if bg is not None else None
                print(f'Fill {i}: {pat.get("patternType")}, fg={fg_str}, bg={bg_str}')
                
        print('--- FONTS ---')
        fonts = root.findall('.//ns:fonts/ns:font', ns)
        for i, font in enumerate(fonts):
            color = font.find('ns:color', ns)
            c_str = color.attrib if color is not None else None
            name = font.find('ns:name', ns)
            n_str = name.get('val') if name is not None else None
            print(f'Font {i}: color={c_str}, name={n_str}')

        print('--- CELLXFS ---')
        cell_xfs = root.findall('.//ns:cellXfs/ns:xf', ns)
        for i, xf in enumerate(cell_xfs):
            font_id = xf.get('fontId')
            fill_id = xf.get('fillId')
            apply_fill = xf.get('applyFill')
            apply_font = xf.get('applyFont')
            print(f'XF {i}: fontId={font_id}, fillId={fill_id}, applyFill={apply_fill}, applyFont={apply_font}')

if __name__ == '__main__':
    main()
