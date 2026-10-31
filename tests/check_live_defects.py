import json
import requests
import sys

sys.stdout.reconfigure(encoding='utf-8')

def main():
    token_path = r'C:\Users\trant\.gemini\antigravity\plugin_data\gsheets\token.json'
    with open(token_path, 'r') as f:
        token = json.load(f)['token']['access_token']

    sheet_id = '1FTx3IDxfaOadbXmY6BB9pRkRqCdnCter12poQ1txu9s'
    rows_to_check = [805, 880, 896, 1065, 1097, 4493, 4611]

    ranges = [f"'Thống kê'!D{r}:E{r}" for r in rows_to_check]
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values:batchGet?" + '&'.join([f"ranges={r}" for r in ranges])

    res = requests.get(url, headers={'Authorization': f'Bearer {token}'}).json()
    for vr in res.get('valueRanges', []):
        rng = vr.get('range')
        vals = vr.get('values', [['', '']])[0]
        col_d = vals[0] if len(vals) > 0 else ''
        col_e = vals[1] if len(vals) > 1 else ''
        print(f"{rng} -> Col D: '{col_d}' | Col E: '{col_e}'")

if __name__ == '__main__':
    main()
