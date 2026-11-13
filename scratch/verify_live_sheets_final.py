import json
import re
import requests
from pathlib import Path
import zipfile
import xml.etree.ElementTree as ET

TOKEN_PATH = Path(r"C:\Users\trant\.gemini\antigravity\plugin_data\gsheets\token.json")
SPREADSHEET_ID = "1FTx3IDxfaOadbXmY6BB9pRkRqCdnCter12poQ1txu9s"
SHEET_NAME = "Test 4 (Formatted)"
EXPORT_XLSX = Path(r"C:\Workspaces\Script-Idesk Sender\test4_export.xlsx")

def get_valid_token():
    with open(TOKEN_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["token"]["access_token"]

def main():
    token = get_valid_token()
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Check sheet merges
    print("Checking sheet metadata and merges on live Google Sheet...")
    meta_url = f"https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}?fields=sheets(properties,merges)"
    r_meta = requests.get(meta_url, headers=headers)
    assert r_meta.status_code == 200, f"Meta fetch failed: {r_meta.status_code}"
    
    target_sheet = None
    for s in r_meta.json().get("sheets", []):
        if s["properties"]["title"] == SHEET_NAME:
            target_sheet = s
            break
    assert target_sheet is not None, f"Sheet {SHEET_NAME} not found!"
    
    merges = target_sheet.get("merges", [])
    print(f"Total merges on sheet '{SHEET_NAME}': {len(merges)}")
    
    # Check H merges (startColumnIndex == 7, endColumnIndex == 8)
    h_merges = [m for m in merges if m.get("startColumnIndex") == 7 and m.get("endColumnIndex") == 8]
    print(f"Total Column H merges on live sheet: {len(h_merges)}")
    assert len(h_merges) == 500, f"Expected 500 merges in Column H, got {len(h_merges)}!"

    # 2. Inspect specific updated cells: H342 (STT 16), H518 (STT 17), H4019 (STT 99), H11515 (STT 308), H6154 (STT 152)
    sample_cells = ["H342", "H518", "H4019", "H6154", "H11515"]
    range_query = "&".join([f"ranges={requests.utils.quote(f'{SHEET_NAME}!{c}')}" for c in sample_cells])
    fetch_url = f"https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}/values:batchGet?{range_query}"
    r_samples = requests.get(fetch_url, headers=headers)
    assert r_samples.status_code == 200, f"Samples fetch failed: {r_samples.status_code}"
    
    print("\n=== SAMPLE CELL VALUES FROM LIVE GOOGLE SHEET ===")
    for cell, v_range in zip(sample_cells, r_samples.json().get("valueRanges", [])):
        val = v_range.get("values", [[""]])[0][0]
        print(f"--- Cell {cell} ---")
        for line in val.splitlines()[:6]:
            print(" ", line)
        if len(val.splitlines()) > 6:
            print("  ...")
            for line in val.splitlines()[-3:]:
                print(" ", line)
        print()

    print("[VERIFICATION COMPLETE] Live Google Sheets verified successfully!")

if __name__ == "__main__":
    main()
