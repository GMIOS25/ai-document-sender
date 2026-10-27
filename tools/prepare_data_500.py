import os
import sys
import json
import re
import pathlib
import time

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"c:\Workspaces\ai-document-sender\src")
sys.path.insert(0, r"c:\Workspaces\ai-document-sender\tools")

from ai_document_sender.config import Settings
from ai_document_sender.extraction import _read_pages, extract_rule_mentions
from lookup_service import RecipientLookupService

def main():
    settings = Settings()
    lookup_db_path = r"c:\Workspaces\ai-document-sender\resources\data\lookup.db"
    service = RecipientLookupService(lookup_db_path)
    base_dir = pathlib.Path(r"c:\Workspaces\ai-document-sender\resources\văn bản mẫu\vpub\Hợp lệ")

    folders = []
    for f in base_dir.iterdir():
        if not f.is_dir():
            continue
        m = re.match(r"^(\d+)", f.name)
        if m:
            num = int(m.group(1))
            if num <= 13116:
                folders.append((num, f))

    folders.sort(key=lambda x: x[0], reverse=True)
    print(f"Total candidate folders <= 13116: {len(folders)}")

    valid_docs = []
    for num, folder in folders:
        # Find main document file (pdf)
        pdf_file = None
        for item in folder.iterdir():
            if item.is_file() and item.suffix.lower() == ".pdf":
                pdf_file = item
                break
        if not pdf_file:
            # Check files without extension if PDF
            for item in folder.iterdir():
                if item.is_file() and item.name not in ("view.cpx",) and "kết_quả" not in item.name.lower():
                    try:
                        with open(item, "rb") as fp:
                            header = fp.read(5)
                            if header.startswith(b"%PDF-"):
                                pdf_file = item
                                break
                    except Exception:
                        pass
        if pdf_file:
            valid_docs.append((num, folder, pdf_file))
            if len(valid_docs) == 500:
                break

    print(f"Selected {len(valid_docs)} documents with valid files.")
    print(f"Top doc: {valid_docs[0][0]} ({valid_docs[0][1].name})")
    print(f"500th doc: {valid_docs[-1][0]} ({valid_docs[-1][1].name})")

    results = []
    start_time = time.time()

    for idx, (num, folder, pdf_file) in enumerate(valid_docs, 1):
        # 1. Read metadata from view.cpx
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

        # 2. Extract mentions using backend
        mentions_list = []
        try:
            pages = _read_pages(str(pdf_file.resolve()), settings)
            mentions, reasons = extract_rule_mentions(pages)
            for m in mentions:
                raw_text = m.raw.strip()
                if raw_text:
                    mentions_list.append(raw_text)
        except Exception as e:
            mentions_list = []

        # 3. Lookup each mention in lookup.db
        recipients_pairs = []
        if mentions_list:
            for raw_m in mentions_list:
                try:
                    res = service.lookup(raw_m, limit=1)
                    if res and len(res) > 0:
                        matched = res[0]
                        d_name = matched.get("display_name", "").strip()
                        code = matched.get("code", "").strip()
                        if code and code not in d_name:
                            res_str = f"{d_name} ({code})"
                        else:
                            res_str = d_name
                    else:
                        res_str = "-"
                except Exception:
                    res_str = "-"
                recipients_pairs.append((raw_m, res_str))
        else:
            recipients_pairs.append(("-", "-"))

        results.append({
            "stt": idx,
            "folder_name": folder.name,
            "pdf_path": str(pdf_file.resolve()),
            "pdf_filename": pdf_file.name if pdf_file.suffix.lower() == ".pdf" else f"{pdf_file.name}.pdf",
            "file_size": pdf_file.stat().st_size,
            "so_hieu": sign_number,
            "trich_yeu": subject,
            "recipients": recipients_pairs
        })

        if idx % 50 == 0 or idx == len(valid_docs):
            print(f"Processed {idx}/500 docs ({time.time() - start_time:.1f}s)")

    output_path = r"c:\Workspaces\ai-document-sender\.tmp\prepared_500_documents.json"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as fp:
        json.dump(results, fp, ensure_ascii=False, indent=2)

    total_rows = sum(len(d["recipients"]) for d in results)
    print(f"Done! Saved to {output_path}")
    print(f"Total documents: {len(results)}, Total spreadsheet rows: {total_rows}")

if __name__ == "__main__":
    main()
