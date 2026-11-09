"""
tools/execute_pipeline_13594_13117.py

End-to-end automation for VPUB documents 13594 - 13117:
1. Scan and extract all 475 crawled documents in range 13594-13117.
2. Concurrently upload all 475 PDF files to Google Drive subfolder 'Tệp Văn bản gốc (13594-13117)'.
3. Extract mentions from PDFs and perform database lookup mapping.
4. Add default recipients with note '(Mặc định)'.
5. Create Google Spreadsheet with tabs:
   - 'Test 1'
   - 'Kết quả đích thực tế'
   - 'Thống kê'
6. Populate all sheets, apply header formats, and calculate comprehensive statistics.
"""

import sys
import os
import json
import time
import re
import pathlib
import unicodedata
import sqlite3
import concurrent.futures
from typing import Dict, List, Any, Tuple
import requests

sys.stdout.reconfigure(encoding='utf-8')

# Paths
WORKSPACE_ROOT = pathlib.Path(r"c:\Workspaces\ai-document-sender")
SOURCE_DIR = WORKSPACE_ROOT / "resources" / "văn bản mẫu" / "vpub" / "Hợp lệ"
DB_PATH = WORKSPACE_ROOT / "resources" / "tenants" / "vpub" / "lookup.db"
TOKEN_PATH = pathlib.Path(r"C:\Users\trant\.gemini\antigravity\plugin_data\gsheets\token.json")
TMP_DIR = WORKSPACE_ROOT / ".tmp"
TMP_DIR.mkdir(parents=True, exist_ok=True)
CACHE_FILE = TMP_DIR / "drive_upload_cache_13594_13117.json"

# Google Drive IDs
MAIN_FOLDER_ID = "1FSGKKT_Sa1CMaa4TAOXtnREzyVtmMpsi"
SUBFOLDER_ID = "19jaEVB0maeVEgFP23LLMhMxz_RlIW9c5"

# Add src to sys.path
sys.path.insert(0, str(WORKSPACE_ROOT / "src"))
sys.path.insert(0, str(WORKSPACE_ROOT / "tools"))

from ai_document_sender.config import Settings
from ai_document_sender.extraction import _read_pages, extract_rule_mentions
from lookup_service import RecipientLookupService


class GoogleClient:
    def __init__(self, token_path: pathlib.Path = TOKEN_PATH):
        self.token_path = token_path
        self._load_token()

    def _load_token(self):
        with open(self.token_path, "r", encoding="utf-8") as f:
            self.data = json.load(f)
        self.access_token = self.data.get("token", {}).get("access_token")

    def refresh(self):
        payload = {
            "client_id": self.data["client_id"],
            "client_secret": self.data["client_secret"],
            "refresh_token": self.data["token"]["refresh_token"],
            "grant_type": "refresh_token"
        }
        resp = requests.post("https://oauth2.googleapis.com/token", data=payload, timeout=20)
        if resp.status_code == 200:
            new_data = resp.json()
            self.access_token = new_data["access_token"]
            self.data["token"]["access_token"] = self.access_token
            with open(self.token_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2)
            print("OAuth access token refreshed successfully.")
        else:
            raise RuntimeError(f"Failed to refresh token: {resp.status_code} {resp.text}")

    def request(self, method: str, url: str, **kwargs) -> requests.Response:
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {self.access_token}"
        res = requests.request(method, url, headers=headers, **kwargs)
        if res.status_code == 401:
            print("Received 401 Unauthorized, refreshing token...")
            self.refresh()
            headers["Authorization"] = f"Bearer {self.access_token}"
            res = requests.request(method, url, headers=headers, **kwargs)
        return res


def clean_mention(raw: str) -> str:
    raw = raw.strip()
    raw = re.sub(r"[;,\.]+$", "", raw).strip()
    return raw


class EntityResolver:
    def __init__(self, db_path: pathlib.Path):
        self.lookup_service = RecipientLookupService(db_path)

    def resolve_single_entity(self, query: str) -> str:
        q = query.strip()
        if not q or q.upper() in ["VT", "LƯU VT", "LƯU: VT", "NHƯ TRÊN", "NHƯ KÍNH GỬI"]:
            return "-"

        # Key leadership roles
        if q in ["CT", "Chủ tịch", "Chủ tịch UBND tỉnh"]:
            return "Phạm Anh Tuấn - Chủ tịch UBND tỉnh (Lãnh đạo UBND tỉnh)"
        if q in ["CVP", "Chánh Văn phòng", "Chánh Văn phòng UBND tỉnh"]:
            return "Nguyễn Xuân Vĩnh - Chánh Văn phòng UBND tỉnh (Lãnh đạo Văn phòng UBND tỉnh)"
        if q in ["PCVNN", "PVPNN"]:
            return "Trần Đình Triết - Phó Chánh Văn phòng (Lãnh đạo Văn phòng UBND tỉnh)"
        if q in ["PCVX", "PVPX"]:
            return "Phan Đình Hải - Phó Chánh Văn phòng (Lãnh đạo Văn phòng UBND tỉnh)"
        if q in ["PCVTH", "PVPTH"]:
            return "Lê Huy Vũ - Phó Chánh Văn phòng, Thư ký Chủ tịch (Lãnh đạo Văn phòng UBND tỉnh)"
        if q in ["các PCT UBND tỉnh", "Lãnh đạo UBND tỉnh"]:
            return "Lãnh đạo UBND tỉnh (Nội bộ UBND tỉnh)"
        if q in ["CVP, các PCVP UBND tỉnh", "CVP và các PCVP"]:
            return (
                "Nguyễn Xuân Vĩnh - Chánh Văn phòng UBND tỉnh (Lãnh đạo Văn phòng UBND tỉnh)\n"
                "Phan Đình Hải - Phó Chánh Văn phòng (Lãnh đạo Văn phòng UBND tỉnh)\n"
                "Trần Đình Triết - Phó Chánh Văn phòng (Lãnh đạo Văn phòng UBND tỉnh)\n"
                "Lê Huy Vũ - Phó Chánh Văn phòng, Thư ký Chủ tịch (Lãnh đạo Văn phòng UBND tỉnh)"
            )

        # Standard lookup
        res = self.lookup_service.lookup(q, limit=1)
        if res:
            top = res[0]
            if q.upper() == "VT" and "VTC" in top.get("display_name", ""):
                return "-"
            d_name = top.get("display_name", "").strip()
            code = top.get("code", "").strip()
            if code and code not in d_name:
                return f"{d_name} ({code})"
            return d_name
        return "-"

    def resolve_mention_text(self, raw_m: str) -> str:
        m = clean_mention(raw_m)

        # Commune lists pattern: "UBND các xã, phường: A, B, C"
        commune_match = re.match(r"^(?:UBND|Ủy ban nhân dân)\s+các\s+(?:xã|phường|thị trấn)[^:]*:\s*(.+)$", m, re.I)
        if commune_match:
            names = [x.strip() for x in re.split(r"[,;]\s*", commune_match.group(1)) if x.strip()]
            resolved_list = []
            for n in names:
                q_commune = f"UBND xã {n}" if not n.lower().startswith(("xã", "phường", "thị trấn")) else f"UBND {n}"
                r = self.lookup_service.lookup(q_commune, limit=1)
                if not r:
                    r = self.lookup_service.lookup(n, limit=1)
                if r:
                    top = r[0]
                    d = top["display_name"]
                    c = top.get("code", "")
                    resolved_list.append(f"{d} ({c})" if c and c not in d else d)
                else:
                    resolved_list.append(f"UBND xã {n} - Tỉnh Gia Lai")
            return "\n".join(resolved_list)

        # Multi-unit lists: "Sở Công Thương, Sở Xây dựng"
        if "," in m and not re.search(r"\b(?:Long|Hưng|Thịnh|Vượng|Phát|Việt Nam)\b", m):
            parts = [p.strip() for p in re.split(r"[,;]\s*", m) if p.strip()]
            if len(parts) > 1 and all(len(p) > 3 for p in parts):
                resolved_parts = []
                for p in parts:
                    res = self.resolve_single_entity(p)
                    if res != "-":
                        resolved_parts.append(res)
                if resolved_parts:
                    return "\n".join(resolved_parts)

        return self.resolve_single_entity(m)


def upload_pdf_file(client: GoogleClient, file_info: dict, subfolder_id: str) -> Tuple[int, str, str, str]:
    stt = file_info["stt"]
    pdf_path = file_info["pdf_path"]
    filename = file_info["filename"]

    if not pdf_path or not os.path.exists(pdf_path):
        return stt, None, "-", "File not found"

    boundary = "==============upload_boundary=="
    meta_json = json.dumps({"name": filename, "parents": [subfolder_id]})

    try:
        with open(pdf_path, "rb") as f:
            file_bytes = f.read()

        body = (
            f"--{boundary}\r\n"
            "Content-Type: application/json; charset=UTF-8\r\n\r\n"
            f"{meta_json}\r\n"
            f"--{boundary}\r\n"
            "Content-Type: application/pdf\r\n\r\n"
        ).encode("utf-8") + file_bytes + f"\r\n--{boundary}--\r\n".encode("utf-8")

        headers = {
            "Content-Type": f"multipart/related; boundary={boundary}",
            "Content-Length": str(len(body))
        }

        r = client.request(
            "POST",
            "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart&fields=id,name,webViewLink",
            headers=headers,
            data=body,
            timeout=60
        )

        if r.status_code == 200:
            res_data = r.json()
            file_id = res_data["id"]
            link = f"https://drive.google.com/file/d/{file_id}/view"
            return stt, file_id, link, None
        else:
            return stt, None, "-", f"HTTP {r.status_code}: {r.text}"
    except Exception as e:
        return stt, None, "-", str(e)


def main():
    print("=" * 80)
    print("STARTING VPUB 13594 - 13117 PIPELINE")
    print("=" * 80)

    settings = Settings()
    client = GoogleClient()
    resolver = EntityResolver(DB_PATH)

    # 1. Gather all documents in range 13117 <= num <= 13594
    candidate_folders = []
    for f in SOURCE_DIR.iterdir():
        if not f.is_dir():
            continue
        m = re.match(r"^(\d+)", f.name)
        if m and 13117 <= int(m.group(1)) <= 13594:
            candidate_folders.append((int(m.group(1)), f))

    candidate_folders.sort(key=lambda x: x[0], reverse=True)
    print(f"Total documents found in range 13594-13117: {len(candidate_folders)}")
    print(f"Top doc: {candidate_folders[0][0]} ({candidate_folders[0][1].name})")
    print(f"Last doc: {candidate_folders[-1][0]} ({candidate_folders[-1][1].name})")

    # 2. Parse metadata and attachments for all documents
    docs = []
    for idx, (doc_num, folder) in enumerate(candidate_folders, 1):
        cpx_file = folder / "view.cpx"
        sign_number = folder.name
        subject = ""
        if cpx_file.exists():
            try:
                with open(cpx_file, "r", encoding="utf-8", errors="replace") as fp:
                    cpx_data = json.load(fp)
                    ed = cpx_data.get("ed", {})
                    sign_number = ed.get("signNumber") or folder.name
                    subject = ed.get("subject") or ""
            except Exception:
                pass

        # Ground truth
        txt_file = folder / "kết_quả_gửi_đi.txt"
        handlers = []
        receivers = []
        if txt_file.exists():
            content = txt_file.read_text(encoding="utf-8", errors="replace")
            for line in content.splitlines():
                line = line.strip()
                if line.startswith("Người xử lí:") or line.startswith("Người theo dõi:"):
                    parts = line.split(":", 1)[1].split(";")
                    for p in parts:
                        p = p.strip()
                        if p and p not in handlers:
                            handlers.append(p)
                elif line.startswith("Đơn vị nhận:"):
                    parts = line.split(":", 1)[1].split(";")
                    for u in parts:
                        u = u.strip()
                        if u and u not in receivers:
                            receivers.append(u)

        # PDF file (using extended path for long paths)
        pdf_file = None
        for p in folder.glob("*.pdf"):
            pdf_file = p
            break

        clean_pdf_path = (r"\\?\\" + str(pdf_file.resolve())) if pdf_file else None
        safe_name = re.sub(r'[\\/*?:"<>|&]', '_', pdf_file.name) if pdf_file else f"{folder.name}.pdf"
        drive_filename = f"{folder.name} - {safe_name}"

        docs.append({
            "stt": idx,
            "doc_num": doc_num,
            "folder_name": folder.name,
            "sign_number": sign_number,
            "subject": subject,
            "handlers": handlers,
            "receivers": receivers,
            "pdf_path": clean_pdf_path,
            "filename": drive_filename
        })

    # 3. Concurrently upload PDFs to Google Drive
    print(f"\n[Step 1/4] Uploading {len(docs)} PDF files to Google Drive subfolder...")
    upload_cache = {}
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                upload_cache = json.load(f)
            print(f"Loaded existing upload cache with {len(upload_cache)} uploaded files.")
        except Exception:
            upload_cache = {}

    to_upload = [d for d in docs if str(d["stt"]) not in upload_cache]
    print(f"Need to upload: {len(to_upload)} files.")

    if to_upload:
        start_time = time.time()
        completed = 0
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            futures = {executor.submit(upload_pdf_file, client, doc, SUBFOLDER_ID): doc["stt"] for doc in to_upload}
            for f in concurrent.futures.as_completed(futures):
                stt, file_id, link, err = f.result()
                if link and link != "-":
                    upload_cache[str(stt)] = {"file_id": file_id, "link": link}
                else:
                    print(f"Warning: upload failed for STT {stt}: {err}")
                    upload_cache[str(stt)] = {"file_id": None, "link": "-"}
                completed += 1
                if completed % 25 == 0 or completed == len(to_upload):
                    elapsed = time.time() - start_time
                    print(f"   Uploaded {completed}/{len(to_upload)} files ({elapsed:.1f}s) - {completed/elapsed:.1f} files/s")

        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(upload_cache, f, ensure_ascii=False, indent=2)
        print("Upload completed and cache saved.")

    # Attach links to docs
    for d in docs:
        cache_entry = upload_cache.get(str(d["stt"]), {})
        d["link"] = cache_entry.get("link", "-")

    # 4. Extract mentions from PDFs and perform lookup mapping
    print(f"\n[Step 2/4] Extracting mentions and performing lookup mapping...")
    start_lookup = time.time()
    for idx, doc in enumerate(docs, 1):
        mentions_pairs = []
        if doc["pdf_path"] and os.path.exists(doc["pdf_path"]):
            try:
                pages = _read_pages(doc["pdf_path"], settings)
                mentions, _ = extract_rule_mentions(pages)
                for m in mentions:
                    raw = m.raw.strip()
                    if not raw:
                        continue
                    mapped = resolver.resolve_mention_text(raw)
                    # Note rule: if mapped is certain, note is empty. If unmapped or hyphen, note is "-"
                    note = "" if mapped != "-" else "-"
                    mentions_pairs.append((raw, mapped, note))
            except Exception as e:
                mentions_pairs.append(("-", "-", f"Error reading PDF: {e}"))
        else:
            mentions_pairs.append(("-", "-", "Không có tệp PDF"))

        # ALWAYS append the default recipients as specified by the user:
        # "Lưu ý: Có một số kết quả là mặc định như tổ công tác hay ban Trung tâm Phục vụ hành chính công tỉnh Gia Lai
        # là các kết quả mặc định, không có kết quả ánh xạ từ nơi nhận 1, thì vẫn để trong nơi nhận 2 với ghi chú (Mặc định)"
        mentions_pairs.append(("", "Tổ công tác (Tổ công tác)", "(Mặc định)"))
        mentions_pairs.append(("", "Trung tâm Phục vụ hành chính công tỉnh Gia Lai", "(Mặc định)"))

        doc["test1_rows"] = mentions_pairs

        if idx % 50 == 0 or idx == len(docs):
            print(f"   Processed extraction & lookup for {idx}/{len(docs)} documents ({time.time() - start_lookup:.1f}s)")

    # 5. Create Google Spreadsheet
    print(f"\n[Step 3/4] Creating Google Spreadsheet...")
    spreadsheet_title = "Thống kê đối soát nơi nhận văn bản VPUB (13594-13117)"
    sheet_meta = {
        "properties": {
            "title": spreadsheet_title
        },
        "sheets": [
            {"properties": {"title": "Test 1", "sheetId": 0}},
            {"properties": {"title": "Kết quả đích thực tế", "sheetId": 1}},
            {"properties": {"title": "Thống kê", "sheetId": 2}}
        ]
    }
    r = client.request("POST", "https://sheets.googleapis.com/v4/spreadsheets", json=sheet_meta)
    if r.status_code != 200:
        raise RuntimeError(f"Failed to create spreadsheet: {r.status_code} {r.text}")

    created_data = r.json()
    spreadsheet_id = created_data["spreadsheetId"]
    spreadsheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"
    print(f"Spreadsheet created! ID: {spreadsheet_id}")
    print(f"Spreadsheet URL: {spreadsheet_url}")

    # Move Spreadsheet into Main Folder
    print(f"Moving spreadsheet into Google Drive main folder: {MAIN_FOLDER_ID}...")
    move_url = f"https://www.googleapis.com/drive/v3/files/{spreadsheet_id}?addParents={MAIN_FOLDER_ID}&fields=id,parents"
    client.request("PATCH", move_url)

    # Make spreadsheet public readable
    client.request(
        "POST",
        f"https://www.googleapis.com/drive/v3/files/{spreadsheet_id}/permissions",
        json={"role": "reader", "type": "anyone"}
    )

    # 6. Populate Sheet 1: "Test 1"
    print("\n[Step 4/4] Populating worksheets...")
    test1_header = [
        "STT",
        "Số hiệu văn bản",
        "Trích yếu",
        "Nơi nhận 1 (Kết quả từ backend liệt kê ra, chưa lookup)",
        "Nơi nhận 2 (Kết quả đã lookup từ database)",
        "Ghi chú",
        "Link liên kết đến tài liệu chính theo văn bản"
    ]

    test1_values = [test1_header]
    for doc in docs:
        stt = doc["stt"]
        sign_number = doc["sign_number"]
        subject = doc["subject"]
        link = doc["link"]

        rows = doc["test1_rows"]
        for idx, (r1, r2, note) in enumerate(rows):
            if idx == 0:
                test1_values.append([stt, sign_number, subject, r1, r2, note, link])
            else:
                test1_values.append(["", "", "", r1, r2, note, ""])

    print(f"Uploading 'Test 1' ({len(test1_values)} rows)...")
    # Batch append/update Test 1
    chunk_size = 1000
    for i in range(0, len(test1_values), chunk_size):
        chunk = test1_values[i:i + chunk_size]
        start_row = i + 1
        range_str = f"'Test 1'!A{start_row}"
        r = client.request(
            "PUT",
            f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{range_str}?valueInputOption=USER_ENTERED",
            json={"values": chunk}
        )
        if r.status_code != 200:
            print(f"Warning writing Test 1 chunk {i}: {r.status_code} {r.text}")

    # 7. Populate Sheet 2: "Kết quả đích thực tế"
    target_header = [
        "STT",
        "Số hiệu văn bản",
        "Trích yếu",
        "Kết quả gửi đi kèm (Đích thực tế)",
        "Đơn vị nhận (Dữ liệu mẫu)",
        "Link liên kết đến tài liệu chính theo văn bản"
    ]

    target_values = [target_header]
    for doc in docs:
        stt = doc["stt"]
        sign_number = doc["sign_number"]
        subject = doc["subject"]
        link = doc["link"]
        handlers_str = "\n".join(doc["handlers"])
        receivers_str = "\n".join(doc["receivers"])
        target_values.append([stt, sign_number, subject, handlers_str, receivers_str, link])

    print(f"Uploading 'Kết quả đích thực tế' ({len(target_values)} rows)...")
    client.request(
        "PUT",
        f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/'Kết quả đích thực tế'!A1?valueInputOption=USER_ENTERED",
        json={"values": target_values}
    )

    # 8. Compute Statistics & Populate Sheet 3: "Thống kê"
    print("Computing evaluation statistics...")
    total_docs = len(docs)
    total_pdf_files = sum(1 for d in docs if d["pdf_path"])
    total_test1_rows = len(test1_values) - 1
    total_default_rows = total_docs * 2  # 2 default rows per doc

    # Mention extraction stats
    docs_with_extracted_mentions = 0
    total_extracted_mentions = 0
    total_mapped_recipients = 0
    unmapped_mentions = 0

    # Verification against ground truth
    total_ground_truth_handlers = sum(len(d["handlers"]) for d in docs)
    total_ground_truth_receivers = sum(len(d["receivers"]) for d in docs)
    total_ground_truth_targets = total_ground_truth_handlers + total_ground_truth_receivers

    tp = 0
    fp = 0
    fn = 0
    exact_matches = 0

    for doc in docs:
        # Predicted entities from Nơi nhận 2 (excluding "-" and empty)
        predicted_set = set()
        for r1, r2, note in doc["test1_rows"]:
            if r2 and r2 != "-":
                for item in r2.split("\n"):
                    item_clean = clean_mention(item)
                    if item_clean and item_clean != "-":
                        predicted_set.add(item_clean)

        # Ground truth set
        gt_set = set()
        for h in doc["handlers"]:
            h_clean = clean_mention(h)
            if h_clean:
                gt_set.add(h_clean)
        for r in doc["receivers"]:
            r_clean = clean_mention(r)
            if r_clean:
                gt_set.add(r_clean)

        # Check mention stats
        doc_mentions = [r for r in doc["test1_rows"] if r[2] != "(Mặc định)"]
        if doc_mentions and any(r[0] and r[0] != "-" for r in doc_mentions):
            docs_with_extracted_mentions += 1
            for r1, r2, note in doc_mentions:
                if r1 and r1 != "-":
                    total_extracted_mentions += 1
                    if r2 and r2 != "-":
                        total_mapped_recipients += 1
                    else:
                        unmapped_mentions += 1

        # Match prediction against ground truth
        # Simplified normalized matching for KPI calculation
        matched_gt = set()
        for pred in predicted_set:
            norm_p = unicodedata.normalize("NFC", pred).lower()
            matched = False
            for gt in gt_set:
                norm_gt = unicodedata.normalize("NFC", gt).lower()
                if norm_p in norm_gt or norm_gt in norm_p:
                    matched = True
                    matched_gt.add(gt)
                    break
            if matched:
                tp += 1
            else:
                fp += 1

        fn += len(gt_set - matched_gt)
        if len(matched_gt) == len(gt_set) and fp == 0:
            exact_matches += 1

    precision = (tp / (tp + fp)) * 100 if (tp + fp) > 0 else 0
    recall = (tp / (tp + fn)) * 100 if (tp + fn) > 0 else 0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

    print(f"\n--- THỐNG KÊ KẾT QUẢ ĐỐI SOÁT ---")
    print(f"Tổng số văn bản: {total_docs}")
    print(f"Số văn bản có tệp PDF: {total_pdf_files}")
    print(f"Số văn bản trích xuất thành công nơi nhận: {docs_with_extracted_mentions}/{total_pdf_files} ({docs_with_extracted_mentions/total_pdf_files*100:.1f}%)")
    print(f"Tổng số lượt nơi nhận trích xuất (Nơi nhận 1): {total_extracted_mentions}")
    print(f"Số lượt lookup thành công vào Nơi nhận 2: {total_mapped_recipients} ({total_mapped_recipients/total_extracted_mentions*100:.1f}%)")
    print(f"Số lượt không tra cứu được (-): {unmapped_mentions}")
    print(f"Số dòng mặc định đã gán (Tổ công tác & TTPVHCC): {total_default_rows} (100% văn bản)")
    print(f"Đích thực tế từ dữ liệu cào: {total_ground_truth_targets} lượt")
    print(f"Precision (Độ chính xác): {precision:.2f}%")
    print(f"Recall (Độ bao phủ): {recall:.2f}%")
    print(f"F1-score: {f1:.2f}%")

    # Populate Sheet 3: "Thống kê"
    thong_ke_values = [
        ["BÁO CÁO THỐNG KÊ ĐỐI SOÁT NƠI NHẬN VĂN BẢN VPUB (13594 - 13117)", "", ""],
        ["", "", ""],
        ["Chỉ số tổng quan", "Giá trị", "Ghi chú"],
        ["Tổng số văn bản kiểm thử", total_docs, "Từ 13594 đến 13117"],
        ["Tổng số tệp PDF văn bản gốc", total_pdf_files, "Đã lưu trữ và upload Google Drive"],
        ["Số văn bản trích xuất được Nơi nhận 1", docs_with_extracted_mentions, f"{docs_with_extracted_mentions/total_pdf_files*100:.1f}% trên tổng số văn bản có PDF"],
        ["Tổng số dòng trong thẻ Test 1", total_test1_rows, "Gồm nơi nhận trích xuất và nơi nhận mặc định"],
        ["Tổng số nơi nhận trích xuất từ PDF (Nơi nhận 1)", total_extracted_mentions, "Kết quả từ backend/LLM đọc ra"],
        ["Số nơi nhận tra cứu thành công (Nơi nhận 2)", total_mapped_recipients, f"Tỷ lệ thành công: {total_mapped_recipients/total_extracted_mentions*100:.1f}%"],
        ["Số nơi nhận chưa tra cứu được (-)", unmapped_mentions, "Cần bổ sung danh bạ hoặc quy tắc"],
        ["Số lượt gán mặc định (Tổ công tác & TTPVHCC)", total_default_rows, "Mỗi văn bản 2 mục mặc định (100%)"],
        ["Tổng số lượt đích thực tế (Đã cào)", total_ground_truth_targets, "Người xử lý, người theo dõi và đơn vị nhận"],
        ["", "", ""],
        ["Chỉ số chất lượng mô hình & Tra cứu", "Tỷ lệ", "Đánh giá"],
        ["Precision (Độ chính xác)", f"{precision:.2f}%", "Tỷ lệ dự đoán đúng trên tổng dự đoán"],
        ["Recall (Độ bao phủ)", f"{recall:.2f}%", "Tỷ lệ phát hiện đúng trên tổng đích thực tế"],
        ["F1-Score", f"{f1:.2f}%", "Trung bình điều hòa giữa Precision và Recall"],
        ["", "", ""],
        ["Liên kết tài nguyên", "Đường dẫn", ""],
        ["Thư mục Google Drive chính", f"https://drive.google.com/drive/folders/{MAIN_FOLDER_ID}", "Chứa tệp PDF và bảng tính"],
        ["Thư mục Tệp văn bản gốc", f"https://drive.google.com/drive/folders/{SUBFOLDER_ID}", "475 tệp PDF văn bản gốc"],
        ["Tài liệu bảng tính Google Sheets", spreadsheet_url, "3 thẻ sheets: Test 1, Kết quả đích thực tế, Thống kê"]
    ]

    client.request(
        "PUT",
        f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/'Thống kê'!A1?valueInputOption=USER_ENTERED",
        json={"values": thong_ke_values}
    )

    # 9. Format Headers, Column widths, and Freezing across all 3 sheets
    print("Applying styling, header colors, frozen rows, and column widths...")
    format_requests = [
        # Format Test 1 Header (Blue background #1A73E8, white bold text, center align)
        {
            "repeatCell": {
                "range": {"sheetId": 0, "startRowIndex": 0, "endRowIndex": 1, "startColumnIndex": 0, "endColumnIndex": 7},
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": {"red": 0.102, "green": 0.451, "blue": 0.910},
                        "textFormat": {"foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0}, "bold": True, "fontSize": 10},
                        "horizontalAlignment": "CENTER",
                        "verticalAlignment": "MIDDLE",
                        "wrapStrategy": "WRAP"
                    }
                },
                "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,verticalAlignment,wrapStrategy)"
            }
        },
        # Freeze 1 row on Test 1
        {"updateSheetProperties": {"properties": {"sheetId": 0, "gridProperties": {"frozenRowCount": 1}}, "fields": "gridProperties.frozenRowCount"}},
        # Set column widths on Test 1
        {"updateDimensionProperties": {"range": {"sheetId": 0, "dimension": "COLUMNS", "startIndex": 0, "endIndex": 1}, "properties": {"pixelSize": 60}, "fields": "pixelSize"}},
        {"updateDimensionProperties": {"range": {"sheetId": 0, "dimension": "COLUMNS", "startIndex": 1, "endIndex": 2}, "properties": {"pixelSize": 160}, "fields": "pixelSize"}},
        {"updateDimensionProperties": {"range": {"sheetId": 0, "dimension": "COLUMNS", "startIndex": 2, "endIndex": 3}, "properties": {"pixelSize": 350}, "fields": "pixelSize"}},
        {"updateDimensionProperties": {"range": {"sheetId": 0, "dimension": "COLUMNS", "startIndex": 3, "endIndex": 4}, "properties": {"pixelSize": 320}, "fields": "pixelSize"}},
        {"updateDimensionProperties": {"range": {"sheetId": 0, "dimension": "COLUMNS", "startIndex": 4, "endIndex": 5}, "properties": {"pixelSize": 380}, "fields": "pixelSize"}},
        {"updateDimensionProperties": {"range": {"sheetId": 0, "dimension": "COLUMNS", "startIndex": 5, "endIndex": 6}, "properties": {"pixelSize": 140}, "fields": "pixelSize"}},
        {"updateDimensionProperties": {"range": {"sheetId": 0, "dimension": "COLUMNS", "startIndex": 6, "endIndex": 7}, "properties": {"pixelSize": 250}, "fields": "pixelSize"}},

        # Format Kết quả đích thực tế Header (Teal/Green background #0D652D, white bold text)
        {
            "repeatCell": {
                "range": {"sheetId": 1, "startRowIndex": 0, "endRowIndex": 1, "startColumnIndex": 0, "endColumnIndex": 6},
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": {"red": 0.051, "green": 0.396, "blue": 0.176},
                        "textFormat": {"foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0}, "bold": True, "fontSize": 10},
                        "horizontalAlignment": "CENTER",
                        "verticalAlignment": "MIDDLE",
                        "wrapStrategy": "WRAP"
                    }
                },
                "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,verticalAlignment,wrapStrategy)"
            }
        },
        # Freeze 1 row on Kết quả đích thực tế
        {"updateSheetProperties": {"properties": {"sheetId": 1, "gridProperties": {"frozenRowCount": 1}}, "fields": "gridProperties.frozenRowCount"}},
        # Set column widths on Kết quả đích thực tế
        {"updateDimensionProperties": {"range": {"sheetId": 1, "dimension": "COLUMNS", "startIndex": 0, "endIndex": 1}, "properties": {"pixelSize": 60}, "fields": "pixelSize"}},
        {"updateDimensionProperties": {"range": {"sheetId": 1, "dimension": "COLUMNS", "startIndex": 1, "endIndex": 2}, "properties": {"pixelSize": 160}, "fields": "pixelSize"}},
        {"updateDimensionProperties": {"range": {"sheetId": 1, "dimension": "COLUMNS", "startIndex": 2, "endIndex": 3}, "properties": {"pixelSize": 350}, "fields": "pixelSize"}},
        {"updateDimensionProperties": {"range": {"sheetId": 1, "dimension": "COLUMNS", "startIndex": 3, "endIndex": 4}, "properties": {"pixelSize": 450}, "fields": "pixelSize"}},
        {"updateDimensionProperties": {"range": {"sheetId": 1, "dimension": "COLUMNS", "startIndex": 4, "endIndex": 5}, "properties": {"pixelSize": 400}, "fields": "pixelSize"}},
        {"updateDimensionProperties": {"range": {"sheetId": 1, "dimension": "COLUMNS", "startIndex": 5, "endIndex": 6}, "properties": {"pixelSize": 250}, "fields": "pixelSize"}},

        # Format Thống kê Header
        {
            "repeatCell": {
                "range": {"sheetId": 2, "startRowIndex": 0, "endRowIndex": 1, "startColumnIndex": 0, "endColumnIndex": 3},
                "cell": {
                    "userEnteredFormat": {
                        "textFormat": {"bold": True, "fontSize": 14, "foregroundColor": {"red": 0.08, "green": 0.2, "blue": 0.5}}
                    }
                },
                "fields": "userEnteredFormat.textFormat"
            }
        },
        {
            "repeatCell": {
                "range": {"sheetId": 2, "startRowIndex": 2, "endRowIndex": 3, "startColumnIndex": 0, "endColumnIndex": 3},
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": {"red": 0.102, "green": 0.451, "blue": 0.910},
                        "textFormat": {"foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0}, "bold": True},
                        "horizontalAlignment": "CENTER"
                    }
                },
                "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)"
            }
        },
        {
            "repeatCell": {
                "range": {"sheetId": 2, "startRowIndex": 13, "endRowIndex": 14, "startColumnIndex": 0, "endColumnIndex": 3},
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": {"red": 0.102, "green": 0.451, "blue": 0.910},
                        "textFormat": {"foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0}, "bold": True},
                        "horizontalAlignment": "CENTER"
                    }
                },
                "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)"
            }
        },
        {"updateDimensionProperties": {"range": {"sheetId": 2, "dimension": "COLUMNS", "startIndex": 0, "endIndex": 1}, "properties": {"pixelSize": 350}, "fields": "pixelSize"}},
        {"updateDimensionProperties": {"range": {"sheetId": 2, "dimension": "COLUMNS", "startIndex": 1, "endIndex": 2}, "properties": {"pixelSize": 180}, "fields": "pixelSize"}},
        {"updateDimensionProperties": {"range": {"sheetId": 2, "dimension": "COLUMNS", "startIndex": 2, "endIndex": 3}, "properties": {"pixelSize": 450}, "fields": "pixelSize"}}
    ]

    client.request(
        "POST",
        f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}:batchUpdate",
        json={"requests": format_requests}
    )

    print("\n" + "=" * 80)
    print("PIPELINE COMPLETED SUCCESSFULLY!")
    print(f"Google Drive Main Folder: https://drive.google.com/drive/folders/{MAIN_FOLDER_ID}")
    print(f"Google Drive Subfolder (PDFs): https://drive.google.com/drive/folders/{SUBFOLDER_ID}")
    print(f"Google Spreadsheet URL:  {spreadsheet_url}")
    print("=" * 80)


if __name__ == "__main__":
    main()
