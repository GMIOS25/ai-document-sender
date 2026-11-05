"""
tools/populate_target_sheet.py

Live Transfer of 500 Canonical Documents and Attached Send Results
to Google Spreadsheet tab "Kết quả đích thực tế" (sheetId: 991067123).

Target Spreadsheet ID: 1FTx3IDxfaOadbXmY6BB9pRkRqCdnCter12poQ1txu9s
Worksheet: "Kết quả đích thực tế"

Columns:
  Col A: STT (1 to 500)
  Col B: Số hiệu văn bản (view.cpx -> ed.signNumber)
  Col C: Trích yếu (view.cpx -> ed.subject)
  Col D: Kết quả gửi đi kèm (Đích thực tế) (Full content from kết_quả_gửi_đi.txt)
  Col E: Đơn vị nhận (Dữ liệu mẫu) (Đơn vị nhận from kết_quả_gửi_đi.txt line 3 / book.receiver)
  Col F: Link liên kết đến tài liệu chính theo văn bản (Google Drive URL)
"""

import os
import sys
import json
import time
import csv
import argparse
from pathlib import Path
import requests

sys.stdout.reconfigure(encoding="utf-8")

# Constants
SPREADSHEET_ID = "1FTx3IDxfaOadbXmY6BB9pRkRqCdnCter12poQ1txu9s"
TARGET_SHEET_NAME = "Kết quả đích thực tế"
TARGET_SHEET_ID = 991067123

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
SOURCE_DOCS_DIR = WORKSPACE_ROOT / "resources" / "văn bản mẫu" / "vpub" / "Hợp lệ"
PREPARED_DOCS_FILE = WORKSPACE_ROOT / ".tmp" / "prepared_500_documents.json"
CSV_MAP_FILE = WORKSPACE_ROOT / ".tmp" / "thong_ke_doi_soat_500_van_ban.csv"
TOKEN_FILE = Path(r"C:\Users\trant\.gemini\antigravity\plugin_data\gsheets\token.json")

HEADER_ROW = [
    "STT",
    "Số hiệu văn bản",
    "Trích yếu",
    "Kết quả gửi đi kèm (Đích thực tế)",
    "Đơn vị nhận (Dữ liệu mẫu)",
    "Link liên kết đến tài liệu chính theo văn bản"
]


def get_access_token() -> str:
    """Load valid Google OAuth access token, refreshing if necessary."""
    if not TOKEN_FILE.exists():
        raise FileNotFoundError(f"OAuth token file not found at: {TOKEN_FILE}")

    with open(TOKEN_FILE, "r", encoding="utf-8") as f:
        token_data = json.load(f)

    token_info = token_data.get("token", {})
    access_token = token_info.get("access_token")

    # Test token validity against Google Sheets API
    test_url = f"https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}?fields=spreadsheetId"
    headers = {"Authorization": f"Bearer {access_token}"}
    r = requests.get(test_url, headers=headers, timeout=10)

    if r.status_code == 200:
        return access_token

    print(f"Current token status {r.status_code}. Refreshing OAuth access token...")
    client_id = token_data.get("client_id")
    client_secret = token_data.get("client_secret")
    refresh_token = token_info.get("refresh_token")

    if not refresh_token:
        raise ValueError("No refresh_token found in token.json to refresh access token.")

    refresh_url = "https://oauth2.googleapis.com/token"
    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token"
    }

    resp = requests.post(refresh_url, data=payload, timeout=15)
    if resp.status_code != 200:
        raise RuntimeError(f"Failed to refresh access token ({resp.status_code}): {resp.text}")

    new_token_data = resp.json()
    new_access_token = new_token_data.get("access_token")
    token_info["access_token"] = new_access_token
    token_data["token"] = token_info

    # Save back to token file
    with open(TOKEN_FILE, "w", encoding="utf-8") as f:
        json.dump(token_data, f, indent=2)

    print("Access token refreshed successfully.")
    return new_access_token


def load_drive_url_map() -> dict[str, str]:
    """Load verified Drive URLs for all 500 documents (STT -> URL)."""
    stt_to_url = {}
    if CSV_MAP_FILE.exists():
        with open(CSV_MAP_FILE, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                if row and row[0].isdigit():
                    stt_to_url[row[0]] = row[5]

    if len(stt_to_url) >= 500:
        return stt_to_url

    # Fallback to query live 'Thống kê' tab
    print("CSV map missing or incomplete. Querying live 'Thống kê' tab for Drive URLs...")
    token = get_access_token()
    headers = {"Authorization": f"Bearer {token}"}
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}/values/'Thống kê'!A2:F5200"
    res = requests.get(url, headers=headers, timeout=20)
    if res.status_code == 200:
        values = res.json().get("values", [])
        for row in values:
            if row and row[0].isdigit():
                stt_to_url[row[0]] = row[5] if len(row) > 5 else ""

    return stt_to_url


def prepare_document_rows() -> list[list[str]]:
    """
    Ingest 500 canonical documents (descending 13116 down to 12610)
    and format into 501 rows (Header + 500 Documents).
    """
    if not PREPARED_DOCS_FILE.exists():
        raise FileNotFoundError(f"Prepared docs catalog not found at: {PREPARED_DOCS_FILE}")

    with open(PREPARED_DOCS_FILE, "r", encoding="utf-8") as f:
        docs = json.load(f)

    if len(docs) != 500:
        raise ValueError(f"Expected 500 documents in prepared catalog, got {len(docs)}")

    drive_urls = load_drive_url_map()
    rows = [HEADER_ROW]

    for i, doc in enumerate(docs, 1):
        stt_str = str(i)
        folder_name = doc["folder_name"]
        doc_dir = SOURCE_DOCS_DIR / folder_name

        # Read metadata from view.cpx
        cpx_path = doc_dir / "view.cpx"
        with open(cpx_path, "r", encoding="utf-8") as f:
            cpx = json.load(f)
        ed = cpx.get("ed", {})
        sign_number = (ed.get("signNumber") or doc.get("so_hieu", "")).strip()
        subject = (ed.get("subject") or doc.get("trich_yeu", "")).strip()

        # Read full attached send results from kết_quả_gửi_đi.txt
        txt_path = doc_dir / "kết_quả_gửi_đi.txt"
        full_send_result = txt_path.read_text(encoding="utf-8").strip()

        # Extract Đơn vị nhận (line 3 / book.receiver)
        don_vi_nhan = ""
        for line in full_send_result.splitlines():
            if line.startswith("Đơn vị nhận:"):
                don_vi_nhan = line[len("Đơn vị nhận:"):].strip()
                break

        # Fallback to book.receiver if empty or missing in txt
        if not don_vi_nhan:
            book_receiver = (cpx.get("book") or {}).get("receiver", "") or ""
            don_vi_nhan = book_receiver.strip()

        drive_url = drive_urls.get(stt_str, "")

        rows.append([
            stt_str,
            sign_number,
            subject,
            full_send_result,
            don_vi_nhan,
            drive_url
        ])

    return rows


def populate_target_sheet(dry_run: bool = False) -> None:
    """Bulk update Google Spreadsheet tab 'Kết quả đích thực tế' with 500 documents."""
    print("=" * 70)
    print("M1: 500 Documents Live Transfer to 'Kết quả đích thực tế'")
    print(f"Spreadsheet ID: {SPREADSHEET_ID}")
    print(f"Worksheet Name: '{TARGET_SHEET_NAME}' (sheetId: {TARGET_SHEET_ID})")
    print("=" * 70)

    start_time = time.time()
    rows = prepare_document_rows()
    print(f"Ingested 500 documents from {SOURCE_DOCS_DIR}")
    print(f"Prepared matrix: {len(rows)} rows x {len(HEADER_ROW)} columns")

    # Sanity checks on prepared rows
    assert len(rows) == 501, f"Expected 501 rows, got {len(rows)}"
    assert rows[1][0] == "1" and "13116" in rows[1][1], f"Row 1 mismatch: {rows[1][:2]}"
    assert rows[500][0] == "500" and "12610" in rows[500][1], f"Row 500 mismatch: {rows[500][:2]}"

    if dry_run:
        print("\n[DRY RUN] Rows verified successfully. No remote changes made.")
        return

    token = get_access_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # Step 1: Bulk write all 501 rows in 1 single HTTP PUT request
    print(f"\nStep 1: Bulk updating values to '{TARGET_SHEET_NAME}'!A1:F501 in 1 API call...")
    put_url = (
        f"https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}/"
        f"values/'{TARGET_SHEET_NAME}'!A1:F501?valueInputOption=USER_ENTERED"
    )
    put_body = {
        "range": f"'{TARGET_SHEET_NAME}'!A1:F501",
        "majorDimension": "ROWS",
        "values": rows
    }

    res_put = requests.put(put_url, headers=headers, json=put_body, timeout=30)
    if res_put.status_code != 200:
        raise RuntimeError(f"Failed to update values ({res_put.status_code}): {res_put.text}")

    put_resp_data = res_put.json()
    print(f"Values updated successfully! Updated cells: {put_resp_data.get('updatedCells')}, rows: {put_resp_data.get('updatedRows')}")

    # Step 2: Format header, columns, and grid dimensions via batchUpdate in 1 API call
    print("\nStep 2: Applying header styling, column widths, freeze row, and grid dimensions...")
    batch_url = f"https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}:batchUpdate"

    col_widths = [
        (0, 1, 60),    # Col A: STT (60px)
        (1, 2, 160),   # Col B: Số hiệu (160px)
        (2, 3, 350),   # Col C: Trích yếu (350px)
        (3, 4, 380),   # Col D: Kết quả gửi đi kèm (380px)
        (4, 5, 380),   # Col E: Đơn vị nhận (380px)
        (5, 6, 260),   # Col F: Link Drive (260px)
    ]

    dimension_requests = [
        {
            "updateDimensionProperties": {
                "range": {
                    "sheetId": TARGET_SHEET_ID,
                    "dimension": "COLUMNS",
                    "startIndex": start,
                    "endIndex": end
                },
                "properties": {
                    "pixelSize": width
                },
                "fields": "pixelSize"
            }
        }
        for start, end, width in col_widths
    ]

    batch_requests = [
        # Resize grid to exactly 501 rows x 6 columns and freeze row 1
        {
            "updateSheetProperties": {
                "properties": {
                    "sheetId": TARGET_SHEET_ID,
                    "gridProperties": {
                        "rowCount": 501,
                        "columnCount": 6,
                        "frozenRowCount": 1
                    }
                },
                "fields": "gridProperties(rowCount,columnCount,frozenRowCount)"
            }
        },
        # Header formatting: Blue background (#1A73E8), white bold text, centered, middle vertical, wrap text
        {
            "repeatCell": {
                "range": {
                    "sheetId": TARGET_SHEET_ID,
                    "startRowIndex": 0,
                    "endRowIndex": 1,
                    "startColumnIndex": 0,
                    "endColumnIndex": 6
                },
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": {
                            "red": 0.102,
                            "green": 0.451,
                            "blue": 0.910
                        },
                        "textFormat": {
                            "foregroundColor": {
                                "red": 1.0,
                                "green": 1.0,
                                "blue": 1.0
                            },
                            "bold": True,
                            "fontSize": 10
                        },
                        "horizontalAlignment": "CENTER",
                        "verticalAlignment": "MIDDLE",
                        "wrapStrategy": "WRAP"
                    }
                },
                "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,verticalAlignment,wrapStrategy)"
            }
        },
        # Data formatting: Col A, B centered
        {
            "repeatCell": {
                "range": {
                    "sheetId": TARGET_SHEET_ID,
                    "startRowIndex": 1,
                    "endRowIndex": 501,
                    "startColumnIndex": 0,
                    "endColumnIndex": 2
                },
                "cell": {
                    "userEnteredFormat": {
                        "horizontalAlignment": "CENTER",
                        "verticalAlignment": "MIDDLE"
                    }
                },
                "fields": "userEnteredFormat(horizontalAlignment,verticalAlignment)"
            }
        },
        # Data formatting: Col C, D, E left aligned with text wrap
        {
            "repeatCell": {
                "range": {
                    "sheetId": TARGET_SHEET_ID,
                    "startRowIndex": 1,
                    "endRowIndex": 501,
                    "startColumnIndex": 2,
                    "endColumnIndex": 5
                },
                "cell": {
                    "userEnteredFormat": {
                        "horizontalAlignment": "LEFT",
                        "verticalAlignment": "MIDDLE",
                        "wrapStrategy": "WRAP"
                    }
                },
                "fields": "userEnteredFormat(horizontalAlignment,verticalAlignment,wrapStrategy)"
            }
        },
        # Data formatting: Col F link left aligned
        {
            "repeatCell": {
                "range": {
                    "sheetId": TARGET_SHEET_ID,
                    "startRowIndex": 1,
                    "endRowIndex": 501,
                    "startColumnIndex": 5,
                    "endColumnIndex": 6
                },
                "cell": {
                    "userEnteredFormat": {
                        "horizontalAlignment": "LEFT",
                        "verticalAlignment": "MIDDLE"
                    }
                },
                "fields": "userEnteredFormat(horizontalAlignment,verticalAlignment)"
            }
        },
        *dimension_requests
    ]

    res_batch = requests.post(batch_url, headers=headers, json={"requests": batch_requests}, timeout=30)
    if res_batch.status_code != 200:
        print(f"Warning: Formatting batch update returned status {res_batch.status_code}: {res_batch.text}")
    else:
        print("Formatting and column widths applied successfully!")

    duration = time.time() - start_time
    sheet_url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit#gid={TARGET_SHEET_ID}"
    print("\n" + "=" * 70)
    print(f"TRANSFER COMPLETE in {duration:.2f}s!")
    print(f"Total Rows: 501 (1 Header + 500 Documents)")
    print(f"Target Sheet URL: {sheet_url}")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="Populate 500 documents to Google Sheets 'Kết quả đích thực tế'")
    parser.add_argument("--dry-run", action="store_true", help="Prepare and validate data without writing to Google Sheets")
    args = parser.parse_args()

    populate_target_sheet(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
