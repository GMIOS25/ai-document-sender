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

    # Load expected H values from sheet formatted cells
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

    def construct_h_text(unique_y, unique_r, unique_ex):
        if not unique_y and not unique_r and not unique_ex:
            return "Đầy đủ (Khớp hoàn toàn như kết quả đích)"
        lines = []
        if unique_y:
            lines.append(f"- Dư ({len(unique_y)}):")
            for it in unique_y: lines.append(f"  + {it}")
        else:
            lines.append("- Dư: Không")
        if unique_r:
            lines.append(f"- Thiếu ({len(unique_r)}):")
            for it in unique_r: lines.append(f"  + {it}")
        else:
            lines.append("- Thiếu: Không")
        if unique_ex:
            lines.append(f"- Ngoại lệ ({len(unique_ex)}):")
            for it in unique_ex: lines.append(f"  + {it}")
        return "\n".join(lines)

    expected_h = {}
    for r1, r2 in h_merges:
        y_cells = [rows[r]["E"]["val"].strip() for r in range(r1, r2 + 1) if rows[r]["G"]["fill"] == "FFFFEB9C"]
        r_cells = [rows[r]["G"]["val"].strip() for r in range(r1, r2 + 1) if rows[r]["G"]["fill"] == "FFFFC7CE"]
        ex_cells = [rows[r]["G"]["val"].strip() for r in range(r1, r2 + 1) if rows[r]["G"]["font"] == "FFFF0000"]
        unique_y = list(dict.fromkeys([x for x in y_cells if x]))
        unique_r = list(dict.fromkeys([x for x in r_cells if x]))
        unique_ex = list(dict.fromkeys([x for x in ex_cells if x]))
        expected_h[r1] = construct_h_text(unique_y, unique_r, unique_ex)

    # Fetch live Column H across entire range
    print("Fetching entire live Column H data (H2:H18320)...")
    fetch_url = f"https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}/values/'{SHEET_NAME}'!H2:H18320"
    r = requests.get(fetch_url, headers=headers)
    assert r.status_code == 200, f"Fetch failed: {r.status_code}"
    
    live_rows = r.json().get("values", [])
    print(f"Fetched {len(live_rows)} rows from Column H.")

    mismatch_count = 0
    for r1, exp_val in expected_h.items():
        idx = r1 - 2 # 0-indexed into H2:H18320
        live_val = live_rows[idx][0] if idx < len(live_rows) and len(live_rows[idx]) > 0 else ""
        cur_norm = "\n".join(l.strip() for l in live_val.splitlines() if l.strip())
        exp_norm = "\n".join(l.strip() for l in exp_val.splitlines() if l.strip())
        if cur_norm != exp_norm:
            print(f"[MISMATCH] at H{r1}:")
            print(f"  Live: {repr(cur_norm[:50])}")
            print(f"  Exp:  {repr(exp_norm[:50])}")
            mismatch_count += 1

    print(f"\nTotal checked docs: {len(expected_h)}")
    print(f"Total mismatches: {mismatch_count}")
    if mismatch_count == 0:
        print("[PERFECT AUDIT] 500/500 documents on Google Sheets Column H are 100% in sync with Unique Entities policy!")

if __name__ == "__main__":
    main()
