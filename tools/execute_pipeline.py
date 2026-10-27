import os
import sys
import json
import time
import re
import csv
import subprocess
import concurrent.futures
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

GDRIVE_BIN = r"C:\Users\trant\.gemini\antigravity\bin\gdrive.cmd"
GSHEETS_BIN = r"C:\Users\trant\.gemini\antigravity\bin\gsheets.cmd"
DATA_FILE = r"c:\Workspaces\ai-document-sender\.tmp\prepared_500_documents.json"
TMP_DIR = Path(r"c:\Workspaces\ai-document-sender\.tmp")
STAGING_DIR = TMP_DIR / "staging_500_uploads"

def run_cmd(args, retries=1):
    full_cmd = ["cmd.exe", "/c"] + args
    for attempt in range(retries):
        res = subprocess.run(
            full_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            shell=False
        )
        if res.returncode == 0:
            return res.stdout.strip(), res.stderr.strip()
        time.sleep(1)
    raise RuntimeError(f"Command failed ({res.returncode}): {' '.join(full_cmd)}\nError: {res.stderr}\nOutput: {res.stdout}")

def extract_id(text):
    m = re.search(r"\(ID:\s*([a-zA-Z0-9_-]+)\)", text)
    if m:
        return m.group(1)
    m = re.search(r'"id":\s*"([a-zA-Z0-9_-]+)"', text)
    if m:
        return m.group(1)
    return None

def upload_worker(item, parent_folder_id):
    staged_path = item["staged_path"]
    stt = item["stt"]
    cmd = [GDRIVE_BIN, "mutate", "upload", staged_path, "--parent", parent_folder_id]
    
    for attempt in range(4):
        try:
            stdout, _ = run_cmd(cmd)
            file_id = extract_id(stdout)
            if file_id:
                link = f"https://drive.google.com/file/d/{file_id}/view"
                return stt, file_id, link, None
            else:
                return stt, None, None, f"Could not parse ID from: {stdout}"
        except Exception as e:
            if attempt == 3:
                return stt, None, None, str(e)
            time.sleep(1.5 * (attempt + 1))

def main():
    if not os.path.exists(DATA_FILE):
        print(f"Error: {DATA_FILE} not found!")
        sys.exit(1)

    with open(DATA_FILE, "r", encoding="utf-8") as fp:
        docs = json.load(fp)

    print(f"Loaded {len(docs)} documents.")

    # 1. Prepare Staging files with clean, unique, sorted names
    STAGING_DIR.mkdir(parents=True, exist_ok=True)
    print("Preparing staging hardlinks...")
    for doc in docs:
        src = Path(doc["pdf_path"])
        clean_ext = ".pdf"
        base_name = doc["pdf_filename"]
        if base_name.lower().endswith(".pdf"):
            base_name = base_name[:-4]
        # Clean special chars from filename
        safe_name = re.sub(r'[\\/*?:"<>|&]', '_', base_name)
        staged_name = f"{doc['folder_name']} - {safe_name}{clean_ext}"
        staged_path = STAGING_DIR / staged_name
        if staged_path.exists():
            staged_path.unlink()
        try:
            os.link(src, staged_path)
        except Exception:
            import shutil
            shutil.copy2(src, staged_path)
        doc["staged_path"] = str(staged_path)
        doc["staged_name"] = staged_name

    print("All staging files ready.")

    # 2. Create Google Drive Folder
    folder_name = "VPUB - 500 Van ban mau va Doi soat Noi nhan"
    print(f"\n[1/5] Creating Google Drive folder: '{folder_name}'...")
    stdout, _ = run_cmd([GDRIVE_BIN, "mutate", "mkdir", folder_name])
    main_folder_id = extract_id(stdout)
    if not main_folder_id:
        print(f"Failed to create folder. Output: {stdout}")
        sys.exit(1)
    folder_url = f"https://drive.google.com/drive/folders/{main_folder_id}"
    print(f"Folder created! ID: {main_folder_id}")
    print(f"Folder URL: {folder_url}")

    # 3. Upload 500 files to Drive folder
    print(f"\n[2/5] Uploading {len(docs)} files concurrently (10 threads)...")
    start_upload = time.time()
    url_map = {}
    errors = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(upload_worker, doc, main_folder_id): doc["stt"] for doc in docs}
        completed = 0
        for f in concurrent.futures.as_completed(futures):
            stt, file_id, link, err = f.result()
            if link:
                url_map[stt] = link
            else:
                errors.append((stt, err))
                url_map[stt] = "-"
            completed += 1
            if completed % 50 == 0 or completed == len(docs):
                elapsed = time.time() - start_upload
                print(f"   Progress: {completed}/{len(docs)} files uploaded ({elapsed:.1f}s) - {completed/elapsed:.1f} files/s")

    upload_duration = time.time() - start_upload
    print(f"Upload complete in {upload_duration:.1f}s. Successful: {len(docs) - len(errors)}, Errors: {len(errors)}")

    # 4. Generate CSV for Google Sheet
    print(f"\n[3/5] Generating CSV dataset with {len(docs)} documents...")
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

    print(f"CSV generated with {total_rows} rows at: {csv_file}")

    # 5. Create Google Spreadsheet
    sheet_title = "Thong ke doi soat Noi nhan 500 van ban VPUB (<= 13116)"
    print(f"\n[4/5] Creating Google Spreadsheet: '{sheet_title}'...")
    stdout, _ = run_cmd([GSHEETS_BIN, "mutate", "create", "--title", sheet_title])
    spreadsheet_id = extract_id(stdout)
    if not spreadsheet_id:
        print(f"Failed to create spreadsheet. Output: {stdout}")
        sys.exit(1)
    sheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"
    print(f"Spreadsheet created! ID: {spreadsheet_id}")

    # Move Spreadsheet into the parent folder
    print(f"Moving spreadsheet into folder {main_folder_id}...")
    run_cmd([GDRIVE_BIN, "mutate", "mv", spreadsheet_id, main_folder_id])

    # Rename initial sheet to Sheet1 if needed and import CSV
    try:
        run_cmd([GSHEETS_BIN, "mutate", "rename-sheet", spreadsheet_id, "--sheet-id", "0", "--title", "Sheet1"])
    except Exception:
        pass

    print(f"\n[5/5] Importing CSV data ({total_rows} rows) into Google Sheet...")
    import_out, _ = run_cmd([GSHEETS_BIN, "mutate", "import-csv", spreadsheet_id, str(csv_file), "--sheet", "Sheet1"])
    print(f"Import status: {import_out}")

    # Format header row: bold, background color, center align, freeze row
    print("Formatting Google Sheet...")
    try:
        run_cmd([GSHEETS_BIN, "mutate", "format", spreadsheet_id, "--sheet-id", "0", "--start-row", "0", "--end-row", "1", "--start-col", "0", "--end-col", "6", "--bold", "--bg-color", "#1A73E8", "--fg-color", "#FFFFFF", "--align", "CENTER", "--wrap"])
        run_cmd([GSHEETS_BIN, "mutate", "freeze", spreadsheet_id, "--sheet-id", "0", "--rows", "1"])
        run_cmd([GSHEETS_BIN, "mutate", "set-col-width", spreadsheet_id, "--sheet-id", "0", "--start-col", "0", "--end-col", "1", "--pixels", "60"])
        run_cmd([GSHEETS_BIN, "mutate", "set-col-width", spreadsheet_id, "--sheet-id", "0", "--start-col", "1", "--end-col", "2", "--pixels", "160"])
        run_cmd([GSHEETS_BIN, "mutate", "set-col-width", spreadsheet_id, "--sheet-id", "0", "--start-col", "2", "--end-col", "3", "--pixels", "350"])
        run_cmd([GSHEETS_BIN, "mutate", "set-col-width", spreadsheet_id, "--sheet-id", "0", "--start-col", "3", "--end-col", "4", "--pixels", "300"])
        run_cmd([GSHEETS_BIN, "mutate", "set-col-width", spreadsheet_id, "--sheet-id", "0", "--start-col", "4", "--end-col", "5", "--pixels", "350"])
        run_cmd([GSHEETS_BIN, "mutate", "set-col-width", spreadsheet_id, "--sheet-id", "0", "--start-col", "5", "--end-col", "6", "--pixels", "250"])
    except Exception as e:
        print(f"Format notice: {e}")

    # Save summary
    summary = {
        "folder_name": folder_name,
        "folder_id": main_folder_id,
        "folder_url": folder_url,
        "spreadsheet_id": spreadsheet_id,
        "spreadsheet_url": sheet_url,
        "total_documents": len(docs),
        "total_rows": total_rows,
        "upload_duration_seconds": upload_duration,
        "errors": errors
    }
    with open(TMP_DIR / "final_run_summary.json", "w", encoding="utf-8") as fp:
        json.dump(summary, fp, ensure_ascii=False, indent=2)

    print("\n" + "=" * 80)
    print("ALL TASKS COMPLETED SUCCESSFULLY!")
    print(f"Folder URL:      {folder_url}")
    print(f"Spreadsheet URL: {sheet_url}")
    print(f"Total Documents: {len(docs)}")
    print(f"Total Rows:      {total_rows}")
    print("=" * 80)

if __name__ == "__main__":
    main()
