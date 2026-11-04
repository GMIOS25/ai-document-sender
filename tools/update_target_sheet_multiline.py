"""
tools/update_target_sheet_multiline.py

Updates the Google Spreadsheet tab "Kết quả đích thực tế" (sheetId: 991067123)
in spreadsheet 1FTx3IDxfaOadbXmY6BB9pRkRqCdnCter12poQ1txu9s according to the user requirements:

1. In Column D ("Kết quả gửi đi kèm (Đích thực tế)"):
   - Remove "Người xử lí" and "Người theo dõi" labels/prefixes.
   - Remove the entire "Đơn vị nhận" section (already present in Column E).
2. In Column D, each title/name is on its own row/line (separated by newline \n):
   e.g. in D2:
   Tổ công tác (Tổ công tác)
   Chủ tịch UBND tỉnh (Phạm Anh Tuấn)
   Phó Chủ tịch Thường trực UBND tỉnh (Nguyễn Tuấn Thanh)
   ...
3. In Column E ("Đơn vị nhận (Dữ liệu mẫu)"):
   - Each recipient unit is on its own row/line (separated by newline \n).
"""

import sys
import os
import json
from pathlib import Path
import requests

sys.stdout.reconfigure(encoding="utf-8")

# Ensure tools directory is in sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
WORKSPACE_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

from reconcile_sheet import GoogleSheetsAuth, DEFAULT_SPREADSHEET_ID

SPREADSHEET_ID = DEFAULT_SPREADSHEET_ID
TARGET_SHEET_NAME = "Kết quả đích thực tế"
TARGET_SHEET_ID = 991067123


def parse_col_d(raw_text: str) -> str:
    """Extract person names from 'Người xử lí:' and 'Người theo dõi:', separated by newlines."""
    lines = raw_text.splitlines()
    names = []
    for line in lines:
        line = line.strip()
        if line.startswith("Người xử lí:"):
            c = line[len("Người xử lí:"):].strip()
            if c:
                for x in c.split(";"):
                    if x.strip():
                        names.append(x.strip())
        elif line.startswith("Người theo dõi:"):
            c = line[len("Người theo dõi:"):].strip()
            if c:
                for x in c.split(";"):
                    if x.strip():
                        names.append(x.strip())
    return "\n".join(names)


def parse_col_e(raw_text: str) -> str:
    """Extract units separated by newlines."""
    if not raw_text:
        return ""
    units = [x.strip() for x in raw_text.split(";") if x.strip()]
    return "\n".join(units)


def main():
    print("=" * 60)
    print("STARTING GOOGLE SHEET UPDATE - MULTILINE FORMATTING")
    print("=" * 60)

    auth = GoogleSheetsAuth()

    # Step 1: Read existing data from target sheet
    print(f"Reading current rows from '{TARGET_SHEET_NAME}'...")
    read_url = f"https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}/values/{TARGET_SHEET_NAME}!A1:F501"
    resp = auth.authorized_request("GET", read_url)
    if resp.status_code != 200:
        raise RuntimeError(f"Failed to read sheet ({resp.status_code}): {resp.text}")

    values = resp.json().get("values", [])
    if len(values) < 501:
        raise ValueError(f"Expected 501 rows (header + 500 items), got {len(values)}")

    header = values[0]
    data_rows = values[1:]
    print(f"Successfully read header: {header}")
    print(f"Found {len(data_rows)} data rows.")

    # Step 2: Transform Column D and Column E for all 500 rows
    transformed_rows = []
    for idx, row in enumerate(data_rows):
        stt = row[0] if len(row) > 0 else str(idx + 1)
        so_hieu = row[1] if len(row) > 1 else ""
        d_val = row[3] if len(row) > 3 else ""
        e_val = row[4] if len(row) > 4 else ""

        new_d = parse_col_d(d_val)
        new_e = parse_col_e(e_val)

        transformed_rows.append([new_d, new_e])

    print(f"Prepared transformed data for {len(transformed_rows)} rows.")
    print("\n--- SAMPLE ROW 1 (STT 1) PREVIEW ---")
    print(f"Col D ({len(transformed_rows[0][0].splitlines())} lines):")
    for line in transformed_rows[0][0].splitlines()[:5]:
        print(f"  {line}")
    print("  ...")
    print(f"Col E ({len(transformed_rows[0][1].splitlines())} lines):")
    for line in transformed_rows[0][1].splitlines()[:5]:
        print(f"  {line}")
    print("  ...")

    # Step 3: Write transformed data back to D2:E501
    update_range = f"{TARGET_SHEET_NAME}!D2:E501"
    print(f"\nWriting transformed data to {update_range}...")
    write_url = f"https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}/values/{update_range}?valueInputOption=USER_ENTERED"
    payload = {
        "range": update_range,
        "majorDimension": "ROWS",
        "values": transformed_rows
    }
    resp = auth.authorized_request("PUT", write_url, json=payload)
    if resp.status_code != 200:
        raise RuntimeError(f"Failed to update values ({resp.status_code}): {resp.text}")

    print("Data write successful:", resp.json())

    # Step 4: Update cell format for rows 2 to 501 (verticalAlignment: TOP, wrapStrategy: WRAP)
    print("\nUpdating formatting (verticalAlignment: TOP, wrapStrategy: WRAP)...")
    format_url = f"https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}:batchUpdate"
    format_requests = {
        "requests": [
            {
                "repeatCell": {
                    "range": {
                        "sheetId": TARGET_SHEET_ID,
                        "startRowIndex": 1,
                        "endRowIndex": 501,
                        "startColumnIndex": 0,
                        "endColumnIndex": 6
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "verticalAlignment": "TOP",
                            "wrapStrategy": "WRAP"
                        }
                    },
                    "fields": "userEnteredFormat.verticalAlignment,userEnteredFormat.wrapStrategy"
                }
            }
        ]
    }
    resp_fmt = auth.authorized_request("POST", format_url, json=format_requests)
    if resp_fmt.status_code != 200:
        print(f"Warning: Formatting update returned {resp_fmt.status_code}: {resp_fmt.text}")
    else:
        print("Formatting updated successfully.")

    # Step 5: Read back and verify
    print("\nReading back to verify data integrity...")
    resp_verify = auth.authorized_request("GET", read_url)
    verified_values = resp_verify.json().get("values", [])
    verified_data = verified_values[1:]

    assert len(verified_data) == 500, f"Expected 500 rows, got {len(verified_data)}"

    for idx, row in enumerate(verified_data):
        d_val = row[3] if len(row) > 3 else ""
        e_val = row[4] if len(row) > 4 else ""

        # Assert no label strings remain in Col D
        assert "Người xử lí" not in d_val, f"Row {idx+2} still has 'Người xử lí'"
        assert "Người theo dõi" not in d_val, f"Row {idx+2} still has 'Người theo dõi'"
        assert "Đơn vị nhận" not in d_val, f"Row {idx+2} still has 'Đơn vị nhận'"

        expected_d, expected_e = transformed_rows[idx]
        assert d_val == expected_d, f"Row {idx+2} Col D mismatch: {repr(d_val[:50])} vs {repr(expected_d[:50])}"
        assert e_val == expected_e, f"Row {idx+2} Col E mismatch: {repr(e_val[:50])} vs {repr(expected_e[:50])}"

    print("=" * 60)
    print("ALL 500 ROWS VERIFIED SUCCESSFULLY! 100% MATCH!")
    print("=" * 60)


if __name__ == "__main__":
    main()
