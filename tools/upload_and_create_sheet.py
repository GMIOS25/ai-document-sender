import os
import sys
import json
import time
import subprocess
import concurrent.futures
import csv
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

GDRIVE_BIN = r"C:\Users\trant\.gemini\antigravity\bin\gdrive.cmd"
GSHEETS_BIN = r"C:\Users\trant\.gemini\antigravity\bin\gsheets.cmd"
DATA_FILE = r"c:\Workspaces\ai-document-sender\.tmp\prepared_500_documents.json"
TMP_DIR = Path(r"c:\Workspaces\ai-document-sender\.tmp")

def run_cmd(args, check=True):
    res = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", shell=True)
    if check and res.returncode != 0:
        raise RuntimeError(f"Command failed ({res.returncode}): {' '.join(args)}\nError: {res.stderr}\nOutput: {res.stdout}")
    return res.stdout.strip(), res.stderr.strip()

def run_json(args):
    stdout, _ = run_cmd(args)
    try:
        return json.loads(stdout)
    except Exception:
        # Maybe text followed by JSON
        idx = stdout.find("{")
        if idx != -1:
            return json.loads(stdout[idx:])
        raise

def upload_single_file(item, parent_folder_id):
    pdf_path = item["pdf_path"]
    filename = item["pdf_filename"]
    # Upload via gdrive
    cmd = [GDRIVE_BIN, "mutate", "upload", f'"{pdf_path}"', "--parent", parent_folder_id, "--json"]
    try:
        stdout, _ = run_cmd(cmd)
        data = json.loads(stdout)
        file_id = data.get("id") or data.get("file_id")
        file_url = data.get("webViewLink") or f"https://drive.google.com/file/d/{file_id}/view"
        return item["stt"], file_id, file_url
    except Exception as e:
        return item["stt"], None, f"ERROR: {e}"

def main():
    if not os.path.exists(DATA_FILE):
        print(f"Error: {DATA_FILE} not found. Run prepare_data_500.py first.")
        sys.exit(1)

    with open(DATA_FILE, "r", encoding="utf-8") as fp:
        docs = json.load(fp)

    print(f"Loaded {len(docs)} documents.")

    # 1. Create main folder on Google Drive
    folder_name = "VPUB - 500 Van ban mau & Doi soat Noi nhan"
    print(f"Creating Drive folder: '{folder_name}'...")
    cmd = [GDRIVE_BIN, "mutate", "mkdir", f'"{folder_name}"', "--json"]
    folder_res = run_json(cmd)
    main_folder_id = folder_res.get("id") or folder_res.get("file_id")
    print(f"Main Folder created! ID: {main_folder_id}")

    # Create subfolder for documents
    subfolder_name = "500_Tep_Van_ban_goc"
    print(f"Creating Subfolder: '{subfolder_name}'...")
    sub_res = run_json([GDRIVE_BIN, "mutate", "mkdir", f'"{subfolder_name}"', "--parent", main_folder_id, "--json"])
    docs_folder_id = sub_res.get("id") or sub_res.get("file_id")
    print(f"Docs Folder created! ID: {docs_folder_id}")

    # 2. Concurrently upload 500 documents
    print(f"Starting upload of {len(docs)} files with 8 threads...")
    start_time = time.time()
    url_map = {}

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(upload_single_file, doc, docs_folder_id): doc["stt"] for doc in docs}
        completed = 0
        for f in concurrent.futures.as_completed(futures):
            stt, file_id, file_url = f.result()
            url_map[stt] = file_url
            completed += 1
            if completed % 50 == 0 or completed == len(docs):
                print(f"Uploaded {completed}/{len(docs)} files ({time.time() - start_time:.1f}s)")

    print(f"Upload complete in {time.time() - start_time:.1f}s.")

    # 3. Generate CSV for Google Sheet
    csv_file = TMP_DIR / "thong_ke_doi_soat_500_van_ban.csv"
    headers = [
        "STT",
        "Số hiệu văn bản",
        "Trích yếu",
        "Nơi nhận 1 (Kết quả từ backend liệt kê ra, chưa lookup)",
        "Nơi nhận 2 (Kết quả đã lookup từ database)",
        "Link văb bản (link liên kết đến tài liệu chính theo văn bản)"
    ]

    total_rows = 0
    with open(csv_file, "w", encoding="utf-8-sig", newline="") as fp:
        writer = csv.writer(fp)
        writer.writerow(headers)
        for doc in docs:
            stt = doc["stt"]
            so_hieu = doc["so_hieu"]
            trich_yeu = doc["trich_yeu"]
            doc_link = url_map.get(stt, "")

            recipients = doc["recipients"]
            for idx, (r1, r2) in enumerate(recipients):
                if idx == 0:
                    writer.writerow([stt, so_hieu, trich_yeu, r1, r2, doc_link])
                else:
                    writer.writerow(["", "", "", r1, r2, ""])
                total_rows += 1

    print(f"Generated CSV with {total_rows} rows at {csv_file}")

    # 4. Create Google Spreadsheet
    sheet_title = "Thống kê đối soát Nơi nhận 500 văn bản VPUB (<= 13116)"
    print(f"Creating Google Spreadsheet: '{sheet_title}'...")
    create_res = run_json([GSHEETS_BIN, "mutate", "create", "--title", f'"{sheet_title}"', "--json"])
    spreadsheet_id = create_res.get("spreadsheetId") or create_res.get("id")
    print(f"Spreadsheet created! ID: {spreadsheet_id}")

    # Move Spreadsheet to main folder
    print("Moving Spreadsheet into main folder...")
    run_cmd([GDRIVE_BIN, "mutate", "mv", spreadsheet_id, main_folder_id])

    # 5. Import CSV into Google Sheet
    print("Importing CSV data into Google Sheet...")
    run_cmd([GSHEETS_BIN, "mutate", "import-csv", spreadsheet_id, f'"{str(csv_file)}"', "--sheet", "Sheet1"])
    print("CSV imported successfully!")

    # 6. Format Header
    print("Formatting Header row...")
    try:
        run_cmd([GSHEETS_BIN, "mutate", "format", spreadsheet_id, "--sheet-id", "0", "--start-row", "0", "--end-row", "1", "--start-col", "0", "--end-col", "6", "--bold", "--bg-color", '"#1A73E8"', "--fg-color", '"#FFFFFF"', "--align", "CENTER", "--wrap"])
        run_cmd([GSHEETS_BIN, "mutate", "freeze", spreadsheet_id, "--sheet-id", "0", "--rows", "1"])
    except Exception as e:
        print(f"Formatting warning: {e}")

    # Output links
    sheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"
    folder_url = f"https://drive.google.com/drive/folders/{main_folder_id}"

    result_summary = {
        "folder_name": folder_name,
        "folder_id": main_folder_id,
        "folder_url": folder_url,
        "spreadsheet_id": spreadsheet_id,
        "spreadsheet_url": sheet_url,
        "total_documents": len(docs),
        "total_rows": total_rows
    }

    summary_file = TMP_DIR / "final_run_summary.json"
    with open(summary_file, "w", encoding="utf-8") as fp:
        json.dump(result_summary, fp, ensure_ascii=False, indent=2)

    print("\n" + "=" * 80)
    print("SUCCESSFULLY COMPLETED ALL TASKS!")
    print(f"Google Drive Folder URL: {folder_url}")
    print(f"Google Spreadsheet URL:  {sheet_url}")
    print("=" * 80)

if __name__ == "__main__":
    main()
