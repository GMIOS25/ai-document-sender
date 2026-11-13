import json
import requests
from pathlib import Path

token_path = Path(r"C:\Users\trant\.gemini\antigravity\plugin_data\gsheets\token.json")
with open(token_path, 'r', encoding='utf-8') as f:
    token = json.load(f)['token']['access_token']

headers = {'Authorization': f'Bearer {token}'}
url = 'https://sheets.googleapis.com/v4/spreadsheets/1FTx3IDxfaOadbXmY6BB9pRkRqCdnCter12poQ1txu9s/values/' + requests.utils.quote('Test 4 (Formatted)!H518')
res = requests.get(url, headers=headers)
val = res.json().get('values', [['']])[0][0]

lines = val.split('\n')
print(f"Total lines in H518: {len(lines)}")
for idx, l in enumerate(lines):
    print(f"{idx+1:2d}: {l}")
