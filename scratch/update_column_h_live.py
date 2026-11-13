import json
import re
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
import requests

TOKEN_PATH = Path(r"C:\Users\trant\.gemini\antigravity\plugin_data\gsheets\token.json")
SPREADSHEET_ID = "1FTx3IDxfaOadbXmY6BB9pRkRqCdnCter12poQ1txu9s"
SHEET_NAME = "Test 4 (Formatted)"
EXPORT_XLSX = Path(r"C:\Workspaces\Script-Idesk Sender\test4_export.xlsx")
BACKUP_PATH = Path(r"C:\Workspaces\ai-document-sender\scratch\backup_54_cells_before_update.json")

def get_valid_token():
    with open(TOKEN_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    token = data["token"]["access_token"]
    refresh_token = data["token"].get("refresh_token")
    client_id = data.get("client_id")
    client_secret = data.get("client_secret")

    # Test token
    test_url = f"https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}?fields=properties.title"
    r = requests.get(test_url, headers={"Authorization": f"Bearer {token}"})
    if r.status_code == 401 and refresh_token and client_id and client_secret:
        print("Refreshing expired access token...")
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
            print("Token refreshed successfully.")
        else:
            raise RuntimeError(f"Token refresh failed: {rf.status_code} - {rf.text}")
    elif r.status_code != 200:
        raise RuntimeError(f"API request failed: {r.status_code} - {r.text}")
    return token

def construct_h_text(unique_y, unique_r, unique_ex):
    if not unique_y and not unique_r and not unique_ex:
        return "Đầy đủ (Khớp hoàn toàn như kết quả đích)"
    lines = []
    # Dư
    if unique_y:
        lines.append(f"- Dư ({len(unique_y)}):")
        for it in unique_y:
            lines.append(f"  + {it}")
    else:
        lines.append("- Dư: Không")
    # Thiếu
    if unique_r:
        lines.append(f"- Thiếu ({len(unique_r)}):")
        for it in unique_r:
            lines.append(f"  + {it}")
    else:
        lines.append("- Thiếu: Không")
    # Ngoại lệ (only if > 0)
    if unique_ex:
        lines.append(f"- Ngoại lệ ({len(unique_ex)}):")
        for it in unique_ex:
            lines.append(f"  + {it}")
    return "\n".join(lines)

def load_doc_diffs():
    with zipfile.ZipFile(EXPORT_XLSX, "r") as z:
        sst_root = ET.fromstring(z.read("xl/sharedStrings.xml"))
        ns = {"ns": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
        shared_strings = ["".join(t.text for t in si.findall(".//ns:t", ns) if t.text) for si in sst_root.findall("ns:si", ns)]
        styles_root = ET.fromstring(z.read("xl/styles.xml"))
        fills = [f.find("ns:patternFill/ns:fgColor", ns).get("rgb") if f.find("ns:patternFill/ns:fgColor", ns) is not None else None for f in styles_root.findall(".//ns:fills/ns:fill", ns)]
        fonts = [font.find("ns:color", ns).get("rgb") if font.find("ns:color", ns) is not None else None for font in styles_root.findall(".//ns:fonts/ns:font", ns)]
        cell_xfs = [{"fontId": int(xf.get("fontId", 0)), "fillId": int(xf.get("fillId", 0))} for xf in styles_root.findall(".//ns:cellXfs/ns:xf", ns)]
        sh_root = ET.fromstring(z.read("xl/worksheets/sheet1.xml"))
        merge_cells = [mc.get("ref") for mc in sh_root.findall(".//ns:mergeCells/ns:mergeCell", ns)]
        
        rows = {}
        for row in sh_root.findall(".//ns:sheetData/ns:row", ns):
            r_idx = int(row.get("r"))
            row_data = {}
            for c in row.findall("ns:c", ns):
                ref = c.get("r")
                col = re.match(r"([A-Z]+)", ref).group(1)
                s_idx = int(c.get("s", 0))
                t = c.get("t")
                v_elem = c.find("ns:v", ns)
                val = ""
                if v_elem is not None and v_elem.text:
                    val = shared_strings[int(v_elem.text)] if t == "s" else v_elem.text
                row_data[col] = {
                    "val": val,
                    "fill": fills[cell_xfs[s_idx]["fillId"]],
                    "font": fonts[cell_xfs[s_idx]["fontId"]]
                }
            rows[r_idx] = row_data

    h_merges = sorted([tuple(map(int, re.match(r"^H(\d+):H(\d+)$", m).groups())) for m in merge_cells if re.match(r"^H(\d+):H(\d+)$", m)], key=lambda x: x[0])

    changed_items = []
    for r1, r2 in h_merges:
        stt = rows[r1]["A"]["val"]
        so_hieu = rows[r1]["B"]["val"]
        cur_h = rows[r1]["H"]["val"].strip()
        
        y_cells = [rows[r]["E"]["val"].strip() for r in range(r1, r2 + 1) if rows[r]["G"]["fill"] == "FFFFEB9C"]
        r_cells = [rows[r]["G"]["val"].strip() for r in range(r1, r2 + 1) if rows[r]["G"]["fill"] == "FFFFC7CE"]
        ex_cells = [rows[r]["G"]["val"].strip() for r in range(r1, r2 + 1) if rows[r]["G"]["font"] == "FFFF0000"]
        
        unique_y = list(dict.fromkeys([x for x in y_cells if x]))
        unique_r = list(dict.fromkeys([x for x in r_cells if x]))
        unique_ex = list(dict.fromkeys([x for x in ex_cells if x]))
        
        new_h = construct_h_text(unique_y, unique_r, unique_ex)
        
        cur_norm = "\n".join(l.strip() for l in cur_h.splitlines() if l.strip())
        new_norm = "\n".join(l.strip() for l in new_h.splitlines() if l.strip())
        
        if cur_norm != new_norm:
            changed_items.append({
                "stt": stt,
                "so_hieu": so_hieu,
                "r1": r1,
                "r2": r2,
                "cell": f"H{r1}",
                "old_h": cur_h,
                "new_h": new_h,
                "unique_y_count": len(unique_y),
                "unique_r_count": len(unique_r),
                "unique_ex_count": len(unique_ex),
            })
    return changed_items

def main():
    changed_items = load_doc_diffs()
    print(f"Loaded {len(changed_items)} items requiring updates.")
    assert len(changed_items) == 54, f"Expected exactly 54 changed items, got {len(changed_items)}"

    token = get_valid_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # 1. Fetch current live values for these 54 cells to backup
    print("Backing up 54 live cells from Google Sheets...")
    range_strs = [f"'{SHEET_NAME}'!{item['cell']}" for item in changed_items]
    ranges_query = "&".join([f"ranges={requests.utils.quote(r)}" for r in range_strs])
    fetch_url = f"https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}/values:batchGet?{ranges_query}"
    r_backup = requests.get(fetch_url, headers=headers)
    assert r_backup.status_code == 200, f"Failed to fetch backup: {r_backup.status_code} - {r_backup.text}"
    backup_data = r_backup.json().get("valueRanges", [])
    
    with open(BACKUP_PATH, "w", encoding="utf-8") as f:
        json.dump(backup_data, f, ensure_ascii=False, indent=2)
    print(f"Backup saved to {BACKUP_PATH}")

    # 2. Prepare batch update payload
    data_payload = []
    for item in changed_items:
        data_payload.append({
            "range": f"'{SHEET_NAME}'!{item['cell']}",
            "values": [[item["new_h"]]]
        })

    update_url = f"https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}/values:batchUpdate"
    update_body = {
        "valueInputOption": "RAW",
        "data": data_payload
    }

    print(f"Sending batchUpdate for {len(data_payload)} cells to Google Sheets...")
    r_update = requests.post(update_url, headers=headers, json=update_body)
    assert r_update.status_code == 200, f"Update failed: {r_update.status_code} - {r_update.text}"
    resp_json = r_update.json()
    print("Batch update response:", resp_json.get("totalUpdatedCells"), "cells updated across", resp_json.get("totalUpdatedSheets"), "sheet.")

    # 3. Verify all 54 cells live from Google Sheets
    print("\nVerifying updated cells from live Google Sheet...")
    r_verify = requests.get(fetch_url, headers=headers)
    assert r_verify.status_code == 200, f"Verification fetch failed: {r_verify.status_code} - {r_verify.text}"
    verified_ranges = r_verify.json().get("valueRanges", [])

    all_matched = True
    for item, v_range in zip(changed_items, verified_ranges):
        live_val = v_range.get("values", [[""]])[0][0]
        exp_val = item["new_h"]
        if live_val != exp_val:
            print(f"[FAIL] Mismatch at {item['cell']} (STT {item['stt']}):")
            print(f"  Expected: {repr(exp_val[:60])}...")
            print(f"  Got live: {repr(live_val[:60])}...")
            all_matched = False

    if all_matched:
        print(f"[SUCCESS] All {len(changed_items)} cells in Column H verified 100% MATCH on Google Sheets!")
    else:
        raise RuntimeError("Verification failed for some cells!")

if __name__ == "__main__":
    main()
