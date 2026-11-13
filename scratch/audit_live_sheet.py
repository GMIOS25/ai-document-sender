import json
import requests
from pathlib import Path

def run_live_audit():
    token_path = Path(r"C:\Users\trant\.gemini\antigravity\plugin_data\gsheets\token.json")
    with open(token_path, 'r', encoding='utf-8') as f:
        token = json.load(f)['token']['access_token']

    headers = {'Authorization': f'Bearer {token}'}
    # Fetch rows 518 to 765 full cell data
    url = ('https://sheets.googleapis.com/v4/spreadsheets/1FTx3IDxfaOadbXmY6BB9pRkRqCdnCter12poQ1txu9s'
           '?ranges=' + requests.utils.quote('Test 4 (Formatted)!A518:H765') +
           '&fields=sheets.data.rowData.values(effectiveFormat.backgroundColor,effectiveFormat.textFormat,formattedValue)')
    res = requests.get(url, headers=headers)
    assert res.status_code == 200, f"API error: {res.status_code}"
    
    data = res.json()
    rows = data['sheets'][0]['data'][0].get('rowData', [])
    print(f"Total rows fetched from live Google Sheet: {len(rows)}")

    def rgb_to_hex(c):
        if not c:
            return "None"
        r = int(round(c.get('red', 0) * 255))
        g = int(round(c.get('green', 0) * 255))
        b = int(round(c.get('blue', 0) * 255))
        return f"#{r:02X}{g:02X}{b:02X}"

    yellow_rows = []
    green_rows = []
    red_rows = []
    white_rows = []

    for idx, r in enumerate(rows):
        r_num = 518 + idx
        vals = r.get('values', [])
        
        val_e = vals[4].get('formattedValue', '') if len(vals) > 4 else ''
        val_g = vals[6].get('formattedValue', '') if len(vals) > 6 else ''
        
        fmt_g = vals[6].get('effectiveFormat', {}) if len(vals) > 6 else {}
        bg_g = rgb_to_hex(fmt_g.get('backgroundColor'))
        fg_g = rgb_to_hex(fmt_g.get('textFormat', {}).get('foregroundColor'))
        
        if bg_g == '#FFEB9C':
            yellow_rows.append((r_num, val_e, val_g, bg_g, fg_g))
        elif bg_g == '#C6EFCE':
            green_rows.append((r_num, val_e, val_g, bg_g, fg_g))
        elif bg_g == '#FFC7CE':
            red_rows.append((r_num, val_e, val_g, bg_g, fg_g))
        else:
            white_rows.append((r_num, val_e, val_g, bg_g, fg_g, bg_g))

    print(f"Live Google Sheet Counts:")
    print(f"  Yellow (#FFEB9C): {len(yellow_rows)}")
    print(f"  Green  (#C6EFCE): {len(green_rows)}")
    print(f"  Red    (#FFC7CE): {len(red_rows)}")
    print(f"  White/Other    : {len(white_rows)}")

    # Check first and last 3 yellow rows
    print("\nFirst 3 yellow rows:")
    for yr in yellow_rows[:3]:
        print(f"  Row {yr[0]}: E='{yr[1]}', G='{yr[2]}', bg={yr[3]}")
    print("Last 3 yellow rows:")
    for yr in yellow_rows[-3:]:
        print(f"  Row {yr[0]}: E='{yr[1]}', G='{yr[2]}', bg={yr[3]}")

if __name__ == '__main__':
    run_live_audit()
