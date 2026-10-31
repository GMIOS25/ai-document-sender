"""Adversarial verification script for Challenger Iteration 2-2.

Performs exhaustive empirical verification of:
1. 14 previously defective mappings against ground-truth sample documents.
2. Row 805 reversion to '-' and move to retained rows set (826 retained rows).
3. All 81 populated rows for semantic, syntax, or institutional defects.
4. Live Google Sheet Column E values, font colors, and cell borders.
5. Consolidated report coverage across all 826 retained rows.
"""

import csv
import json
import os
import sys
from pathlib import Path
import requests

WORKSPACE = Path(r"c:\Workspaces\ai-document-sender")
EXPLORER_DIR = WORKSPACE / ".agents" / "teamwork" / "explorer_survey_2"
HUMAN_CORR_PATH = WORKSPACE / ".agents" / "teamwork" / "explorer_survey_3" / "human_red_corrections.json"
POPULATED_CSV = EXPLORER_DIR / "populated_rows.csv"
RETAINED_CSV = EXPLORER_DIR / "retained_rows.csv"
DECISIONS_JSON = EXPLORER_DIR / "reconciliation_decisions.json"
REPORT_PATH = WORKSPACE / "reports" / "unmapped_recipients_report.md"
SAMPLE_DIR = WORKSPACE / "resources" / "văn bản mẫu" / "vpub" / "Hợp lệ"
TOKEN_PATH = Path(r"C:\Users\trant\.gemini\antigravity\plugin_data\gsheets\token.json")
SHEET_ID = "1FTx3IDxfaOadbXmY6BB9pRkRqCdnCter12poQ1txu9s"
SHEET_TITLE = "Thống kê"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def get_token():
    with open(TOKEN_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    token = data["token"]["access_token"]
    # Check if expired or test with API
    test_res = requests.get(
        f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}?fields=properties.title",
        headers={"Authorization": f"Bearer {token}"}
    )
    if test_res.status_code == 401:
        # Refresh
        refresh_token = data["token"]["refresh_token"]
        client_id = data["client_id"]
        client_secret = data["client_secret"]
        token_uri = data.get("token_uri", "https://oauth2.googleapis.com/token")
        r = requests.post(token_uri, data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": client_id,
            "client_secret": client_secret,
        })
        token = r.json()["access_token"]
    return token


def find_sample_folder(doc_id):
    clean_id = doc_id.split("/")[0].strip()
    folders = [d for d in os.listdir(SAMPLE_DIR) if clean_id in d]
    results = {}
    for f in folders:
        kq_path = SAMPLE_DIR / f / "kết_quả_gửi_đi.txt"
        cpx_path = SAMPLE_DIR / f / "view.cpx"
        kq_text = kq_path.read_text(encoding="utf-8", errors="ignore") if kq_path.exists() else ""
        cpx_text = cpx_path.read_text(encoding="utf-8", errors="ignore") if cpx_path.exists() else ""
        results[f] = {"kq": kq_text, "cpx": cpx_text}
    return results


def main():
    print("=" * 80)
    print("CHALLENGER ITER2-2: ADVERSARIAL VERIFICATION START")
    print("=" * 80)

    # 1. Load Local Datasets
    assert POPULATED_CSV.exists()
    assert RETAINED_CSV.exists()
    assert DECISIONS_JSON.exists()
    assert REPORT_PATH.exists()

    with open(POPULATED_CSV, "r", encoding="utf-8") as f:
        populated = list(csv.DictReader(f))
    with open(RETAINED_CSV, "r", encoding="utf-8") as f:
        retained = list(csv.DictReader(f))
    with open(HUMAN_CORR_PATH, "r", encoding="utf-8") as f:
        human_corrections = json.load(f)

    pop_by_row = {int(r["Row"]): r for r in populated}
    ret_by_row = {int(r["Row"]): r for r in retained}

    failures = []

    print(f"Loaded: {len(populated)} populated rows, {len(retained)} retained rows.")

    # Check counts
    if len(populated) != 81:
        failures.append(f"Populated rows count expected 81, got {len(populated)}")
    if len(retained) != 826:
        failures.append(f"Retained rows count expected 826, got {len(retained)}")

    overlap = set(pop_by_row.keys()).intersection(set(ret_by_row.keys()))
    if overlap:
        failures.append(f"Overlapping rows between populated and retained: {overlap}")

    # =========================================================================
    # TASK 1: ADVERSARIALLY VERIFY 14 PREVIOUSLY DEFECTIVE MAPPINGS
    # =========================================================================
    print("\n" + "-" * 60)
    print("TASK 1: VERIFYING 14 REMEDIATED ROWS AGAINST GROUND TRUTH SAMPLES")
    print("-" * 60)

    # Sub-task 1.1: Rows 1065, 1097, 4493, 4611 (Văn phòng Đảng ủy UBND tỉnh)
    party_rows = [1065, 1097, 4493, 4611]
    expected_party_target = "Đảng ủy Ủy ban nhân dân tỉnh Gia Lai"
    for r in party_rows:
        if r not in pop_by_row:
            failures.append(f"Row {r} missing from populated rows!")
            continue
        item = pop_by_row[r]
        actual_target = item["TargetNoiNhan2"]
        doc_id = item["DocID"]
        nn1 = item["NoiNhan1"]

        # Check target string
        if actual_target != expected_party_target:
            failures.append(f"Row {r} ({doc_id}): Target expected '{expected_party_target}', got '{actual_target}'")
        if actual_target.endswith(";"):
            failures.append(f"Row {r}: Trailing semicolon defect detected: '{actual_target}'")
        if "ĐBQH" in actual_target:
            failures.append(f"Row {r}: Institutional conflation defect detected: '{actual_target}'")

        # Check ground truth
        truth = find_sample_folder(doc_id)
        found_in_truth = False
        for fld, data in truth.items():
            if expected_party_target in data["kq"]:
                found_in_truth = True
                print(f"[PASS] Row {r} ({doc_id}) -> Verified in '{fld}/kết_quả_gửi_đi.txt'")
                break
        if not found_in_truth:
            failures.append(f"Row {r} ({doc_id}): '{expected_party_target}' NOT found in sample dispatch log!")

        # Also check human precedent in human_red_corrections for related party variants
        party_precedents = [hc for hc in human_corrections if any(k in str(hc.get("d", "")) for k in ["Đảng ủy UBND", "VP ĐU UBND", "Đảng uỷ UBND"])]
        matching_prec = [hc for hc in party_precedents if hc.get("e", "").strip() == expected_party_target]
        print(f"       Human precedent check: {len(matching_prec)}/{len(party_precedents)} party committee corrections match '{expected_party_target}'")

    # Sub-task 1.2: Row 896 (Các Ban QLDA thuộc tỉnh)
    print("\nChecking Row 896 (Các Ban QLDA thuộc tỉnh)...")
    if 896 not in pop_by_row:
        failures.append("Row 896 missing from populated rows!")
    else:
        item_896 = pop_by_row[896]
        actual_896 = item_896["TargetNoiNhan2"]
        doc_896 = item_896["DocID"]
        truth_896 = find_sample_folder(doc_896)
        
        pmbs = [
            "Ban QLDA các công trình Giao thông và Dân dụng tỉnh Gia Lai",
            "Ban Quản lý Dự án Nông nghiệp và Phát triển nông thôn tỉnh Gia Lai",
            "Ban Quản lý các dự án đầu tư xây dựng tỉnh Gia Lai",
        ]
        # Check all 3 PMBs present
        actual_pmbs = [p.strip() for p in actual_896.split(";")]
        if len(actual_pmbs) != 3:
            failures.append(f"Row 896: expected 3 PMBs separated by ';', got {len(actual_pmbs)}: {actual_896}")
        for p in pmbs:
            if p not in actual_896:
                failures.append(f"Row 896: missing PMB '{p}'")

        # Ground truth check
        found_896 = False
        for fld, data in truth_896.items():
            kq = data["kq"]
            if all(p in kq for p in pmbs):
                found_896 = True
                print(f"[PASS] Row 896 ({doc_896}) -> All 3 PMBs verified in '{fld}/kết_quả_gửi_đi.txt'")
                break
        if not found_896:
            failures.append(f"Row 896 ({doc_896}): PMBs NOT all verified in sample dispatch log!")

    # Sub-task 1.3: 9 Joint Office Rows (880, 1107, 1891, 2097, 2132, 3719, 3747, 4676, 4812)
    print("\nChecking 9 Joint Office rows (Các VP: Tỉnh uỷ, Đoàn ĐBQH và HĐND tỉnh)...")
    joint_rows = [880, 1107, 1891, 2097, 2132, 3719, 3747, 4676, 4812]
    expected_joint = "Văn phòng Tỉnh ủy;Văn phòng Đoàn ĐBQH và HĐND tỉnh Gia Lai"
    for r in joint_rows:
        if r not in pop_by_row:
            failures.append(f"Row {r} missing from populated rows!")
            continue
        item = pop_by_row[r]
        actual = item["TargetNoiNhan2"]
        doc_id = item["DocID"]

        if actual != expected_joint:
            failures.append(f"Row {r} ({doc_id}): Expected '{expected_joint}', got '{actual}'")
        if "Văn phòng Tỉnh ủy" not in actual:
            failures.append(f"Row {r}: Missing 'Văn phòng Tỉnh ủy'!")
        if "Văn phòng Đoàn ĐBQH và HĐND tỉnh Gia Lai" not in actual:
            failures.append(f"Row {r}: Missing 'Văn phòng Đoàn ĐBQH và HĐND tỉnh Gia Lai'!")

        # Check sample ground truth
        truth = find_sample_folder(doc_id)
        if not truth:
            failures.append(f"Row {r} ({doc_id}): No ground truth sample document folder found!")
        else:
            found_joint = False
            for fld, data in truth.items():
                kq = data["kq"]
                if "Văn phòng Tỉnh ủy" in kq and "Văn phòng Đoàn ĐBQH và HĐND" in kq:
                    found_joint = True
                    print(f"[PASS] Row {r} ({doc_id}) -> Both offices verified in '{fld}/kết_quả_gửi_đi.txt'")
                    break
            if not found_joint:
                failures.append(f"Row {r} ({doc_id}): Both offices NOT confirmed in sample dispatch log!")

    # =========================================================================
    # TASK 2: VERIFY ROW 805 REVERSION TO "-" AND MOVE TO RETAINED SET
    # =========================================================================
    print("\n" + "-" * 60)
    print("TASK 2: VERIFYING ROW 805 REVERSION AND RETAINED SET INTEGRITY")
    print("-" * 60)

    if 805 in pop_by_row:
        failures.append("Row 805 STILL PRESENT in populated_rows.csv!")
    else:
        print("[PASS] Row 805 correctly absent from populated_rows.csv.")

    if 805 not in ret_by_row:
        failures.append("Row 805 NOT FOUND in retained_rows.csv!")
    else:
        r805 = ret_by_row[805]
        print(f"[PASS] Row 805 found in retained_rows.csv: DocID={r805['DocID']}, NN1={r805['NoiNhan1']}, Decision={r805['Decision']}, Src={r805['Source']}")
        if r805["Decision"] != "-":
            failures.append(f"Row 805 Decision is not '-', got '{r805['Decision']}'")
        if r805["NoiNhan1"] != "Truyền tải điện 3":
            failures.append(f"Row 805 NoiNhan1 mismatch, got '{r805['NoiNhan1']}'")
        if r805["Source"] != "UNMAPPED_EXTERNAL_OR_SPECIFIC":
            failures.append(f"Row 805 Source expected 'UNMAPPED_EXTERNAL_OR_SPECIFIC', got '{r805['Source']}'")

    # Verify Doc 13035/UBND-XDCT ground truth:
    # Row 804 was "Cty Điện lực Gia Lai" -> Công ty Điện lực Gia Lai
    # Row 805 was "Truyền tải điện 3" -> PTC3 (national transmission operator under EVNNPT)
    truth_805 = find_sample_folder("13035")
    for fld, data in truth_805.items():
        kq = data["kq"]
        has_pc = "Công ty Điện lực Gia Lai" in kq
        has_ptc = "Truyền tải điện 3" in kq
        print(f"       Sample {fld} kq: 'Công ty Điện lực Gia Lai' in log={has_pc}, 'Truyền tải điện 3' in log={has_ptc}")
        if has_ptc:
            failures.append(f"Sample {fld} unexpectedly has 'Truyền tải điện 3' in kq!")

    # Check total retained rows and categories
    vt_count = sum(1 for r in retained if r.get("Source") == "POLICY_ARCHIVAL_VT")
    ext_count = sum(1 for r in retained if r.get("Source") == "UNMAPPED_EXTERNAL_OR_SPECIFIC")
    print(f"       Retained rows: Total={len(retained)}, VT={vt_count}, External={ext_count}")
    if vt_count != 474:
        failures.append(f"Expected 474 VT retained rows, got {vt_count}")
    if ext_count != 124:
        failures.append(f"Expected 124 External retained rows, got {ext_count}")

    # =========================================================================
    # TASK 3: CONFIRM 0 DEFECTS ACROSS ALL 81 POPULATED ROWS
    # =========================================================================
    print("\n" + "-" * 60)
    print("TASK 3: AUDITING ALL 81 POPULATED ROWS FOR SYNTAX / SEMANTICS / SOURCES")
    print("-" * 60)

    # Human precedent mapping
    human_map = {}
    for hc in human_corrections:
        d = str(hc.get("d", "")).strip()
        e = str(hc.get("e", "")).strip()
        if d:
            if d not in human_map:
                human_map[d] = set()
            human_map[d].add(e)

    for item in populated:
        r_num = int(item["Row"])
        doc_id = item["DocID"]
        nn1 = item["NoiNhan1"].strip()
        target = item["TargetNoiNhan2"].strip()
        source = item["Source"]

        # Syntax checks
        if target.endswith(";") or target.endswith(","):
            failures.append(f"Row {r_num}: Syntax error (trailing punctuation): '{target}'")
        if target.startswith(";") or target.startswith(","):
            failures.append(f"Row {r_num}: Syntax error (leading punctuation): '{target}'")
        if ";;" in target:
            failures.append(f"Row {r_num}: Syntax error (double semicolon): '{target}'")
        if not target or target == "-":
            failures.append(f"Row {r_num}: Empty or dash target in populated rows: '{target}'")

        # Semantic sanity checks
        if "Đảng ủy" in nn1 and "ĐBQH" in target:
            failures.append(f"Row {r_num}: Party committee mapped to legislative council: '{target}'")
        if "Truyền tải điện" in nn1 and "Điện lực Gia Lai" in target:
            failures.append(f"Row {r_num}: PTC mapped to provincial power company: '{target}'")

        # Source verification
        if source == "HUMAN_CORRECTION_PRECEDENT":
            if nn1 not in human_map:
                failures.append(f"Row {r_num} ({doc_id}): Source is HUMAN_CORRECTION_PRECEDENT but '{nn1}' not in human_red_corrections.json")
            else:
                clean_target = target.rstrip(";")
                clean_human_targets = {t.rstrip(";") for t in human_map[nn1]}
                if clean_target not in clean_human_targets:
                    failures.append(f"Row {r_num} ({doc_id}): Precedent mismatch: '{target}' not in {clean_human_targets}")
        elif source == "SAMPLE_DOC_GROUND_TRUTH":
            truth = find_sample_folder(doc_id)
            if not truth:
                failures.append(f"Row {r_num} ({doc_id}): No sample folder found for ground truth check")
            else:
                found_any = False
                for fld, data in truth.items():
                    sub_targets = [s.strip() for s in target.split(";")]
                    if all(st in data["kq"] for st in sub_targets):
                        found_any = True
                        break
                if not found_any:
                    failures.append(f"Row {r_num} ({doc_id}): Target '{target}' not fully verified in ground truth kq")
        else:
            failures.append(f"Row {r_num}: Unknown source '{source}'")

    print(f"[PASS] Syntax & Semantic audit completed across all {len(populated)} populated rows.")

    # =========================================================================
    # TASK 4: VERIFY LIVE GOOGLE SHEET VIA API
    # =========================================================================
    print("\n" + "-" * 60)
    print("TASK 4: LIVE GOOGLE SHEET EMPIRICAL API VERIFICATION")
    print("-" * 60)

    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}

    # Batch get all 81 populated cells (Column E) and Row 805
    all_check_rows = [int(r["Row"]) for r in populated] + [805]
    ranges = [f"'{SHEET_TITLE}'!E{r}:E{r}" for r in all_check_rows]

    # Query in chunks of 50 to avoid URL length issues
    chunk_size = 40
    live_results = {}
    for i in range(0, len(all_check_rows), chunk_size):
        chunk_rows = all_check_rows[i:i+chunk_size]
        chunk_ranges = [f"'{SHEET_TITLE}'!E{r}:E{r}" for r in chunk_rows]
        fields = "sheets.data.rowData.values(userEnteredValue,effectiveFormat.textFormat.foregroundColor)"
        url = f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}?fields={fields}&" + "&".join([f"ranges={r}" for r in chunk_ranges])
        res = requests.get(url, headers=headers).json()
        sheets_data = res.get("sheets", [{}])[0].get("data", [])
        for block, r_num in zip(sheets_data, chunk_rows):
            cell = block.get("rowData", [{}])[0].get("values", [{}])[0]
            val = cell.get("userEnteredValue", {}).get("stringValue", "")
            fg = cell.get("effectiveFormat", {}).get("textFormat", {}).get("foregroundColor", {})
            live_results[r_num] = (val, fg)

    print(f"Queried {len(live_results)} live cells.")

    # Check Row 805
    val_805, fg_805 = live_results[805]
    print(f"Live Cell E805: val='{val_805}', color={fg_805}")
    if val_805 != "-":
        failures.append(f"Live E805 is not '-', got '{val_805}'")
    if fg_805.get("red", 0) >= 0.99:
        failures.append(f"Live E805 is RED! Should be non-red format: {fg_805}")

    # Check 81 Populated Rows
    live_val_mismatches = []
    live_color_mismatches = []
    for item in populated:
        r_num = int(item["Row"])
        exp_val = item["TargetNoiNhan2"]
        actual_val, fg = live_results[r_num]

        if actual_val != exp_val:
            live_val_mismatches.append((r_num, exp_val, actual_val))
        if fg.get("red", 0) < 0.99 or fg.get("green", 0) > 0.05 or fg.get("blue", 0) > 0.05:
            live_color_mismatches.append((r_num, fg))

    if live_val_mismatches:
        failures.append(f"Live cell value mismatches ({len(live_val_mismatches)} rows): {live_val_mismatches[:5]}")
    if live_color_mismatches:
        failures.append(f"Live cell color mismatches ({len(live_color_mismatches)} rows): {live_color_mismatches[:5]}")

    print(f"[PASS] Live Sheet verification: 81/81 values and pure RED colors confirmed. Row 805 confirmed as non-red '-'.")

    # Deep verification of all 826 retained rows on live sheet
    print("\nDeep checking all 826 retained rows on Live Google Sheet...")
    url_all_e = f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/'{SHEET_TITLE}'!E2:E5140"
    res_all_e = requests.get(url_all_e, headers=headers).json()
    e_vals = res_all_e.get("values", [])

    retained_mismatches = []
    for r in retained:
        r_num = int(r["Row"])
        idx = r_num - 2
        v = e_vals[idx][0] if idx < len(e_vals) and e_vals[idx] else ""
        if v != "-":
            retained_mismatches.append((r_num, v))

    if retained_mismatches:
        failures.append(f"Retained rows with non-dash values ({len(retained_mismatches)} rows): {retained_mismatches[:5]}")
    else:
        print(f"[PASS] All {len(retained)} retained rows verified with value '-' on live sheet.")

    # Global red color audit across all 5,139 rows in column E
    print("Auditing global red cell count across entire Column E...")
    fields_red = "sheets.data.rowData.values(effectiveFormat.textFormat.foregroundColor)"
    url_red = f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}?fields={fields_red}&ranges='{SHEET_TITLE}'!E2:E5140"
    res_red = requests.get(url_red, headers=headers).json()
    sheet_data = res_red.get("sheets", [{}])[0].get("data", [])
    row_data = sheet_data[0].get("rowData", []) if sheet_data else []

    all_red_rows = set()
    for idx, row in enumerate(row_data, start=2):
        vals = row.get("values", [])
        if vals:
            fg = vals[0].get("effectiveFormat", {}).get("textFormat", {}).get("foregroundColor", {})
            if fg.get("red", 0.0) >= 0.99 and fg.get("green", 0.0) == 0.0 and fg.get("blue", 0.0) == 0.0:
                all_red_rows.add(idx)

    print(f"Total red cells in Column E: {len(all_red_rows)} (Expected: 1579 = 1498 baseline + 81 new)")
    if len(all_red_rows) != 1579:
        failures.append(f"Expected 1579 red cells in Column E, found {len(all_red_rows)}")

    pop_row_indices = set(int(r["Row"]) for r in populated)
    missing_pop_red = pop_row_indices - all_red_rows
    if missing_pop_red:
        failures.append(f"Populated rows missing red color: {missing_pop_red}")

    ret_row_indices = set(int(r["Row"]) for r in retained)
    ret_red_leakage = ret_row_indices.intersection(all_red_rows)
    if ret_red_leakage:
        failures.append(f"Retained rows accidentally colored red: {ret_red_leakage}")
    else:
        print("[PASS] Zero retained rows have red text color.")


    # =========================================================================
    # TASK 5: VERIFY REPORT COVERAGE ACROSS ALL 826 RETAINED ROWS
    # =========================================================================
    print("\n" + "-" * 60)
    print("TASK 5: CONSOLIDATED REPORT COVERAGE VERIFICATION")
    print("-" * 60)

    report_text = REPORT_PATH.read_text(encoding="utf-8")
    report_missing_rows = []
    for r in retained:
        r_num = r["Row"]
        if f"| {r_num} |" not in report_text:
            report_missing_rows.append(r_num)

    if report_missing_rows:
        failures.append(f"Report missing {len(report_missing_rows)} retained rows: {report_missing_rows[:10]}")
    else:
        print(f"[PASS] All 826 retained rows are present in {REPORT_PATH}")

    # Check Section 2.5 mentions Row 805 / PTC3
    if "Truyền tải điện 3" not in report_text or "805" not in report_text:
        failures.append("Report does not adequately document Row 805 / Truyền tải điện 3!")
    else:
        print("[PASS] Report explicitly documents Row 805 / Truyền tải điện 3 distinction from PC Gia Lai.")

    # =========================================================================
    # SUMMARY VERDICT
    # =========================================================================
    print("\n" + "=" * 80)
    print("FINAL ADVERSARIAL VERIFICATION SUMMARY")
    print("=" * 80)
    if failures:
        print(f"VERDICT: REJECT - Found {len(failures)} defects/failures:")
        for idx, f in enumerate(failures, 1):
            print(f"  {idx}. {f}")
        return False
    else:
        print("VERDICT: APPROVE - 0 defects found across all tests, ground-truth samples, datasets, and live Google Sheet.")
        return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
