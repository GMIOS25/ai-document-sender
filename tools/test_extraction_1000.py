"""Evaluation script to test backend extraction on 1000 sample documents.

Measures:
1. Extraction success rate: can backend read PDF and extract recipient mentions?
2. Mention composition: units, roles, staff codes, archive, references.
3. Completeness & Reasonableness (%): comparison against ground truth (kết_quả_gửi_đi.txt).
4. Error & Edge case analysis: scanned documents, missing sections, layout challenges.
"""

import sys
import os
import pathlib
import re
import json
import time
import unicodedata
from collections import Counter

from ai_document_sender.config import Settings
from ai_document_sender.extraction import _read_pages, extract_rule_mentions


def normalize_text(s: str) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFC", s).lower()
    return re.sub(r"[\s\-_,.:;()\/]+", " ", s).strip()


def parse_ground_truth(txt_path: pathlib.Path):
    if not txt_path.exists():
        return None
    content = txt_path.read_text(encoding="utf-8", errors="replace")
    gt = {"xu_ly": [], "theo_doi": [], "don_vi": []}
    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("Người xử lí:"):
            gt["xu_ly"] = [it.strip() for it in line.replace("Người xử lí:", "").split(";") if it.strip()]
        elif line.startswith("Người theo dõi:"):
            gt["theo_doi"] = [it.strip() for it in line.replace("Người theo dõi:", "").split(";") if it.strip()]
        elif line.startswith("Đơn vị nhận:"):
            gt["don_vi"] = [it.strip() for it in line.replace("Đơn vị nhận:", "").split(";") if it.strip()]
    return gt


def match_internal_person(gt_str: str, mentions_raw: list[str]) -> tuple[bool, str]:
    # 1. Staff code match: V1, V5, N6, T4, X2, C4, C7...
    code_match = re.search(r"\b([TVNCX]\d{1,2})\b", gt_str, re.I)
    if code_match:
        code = code_match.group(1).upper()
        for m in mentions_raw:
            if re.search(r"\b" + code + r"\b", m, re.I):
                return True, f"code:{code}"

    # 2. Key leadership roles:
    gt_lower = gt_str.lower()
    if "chủ tịch" in gt_lower and "phó" not in gt_lower:
        for m in mentions_raw:
            m_l = m.lower()
            if m_l in ["ct", "chủ tịch", "chủ tịch ubnd tỉnh"] or re.search(r"\bct\b", m_l):
                return True, "role:CT"

    if "chánh văn phòng" in gt_lower and "phó" not in gt_lower:
        for m in mentions_raw:
            m_l = m.lower()
            if m_l in ["cvp", "chánh văn phòng"] or re.search(r"\bcvp\b", m_l):
                return True, "role:CVP"

    if "phó chánh văn phòng" in gt_lower:
        for m in mentions_raw:
            m_l = m.lower()
            if re.search(r"\b(?:pcvp|pvp\w*|phó chánh văn phòng)\b", m_l):
                return True, "role:PCVP"

    if "phó chủ tịch" in gt_lower:
        # Check specific PCT name if available
        for m in mentions_raw:
            m_l = m.lower()
            if re.search(r"\b(?:pct\w*|phó chủ tịch)\b", m_l):
                return True, "role:PCT"

    # 3. Match person full name or name inside parentheses
    name_match = re.search(r"\(([^)]+)\)", gt_str)
    target_names = [name_match.group(1).strip()] if name_match else []
    clean_gt = re.sub(r"^(?:Chủ tịch|Phó Chủ tịch|Chánh Văn phòng|Phó Chánh Văn phòng|Trưởng phòng|Phó Trưởng phòng|Phó Trưởng ban|Trưởng ban|Chuyên viên)\s*[A-Z0-9]*\s*", "", gt_str, flags=re.I).strip(" ()")
    if clean_gt:
        target_names.append(clean_gt)

    for name in target_names:
        name_norm = normalize_text(name)
        if len(name_norm) > 4:
            for m in mentions_raw:
                if name_norm in normalize_text(m):
                    return True, f"name:{name}"

    return False, ""


def match_unit(gt_str: str, mentions_raw: list[str]) -> tuple[bool, str]:
    clean_gt = re.sub(r"(\s*-\s*tỉnh\s*gia\s*lai|\s*tỉnh\s*gia\s*lai)", "", gt_str, flags=re.I).strip()
    clean_gt_norm = normalize_text(clean_gt)

    # Standard administrative alias mappings
    aliases = {
        "sở xd": "sở xây dựng",
        "sở nn&mt": "sở nông nghiệp và môi trường",
        "sở kh&đt": "sở kế hoạch và đầu tư",
        "sở vhtt&dl": "sở văn hóa thể thao và du lịch",
        "sở văn hóa thể thao và du lịch": "sở văn hóa thể thao và du lịch",
        "sở tt&tt": "sở thông tin và truyền thông",
        "ubnd": "ủy ban nhân dân",
        "hđnd": "hội đồng nhân dân",
    }

    def expand_alias(text):
        for k, v in aliases.items():
            text = text.replace(k, v)
        return text

    exp_gt = expand_alias(clean_gt_norm)

    for m in mentions_raw:
        m_norm = normalize_text(m)
        exp_m = expand_alias(m_norm)

        # Exact substring
        if clean_gt_norm in m_norm or m_norm in clean_gt_norm:
            return True, f"exact:{m}"
        if exp_gt in exp_m or exp_m in exp_gt:
            return True, f"alias:{m}"

        # Word overlap for units
        words_gt = set(exp_gt.split())
        words_m = set(exp_m.split())
        # remove stopwords
        stop = {"tỉnh", "thành", "phố", "các", "ban", "và", "của", "tại"}
        words_gt -= stop
        words_m -= stop

        common = words_gt.intersection(words_m)
        if common and len(common) >= 2:
            overlap = len(common) / min(len(words_gt), len(words_m)) if min(len(words_gt), len(words_m)) > 0 else 0
            if overlap >= 0.7:
                return True, f"overlap:{m}"

    return False, ""


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    settings = Settings()
    base_dir = pathlib.Path("resources/văn bản mẫu/vpub/Hợp lệ")
    folders = sorted([f for f in base_dir.iterdir() if f.is_dir()])
    total_folders = len(folders)

    print(f"Bắt đầu kiểm thử trên toàn bộ {total_folders} thư mục văn bản mẫu...")
    start_time = time.time()

    results = []
    category_counts = Counter()
    mention_kinds_counter = Counter()

    gt_unit_total = 0
    gt_unit_matched = 0
    gt_person_total = 0
    gt_person_matched = 0

    scanned_docs = []
    no_pdf_docs = []
    error_docs = []
    no_mention_docs = []

    for idx, folder in enumerate(folders, 1):
        pdfs = list(folder.glob("*.pdf"))
        txt_path = folder / "kết_quả_gửi_đi.txt"
        gt_data = parse_ground_truth(txt_path)

        if not pdfs:
            category_counts["no_pdf"] += 1
            no_pdf_docs.append(folder.name)
            results.append({
                "folder": folder.name,
                "status": "NO_PDF",
                "mentions_count": 0,
                "gt_total": len(gt_data["xu_ly"] + gt_data["theo_doi"] + gt_data["don_vi"]) if gt_data else 0,
                "gt_matched": 0,
                "recall_pct": 0.0
            })
            continue

        pdf_path = pdfs[0]
        filename = str(pdf_path.resolve())
        if os.name == "nt" and not filename.startswith("\\\\?\\"):
            filename = "\\\\?\\" + filename

        try:
            pages = _read_pages(filename, settings)
        except Exception as e:
            category_counts["read_error"] += 1
            error_docs.append((folder.name, str(e)))
            results.append({
                "folder": folder.name,
                "status": "READ_ERROR",
                "error": str(e),
                "mentions_count": 0,
                "gt_total": len(gt_data["xu_ly"] + gt_data["theo_doi"] + gt_data["don_vi"]) if gt_data else 0,
                "gt_matched": 0,
                "recall_pct": 0.0
            })
            continue

        # Check if scanned
        all_text = "".join(p.get("text", "") for p in pages)
        is_scanned = len(all_text.strip()) < 50
        if is_scanned:
            category_counts["scanned_needs_ocr"] += 1
            scanned_docs.append(folder.name)
            results.append({
                "folder": folder.name,
                "status": "SCANNED_NEEDS_OCR",
                "pages": len(pages),
                "mentions_count": 0,
                "gt_total": len(gt_data["xu_ly"] + gt_data["theo_doi"] + gt_data["don_vi"]) if gt_data else 0,
                "gt_matched": 0,
                "recall_pct": 0.0
            })
            continue

        # Rule-based mention extraction
        try:
            mentions, reasons = extract_rule_mentions(pages)
        except Exception as e:
            category_counts["extract_error"] += 1
            error_docs.append((folder.name, str(e)))
            continue

        if not mentions:
            category_counts["no_mentions_found"] += 1
            no_mention_docs.append((folder.name, reasons))
            results.append({
                "folder": folder.name,
                "status": "NO_MENTIONS",
                "reasons": reasons,
                "pages": len(pages),
                "mentions_count": 0,
                "gt_total": len(gt_data["xu_ly"] + gt_data["theo_doi"] + gt_data["don_vi"]) if gt_data else 0,
                "gt_matched": 0,
                "recall_pct": 0.0
            })
            continue

        # Categorize kinds
        for m in mentions:
            mention_kinds_counter[m.kind] += 1

        # Match against GT
        mentions_raw = [m.raw for m in mentions]
        matched_gt = 0
        total_gt = 0
        missed_items = []

        if gt_data:
            # Match internal people
            internal_gt = gt_data["xu_ly"] + gt_data["theo_doi"]
            for person_str in internal_gt:
                total_gt += 1
                gt_person_total += 1
                matched, how = match_internal_person(person_str, mentions_raw)
                if matched:
                    matched_gt += 1
                    gt_person_matched += 1
                else:
                    missed_items.append(("person", person_str))

            # Match units
            for unit_str in gt_data["don_vi"]:
                total_gt += 1
                gt_unit_total += 1
                matched, how = match_unit(unit_str, mentions_raw)
                if matched:
                    matched_gt += 1
                    gt_unit_matched += 1
                else:
                    missed_items.append(("unit", unit_str))

        recall_pct = round((matched_gt / total_gt * 100), 1) if total_gt > 0 else 100.0

        if recall_pct >= 90.0:
            category_counts["excellent_match_90_100"] += 1
        elif recall_pct >= 75.0:
            category_counts["good_match_75_89"] += 1
        elif recall_pct >= 50.0:
            category_counts["fair_match_50_74"] += 1
        else:
            category_counts["low_match_under_50"] += 1

        results.append({
            "folder": folder.name,
            "status": "EXTRACTED",
            "pages": len(pages),
            "mentions_count": len(mentions),
            "reasons": reasons,
            "gt_total": total_gt,
            "gt_matched": matched_gt,
            "recall_pct": recall_pct,
            "missed_items": missed_items
        })

        if idx % 100 == 0:
            print(f"Đã xử lý {idx}/{total_folders} văn bản...")

    elapsed = time.time() - start_time
    print(f"\n===== KẾT QUẢ TỔNG QUAN KIỂM THỬ (Thời gian: {elapsed:.1f}s) =====")
    print(f"Tổng số văn bản mẫu quét: {total_folders}")
    print(f" - Văn bản có PDF và text layer: {len(results) - category_counts['no_pdf'] - category_counts['read_error'] - category_counts['scanned_needs_ocr']}")
    print(f" - Văn bản scan (cần OCR): {category_counts['scanned_needs_ocr']}")
    print(f" - Thư mục không có PDF: {category_counts['no_pdf']}")
    print(f" - Lỗi đọc PDF: {category_counts['read_error']}")
    print(f" - Đọc được PDF nhưng không trích xuất được Nơi nhận (0 mentions): {category_counts['no_mentions_found']}")

    extracted_valid = [r for r in results if r["status"] == "EXTRACTED"]
    total_valid = len(extracted_valid)

    print(f"\n===== TỶ LỆ TRÍCH XUẤT THÀNH CÔNG =====")
    print(f"Số văn bản trích xuất thành công danh sách nơi nhận: {total_valid}/{total_folders} ({total_valid/total_folders*100:.2f}%)")
    searchable_total = total_folders - category_counts['no_pdf'] - category_counts['scanned_needs_ocr'] - category_counts['read_error']
    if searchable_total > 0:
        print(f"Tỷ lệ trên các văn bản có lớp chữ (Searchable PDFs): {total_valid}/{searchable_total} ({total_valid/searchable_total*100:.2f}%)")

    print(f"\n===== ĐỘ HỢP LÝ VÀ PHỦ ĐỐI CHIẾU THỰC TẾ (GROUND TRUTH) =====")
    print(f"1. Phân bố mức độ hợp lý theo văn bản:")
    print(f" - Rất cao (Khớp 90% - 100% người/đơn vị): {category_counts['excellent_match_90_100']} văn bản ({category_counts['excellent_match_90_100']/total_valid*100:.2f}%)")
    print(f" - Cao (Khớp 75% - 89% người/đơn vị): {category_counts['good_match_75_89']} văn bản ({category_counts['good_match_75_89']/total_valid*100:.2f}%)")
    print(f" - Khá (Khớp 50% - 74% người/đơn vị): {category_counts['fair_match_50_74']} văn bản ({category_counts['fair_match_50_74']/total_valid*100:.2f}%)")
    print(f" - Thấp (Dưới 50% người/đơn vị): {category_counts['low_match_under_50']} văn bản ({category_counts['low_match_under_50']/total_valid*100:.2f}%)")
    
    high_match = category_counts['excellent_match_90_100'] + category_counts['good_match_75_89']
    print(f" => Tổng số văn bản đạt mức HỢP LÝ CAO (>= 75%): {high_match}/{total_valid} ({high_match/total_valid*100:.2f}%)")
    acceptable = high_match + category_counts['fair_match_50_74']
    print(f" => Tổng số văn bản đạt mức CHẤP NHẬN ĐƯỢC (>= 50%): {acceptable}/{total_valid} ({acceptable/total_valid*100:.2f}%)")

    print(f"\n2. Tỷ lệ bao phủ theo thực thể (Entity Recall):")
    gt_total_all = gt_unit_total + gt_person_total
    gt_matched_all = gt_unit_matched + gt_person_matched
    print(f" - Tổng thực thể đối chiếu: {gt_matched_all}/{gt_total_all} ({gt_matched_all/gt_total_all*100:.2f}%)")
    print(f" - Đơn vị nhận (External Units): {gt_unit_matched}/{gt_unit_total} ({gt_unit_matched/gt_unit_total*100:.2f}%)")
    print(f" - Người/Chức danh nội bộ (Internal Leaders/Staff): {gt_person_matched}/{gt_person_total} ({gt_person_matched/gt_person_total*100:.2f}%)")

    print(f"\n===== CƠ CẤU MENTIONS ĐƯỢC TRÍCH XUẤT =====")
    total_mentions_all = sum(mention_kinds_counter.values())
    print(f"Tổng số mentions trích xuất: {total_mentions_all} (trung bình {total_mentions_all/total_valid:.1f} mentions/văn bản)")
    for kind, count in mention_kinds_counter.most_common():
        print(f" - {kind}: {count} ({count/total_mentions_all*100:.1f}%)")

    # Save summary report to JSON
    report_data = {
        "summary": {
            "total_folders": total_folders,
            "searchable_pdfs": searchable_total,
            "scanned_needs_ocr": category_counts["scanned_needs_ocr"],
            "no_pdf": category_counts["no_pdf"],
            "read_error": category_counts["read_error"],
            "no_mentions_found": category_counts["no_mentions_found"],
            "extracted_valid": total_valid,
            "extraction_rate_all": round(total_valid / total_folders * 100, 2),
            "extraction_rate_searchable": round(total_valid / searchable_total * 100, 2) if searchable_total > 0 else 0,
            "high_match_count": high_match,
            "high_match_pct": round(high_match / total_valid * 100, 2) if total_valid > 0 else 0,
            "acceptable_count": acceptable,
            "acceptable_pct": round(acceptable / total_valid * 100, 2) if total_valid > 0 else 0,
            "entity_recall_all": round(gt_matched_all / gt_total_all * 100, 2) if gt_total_all > 0 else 0,
            "entity_recall_units": round(gt_unit_matched / gt_unit_total * 100, 2) if gt_unit_total > 0 else 0,
            "entity_recall_persons": round(gt_person_matched / gt_person_total * 100, 2) if gt_person_total > 0 else 0,
        },
        "mention_kinds": dict(mention_kinds_counter),
        "category_counts": dict(category_counts),
        "scanned_folders": scanned_docs,
        "no_pdf_folders": no_pdf_docs,
        "no_mention_folders": no_mention_docs,
        "results": results
    }

    out_file = pathlib.Path("var/extraction_evaluation_results.json")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(report_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nĐã lưu kết quả chi tiết vào: {out_file}")


if __name__ == "__main__":
    main()
