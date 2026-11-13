import json
import requests
from pathlib import Path

TOKEN_PATH = Path(r"C:\Users\trant\.gemini\antigravity\plugin_data\gsheets\token.json")
SPREADSHEET_ID = "1FTx3IDxfaOadbXmY6BB9pRkRqCdnCter12poQ1txu9s"
SHEET_TITLE = "Thống kê Đánh giá (DA)"

def hex_to_rgb(hex_str):
    hex_str = hex_str.lstrip("#")
    r = int(hex_str[0:2], 16) / 255.0
    g = int(hex_str[2:4], 16) / 255.0
    b = int(hex_str[4:6], 16) / 255.0
    return {"red": round(r, 3), "green": round(g, 3), "blue": round(b, 3)}

def get_valid_token():
    with open(TOKEN_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    token = data["token"]["access_token"]
    refresh_token = data["token"].get("refresh_token")
    client_id = data.get("client_id")
    client_secret = data.get("client_secret")

    test_url = f"https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}?fields=properties.title"
    r = requests.get(test_url, headers={"Authorization": f"Bearer {token}"})
    if r.status_code == 401 and refresh_token and client_id and client_secret:
        rf = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
        )
        if rf.status_code == 200:
            token = rf.json()["access_token"]
            data["token"]["access_token"] = token
            with open(TOKEN_PATH, "w", encoding="utf-8") as f_out:
                json.dump(data, f_out, indent=2)
    return token

def create_or_recreate_sheet():
    token = get_valid_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    # 1. Get sheets list
    meta_url = f"https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}?fields=sheets.properties"
    res = requests.get(meta_url, headers=headers).json()
    sheets = res.get("sheets", [])
    
    existing_sheet_id = None
    for s in sheets:
        if s["properties"]["title"] == SHEET_TITLE:
            existing_sheet_id = s["properties"]["sheetId"]
            break
            
    if existing_sheet_id is not None:
        print(f"Sheet '{SHEET_TITLE}' already exists with ID {existing_sheet_id}. Deleting to recreate clean...")
        del_body = {"requests": [{"deleteSheet": {"sheetId": existing_sheet_id}}]}
        del_r = requests.post(
            f"https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}:batchUpdate",
            headers=headers,
            json=del_body
        )
        assert del_r.status_code == 200, f"Failed to delete existing sheet: {del_r.text}"
        print("Deleted existing sheet.")

    # 2. Add sheet at index 0
    print(f"Creating new sheet '{SHEET_TITLE}' at index 0...")
    add_body = {
        "requests": [
            {
                "addSheet": {
                    "properties": {
                        "title": SHEET_TITLE,
                        "index": 0,
                        "gridProperties": {
                            "rowCount": 55,
                            "columnCount": 10,
                            "frozenRowCount": 4
                        },
                        "tabColor": hex_to_rgb("#1A365D")
                    }
                }
            }
        ]
    }
    add_r = requests.post(
        f"https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}:batchUpdate",
        headers=headers,
        json=add_body
    )
    assert add_r.status_code == 200, f"Failed to add sheet: {add_r.text}"
    new_sheet_id = add_r.json()["replies"][0]["addSheet"]["properties"]["sheetId"]
    print(f"Created sheet successfully with sheetId: {new_sheet_id}")
    return new_sheet_id

if __name__ == "__main__":
    sid = create_or_recreate_sheet()
    print("New Sheet ID:", sid)
