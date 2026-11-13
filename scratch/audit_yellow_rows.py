import zipfile
import xml.etree.ElementTree as ET
import json
import requests
from pathlib import Path

def run_deep_check():
    xlsx_path = Path(r"C:\Workspaces\Script-Idesk Sender\test4_export.xlsx")
    with zipfile.ZipFile(xlsx_path, 'r') as z:
        sst_xml = z.read('xl/sharedStrings.xml')
        sst_root = ET.fromstring(sst_xml)
        ns = {'ns': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
        shared_strings = [''.join([t.text for t in si.findall('.//ns:t', ns) if t.text]) for si in sst_root.findall('ns:si', ns)]
        
        sheet_xml = z.read('xl/worksheets/sheet1.xml')
        sh_root = ET.fromstring(sheet_xml)
        
        styles_xml = z.read('xl/styles.xml')
        s_root = ET.fromstring(styles_xml)
        fills = [f.find('ns:patternFill/ns:fgColor', ns).get('rgb') if f.find('ns:patternFill/ns:fgColor', ns) is not None else None for f in s_root.findall('.//ns:fills/ns:fill', ns)]
        fonts = [font.find('ns:color', ns).get('rgb') if font.find('ns:color', ns) is not None else None for font in s_root.findall('.//ns:fonts/ns:font', ns)]
        cell_xfs = [{'fontId': int(xf.get('fontId', 0)), 'fillId': int(xf.get('fillId', 0))} for xf in s_root.findall('.//ns:cellXfs/ns:xf', ns)]

        hidden_rows = []
        custom_height_rows = []
        all_rows = {}
        for r in sh_root.findall('.//ns:sheetData/ns:row', ns):
            r_num = int(r.get('r'))
            if 518 <= r_num <= 765:
                if r.get('hidden') == '1' or r.get('hidden') == 'true':
                    hidden_rows.append(r_num)
                ht = r.get('ht')
                if ht:
                    custom_height_rows.append((r_num, ht))
                row_dict = {}
                for c in r.findall('ns:c', ns):
                    cell_ref = c.get('r')
                    col_letter = ''.join([ch for ch in cell_ref if ch.isalpha()])
                    s_idx = int(c.get('s', 0))
                    v_elem = c.find('ns:v', ns)
                    val = ''
                    if v_elem is not None and v_elem.text:
                        val = shared_strings[int(v_elem.text)] if c.get('t') == 's' else v_elem.text
                    fill_color = fills[cell_xfs[s_idx]['fillId']] if s_idx < len(cell_xfs) else None
                    font_color = fonts[cell_xfs[s_idx]['fontId']] if s_idx < len(cell_xfs) else None
                    row_dict[col_letter] = {'val': val, 'fill': fill_color, 'font': font_color, 's': s_idx}
                all_rows[r_num] = row_dict

    print(f"Hidden rows in 518-765: {hidden_rows}")
    print(f"Total rows with custom height: {len(custom_height_rows)}")

    # Check yellow rows
    yellow_rows = []
    for r in range(518, 766):
        rd = all_rows.get(r, {})
        g = rd.get('G', {})
        if g.get('fill') == 'FFFFEB9C':
            yellow_rows.append((r, rd))

    print(f"Total yellow rows: {len(yellow_rows)}")
    
    # Check for duplicate names in Column E
    names = [rd.get('E', {}).get('val', '') for r, rd in yellow_rows]
    print(f"Unique names count: {len(set(names))} / {len(names)}")
    from collections import Counter
    counts = Counter(names)
    dups = {k: v for k, v in counts.items() if v > 1}
    print(f"Duplicates in yellow rows: {dups}")

    # Check empty names
    empty_names = [r for r, rd in yellow_rows if not rd.get('E', {}).get('val', '').strip()]
    print(f"Empty names in yellow rows: {empty_names}")

    # Check Fills and Fonts of G across yellow rows
    g_fills = set(rd.get('G', {}).get('fill') for r, rd in yellow_rows)
    g_fonts = set(rd.get('G', {}).get('font') for r, rd in yellow_rows)
    g_vals = set(rd.get('G', {}).get('val') for r, rd in yellow_rows)
    print(f"Distinct G fills in yellow rows: {g_fills}")
    print(f"Distinct G fonts in yellow rows: {g_fonts}")
    print(f"Distinct G vals in yellow rows: {g_vals}")

    # Check all rows from 518 to 765: color distribution
    colors_dist = {}
    for r in range(518, 766):
        fill = all_rows.get(r, {}).get('G', {}).get('fill')
        colors_dist[fill] = colors_dist.get(fill, 0) + 1
    print(f"Overall color distribution in Col G (518-765): {colors_dist}")

    # Print non-yellow rows summary
    non_yellow = []
    for r in range(518, 766):
        rd = all_rows.get(r, {})
        fill = rd.get('G', {}).get('fill')
        if fill != 'FFFFEB9C':
            non_yellow.append((r, fill, rd.get('E', {}).get('val', ''), rd.get('G', {}).get('val', '')))
    print(f"Total non-yellow rows: {len(non_yellow)} (Green: {len([x for x in non_yellow if x[1]=='FFC6EFCE'])}, Red: {len([x for x in non_yellow if x[1]=='FFFFC7CE'])}, White: {len([x for x in non_yellow if x[1]=='FFFFFFFF'])})")

    # Let's inspect the 2 red rows and 1 white row
    print("\nNon-green, non-yellow rows:")
    for r, fill, e_val, g_val in non_yellow:
        if fill not in ('FFC6EFCE', 'FFFFEB9C'):
            print(f"  Row {r}: fill={fill}, E='{e_val}', G='{g_val}'")

if __name__ == '__main__':
    run_deep_check()
