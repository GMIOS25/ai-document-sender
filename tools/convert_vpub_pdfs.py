import os
import sys
import json
import re
from pathlib import Path
import pymupdf
import pymupdf4llm
from rapidocr_onnxruntime import RapidOCR

# Configure stdout for utf-8 on Windows
sys.stdout.reconfigure(encoding='utf-8')

def extract_metadata_from_cpx(cpx_path):
    if not os.path.exists(cpx_path):
        return {}
    try:
        with open(cpx_path, 'r', encoding='utf-8') as f:
            content = f.read()
            try:
                data = json.loads(content)
                ed = data.get('ed', {})
            except Exception:
                # Fallback parse bằng regex nếu file view.cpx không chuẩn json
                ed = {}
                for key in ['id', 'documentId', 'subject', 'signNumber', 'createDate', 'docDate', 'docDateStr', 'category', 'kpi', 'kpiName', 'signer', 'approver', 'composer', 'note', 'author']:
                    m = re.search(rf'{key}\s+([^,\r\n]+)', content)
                    if m:
                        ed[key] = m.group(1).strip()
        return {
            "id": ed.get('id'),
            "so_hieu": ed.get('signNumber', '').strip(),
            "trich_yeu": ed.get('subject', '').strip(),
            "co_quan_ban_hanh": ed.get('author', '').strip(),
            "ngay_van_ban": ed.get('docDateStr', '')[:10] if ed.get('docDateStr') else ed.get('docDate', '').strip(),
            "ngay_tao": ed.get('createDate', '').strip(),
            "loai_van_ban": ed.get('category', '').strip(),
            "kpi": ed.get('kpi', '').strip(),
            "kpi_ten": ed.get('kpiName', '').strip(),
            "nguoi_ky": ed.get('signer', '').strip(),
            "nguoi_duyet": ed.get('approver', '').strip(),
            "nguoi_soan": ed.get('composer', '').strip(),
            "ghi_chu": ed.get('note', '').strip(),
        }
    except Exception as e:
        print(f"  [Warning] Cannot read view.cpx: {e}")
        return {}

def clean_markdown_text(text: str) -> str:
    # 1. Xóa các thẻ HTML dư thừa do phân tích layout PDF sinh ra
    text = re.sub(r'</?mark>', '', text)
    text = re.sub(r'\*\*\s+\*\*', '', text)
    
    # 2. Chuẩn hóa ngày tháng bị stamp đè rơi ra sau
    # Dạng: ngày ... tháng ... năm 2026 ... DD MM
    text = re.sub(
        r'ngày\s+tháng\s+năm\s+(\d{4})_?\s+(\d{1,2})\s+(\d{1,2})',
        r'ngày \2 tháng \3 năm \1',
        text
    )
    # Dạng: ngày ... tháng MM năm YYYY ... DD
    text = re.sub(
        r'ngày\s+tháng\s+(\d{1,2})\s+năm\s+(\d{4})_?\s+(\d{1,2})',
        r'ngày \3 tháng \1 năm \2',
        text
    )
    
    # 3. Chuẩn hóa số hiệu văn bản bị tách số ra phía sau do e-Office overlay
    # Dạng: 'Số:       /QĐ - UBND       3550' -> 'Số: 3550/QĐ - UBND'
    def fix_detached_number(m):
        coquan = m.group('coquan').strip()
        num = m.group('num').strip()
        rest = m.group('rest') or ''
        return f'Số: {num}/{coquan} {rest}'
        
    text = re.sub(
        r'Số:\s+/(?P<coquan>[A-ZĐa-z0-9\-/ ]+?)\s+(?P<num>\d{3,6})\b(?P<rest>.*)',
        fix_detached_number,
        text
    )

    # 4. Thu gọn dòng trống thừa
    text = re.sub(r'\n{3,}', '\n\n', text)
    lines = [line.rstrip() for line in text.splitlines()]
    return '\n'.join(lines).strip()

def extract_pdf_with_digital_text(pdf_path: str) -> str:
    try:
        md_text = pymupdf4llm.to_markdown(pdf_path)
        return clean_markdown_text(md_text)
    except Exception as e:
        print(f"  [Error] pymupdf4llm failed: {e}")
        return ""

def extract_pdf_with_ocr(pdf_path: str, ocr_engine: RapidOCR) -> str:
    doc = pymupdf.open(pdf_path)
    page_texts = []
    for page_idx, page in enumerate(doc):
        pix = page.get_pixmap(dpi=200)
        img_bytes = pix.tobytes('png')
        res, _ = ocr_engine(img_bytes)
        if res:
            # Sort items primarily top-to-bottom, secondarily left-to-right
            sorted_res = sorted(res, key=lambda item: (item[0][0][1], item[0][0][0]))
            lines = [item[1].strip() for item in sorted_res if item[1].strip()]
            page_content = '\n'.join(lines)
            page_texts.append(f"<!-- TRANG {page_idx + 1} -->\n" + page_content)
        else:
            page_texts.append(f"<!-- TRANG {page_idx + 1} (Không nhận dạng được chữ) -->")
    doc.close()
    return '\n\n---\n\n'.join(page_texts)

def build_yaml_frontmatter(metadata: dict, page_count: int, doc_type: str, pdf_filename: str) -> str:
    lines = ["---"]
    lines.append(f"ten_file_goc: {json.dumps(pdf_filename, ensure_ascii=False)}")
    lines.append(f"loai_trich_xuat: {json.dumps(doc_type, ensure_ascii=False)}")
    lines.append(f"so_trang: {page_count}")
    
    fields = [
        ("so_hieu", "so_hieu"),
        ("trich_yeu", "trich_yeu"),
        ("co_quan_ban_hanh", "co_quan_ban_hanh"),
        ("ngay_van_ban", "ngay_van_ban"),
        ("loai_van_ban", "loai_van_ban"),
        ("nguoi_ky", "nguoi_ky"),
        ("nguoi_duyet", "nguoi_duyet"),
        ("nguoi_soan", "nguoi_soan"),
        ("kpi", "kpi"),
        ("kpi_ten", "kpi_ten"),
        ("ghi_chu", "ghi_chu"),
    ]
    
    for key, label in fields:
        val = metadata.get(key, "")
        if val:
            lines.append(f"{label}: {json.dumps(val, ensure_ascii=False)}")
    
    lines.append("---")
    return '\n'.join(lines)

def process_vpub_directory(base_dir: str):
    print(f"Bắt đầu quét và chuyển đổi tài liệu trong: {base_dir}")
    ocr_engine = None
    
    pdf_files = []
    for root, dirs, files in os.walk(base_dir):
        for f in files:
            if f.lower().endswith('.pdf'):
                pdf_files.append(os.path.join(root, f))
                
    total = len(pdf_files)
    print(f"Tổng số file PDF tìm thấy: {total}")
    
    catalog = []
    digital_count = 0
    scanned_count = 0
    
    for idx, pdf_path in enumerate(pdf_files, 1):
        folder_dir = os.path.dirname(pdf_path)
        pdf_name = os.path.basename(pdf_path)
        md_name = os.path.splitext(pdf_name)[0] + ".md"
        md_path = os.path.join(folder_dir, md_name)
        cpx_path = os.path.join(folder_dir, "view.cpx")
        
        print(f"[{idx}/{total}] Đang xử lý: {pdf_name}")
        
        # 1. Trích xuất metadata từ view.cpx nếu có
        metadata = extract_metadata_from_cpx(cpx_path)
        
        # 2. Mở file PDF và kiểm tra số trang
        doc = pymupdf.open(pdf_path)
        page_count = len(doc)
        
        # Kiểm tra nhanh độ dài text để phân loại digital hay scanned
        sample_text = ""
        for p in doc:
            sample_text += p.get_text()
            if len(sample_text) > 150:
                break
        doc.close()
        
        doc_type = "digital_text"
        md_body = ""
        
        # 3. Chuyển đổi nội dung
        if len(sample_text.strip()) > 50 and not (len(sample_text.strip()) < 80 and "Ký bởi:" in sample_text):
            # Born-digital PDF
            md_body = extract_pdf_with_digital_text(pdf_path)
            digital_count += 1
        else:
            # Scanned PDF -> dùng OCR
            print(f"  -> File scan / ảnh: kích hoạt OCR cho {page_count} trang...")
            if ocr_engine is None:
                ocr_engine = RapidOCR()
            md_body = extract_pdf_with_ocr(pdf_path, ocr_engine)
            doc_type = "scanned_ocr"
            scanned_count += 1
            
        # 4. Gắn Frontmatter & Tiêu đề
        frontmatter = build_yaml_frontmatter(metadata, page_count, doc_type, pdf_name)
        
        subject_title = metadata.get('trich_yeu') or os.path.splitext(pdf_name)[0]
        sign_number = metadata.get('so_hieu')
        header_title = f"# {sign_number} - {subject_title}" if sign_number else f"# {subject_title}"
        
        final_content = f"{frontmatter}\n\n{header_title}\n\n{md_body}\n"
        
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(final_content)
            
        # Ước tính token (khoảng 3.5 ký tự / token cho tiếng Việt)
        char_count = len(final_content)
        est_tokens = int(char_count / 3.5)
        
        rel_md_path = os.path.relpath(md_path, base_dir)
        catalog.append({
            "stt": idx,
            "so_hieu": metadata.get('so_hieu', 'N/A'),
            "trich_yeu": metadata.get('trich_yeu', subject_title),
            "loai_van_ban": metadata.get('loai_van_ban', 'N/A'),
            "co_quan_ban_hanh": metadata.get('co_quan_ban_hanh', 'N/A'),
            "ngay_van_ban": metadata.get('ngay_van_ban', 'N/A'),
            "loai_trich_xuat": doc_type,
            "so_trang": page_count,
            "ky_tu": char_count,
            "uoc_tinh_token": est_tokens,
            "duong_dan_md": rel_md_path
        })
        print(f"  ✓ Đã lưu: {md_name} ({char_count:,} ký tự ~ {est_tokens:,} tokens)")

    # 5. Xuất danh mục tổng hợp DANH_MUC_VAN_BAN.md và catalog.json
    catalog_md_path = os.path.join(base_dir, "DANH_MUC_VAN_BAN.md")
    catalog_json_path = os.path.join(base_dir, "catalog.json")
    
    with open(catalog_json_path, 'w', encoding='utf-8') as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)
        
    md_table_rows = []
    for item in catalog:
        clean_trich_yeu = item['trich_yeu'].replace('\n', ' ')
        duong_dan = item['duong_dan_md'].replace('\\', '/')
        md_table_rows.append(
            f"| {item['stt']} | `{item['so_hieu']}` | [{clean_trich_yeu}]({duong_dan}) | {item['loai_van_ban']} | {item['so_trang']} | {item['loai_trich_xuat']} | ~{item['uoc_tinh_token']:,} |"
        )
        
    catalog_md_content = f"""# DANH MỤC VĂN BẢN VPUB (DÀNH CHO AI AGENT)

Tài liệu này tổng hợp toàn bộ các văn bản đã được chuyển đổi từ PDF sang Markdown tối ưu cho AI Agent.
Mỗi file Markdown chứa toàn bộ nội dung văn bản kèm Frontmatter metadata chuẩn hóa ở đầu file giúp Agent đọc trực tiếp không tốn quota thị giác (Vision tokens).

## Thống kê tổng quan
- **Tổng số văn bản:** {total}
- **Văn bản điện tử (Digital Text):** {digital_count}
- **Văn bản scan (OCR):** {scanned_count}
- **Tổng số tokens ước tính:** ~{sum(x['uoc_tinh_token'] for x in catalog):,} tokens

## Bảng tra cứu văn bản

| STT | Số hiệu | Trích yếu / Tiêu đề | Loại văn bản | Trang | Loại trích xuất | Token ước tính |
|:---:|:---|:---|:---|:---:|:---:|:---:|
""" + '\n'.join(md_table_rows) + "\n"

    with open(catalog_md_path, 'w', encoding='utf-8') as f:
        f.write(catalog_md_content)

    print("\n" + "="*50)
    print("HOÀN THÀNH CHUYỂN ĐỔI TOÀN BỘ VĂN BẢN!")
    print(f"- Tổng số văn bản: {total}")
    print(f"- Văn bản điện tử: {digital_count}")
    print(f"- Văn bản scan (đã OCR): {scanned_count}")
    print(f"- Đã tạo mục lục: {catalog_md_path}")
    print(f"- Đã tạo catalog JSON: {catalog_json_path}")
    print("="*50)

if __name__ == '__main__':
    target_dir = r"d:\Work\ai-document-sender\resources\văn bản mẫu\vpub"
    if len(sys.argv) > 1:
        target_dir = sys.argv[1]
    process_vpub_directory(target_dir)
