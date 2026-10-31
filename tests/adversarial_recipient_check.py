import csv
import json
import os
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def load_thong_ke():
    path = r'c:\Workspaces\ai-document-sender\.agents\teamwork\explorer_survey_2\thong_ke.csv'
    rows = {}
    with open(path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        for idx, row in enumerate(reader, 1):
            rows[idx] = row
    return rows

def load_human_corrections():
    path = r'c:\Workspaces\ai-document-sender\.agents\teamwork\explorer_survey_3\human_red_corrections.json'
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def load_populated_rows():
    path = r'c:\Workspaces\ai-document-sender\.agents\teamwork\explorer_survey_2\populated_rows.csv'
    rows = []
    with open(path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)
    return rows

def load_retained_rows():
    path = r'c:\Workspaces\ai-document-sender\.agents\teamwork\explorer_survey_2\retained_rows.csv'
    rows = []
    with open(path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)
    return rows

def get_sample_doc_truth(doc_id_prefix):
    # E.g. '13101'
    clean_id = doc_id_prefix.split('/')[0].strip()
    root = r'c:\Workspaces\ai-document-sender\resources\văn bản mẫu\vpub\Hợp lệ'
    matching_folders = [d for d in os.listdir(root) if clean_id in d]
    results = {}
    for folder_name in matching_folders:
        folder_path = os.path.join(root, folder_name)
        kq_file = os.path.join(folder_path, 'kết_quả_gửi_đi.txt')
        cpx_file = os.path.join(folder_path, 'view.cpx')
        
        kq_text = ""
        if os.path.exists(kq_file):
            with open(kq_file, 'r', encoding='utf-8', errors='ignore') as f:
                kq_text = f.read()
        
        cpx_text = ""
        if os.path.exists(cpx_file):
            with open(cpx_file, 'r', encoding='utf-8', errors='ignore') as f:
                cpx_text = f.read()
                
        results[folder_name] = {
            'ket_qua_gui_di': kq_text,
            'cpx': cpx_text
        }
    return results

def main():
    thong_ke = load_thong_ke()
    human_corrections = load_human_corrections()
    populated = load_populated_rows()
    retained = load_retained_rows()
    
    print(f"Loaded {len(populated)} populated rows, {len(retained)} retained rows, {len(human_corrections)} human corrections.")
    
    findings = []
    
    # 1. Adversarial verification of 82 populated rows
    print("\n" + "="*80)
    print("VERIFYING 82 POPULATED ROWS AGAINST HUMAN CORRECTIONS & GROUND TRUTH")
    print("="*80)
    
    # Map human corrections by raw text
    human_map = {}
    for hc in human_corrections:
        nn1 = str(hc.get('d', '')).strip()
        nn2 = str(hc.get('e', '')).strip()
        if nn1:
            if nn1 not in human_map:
                human_map[nn1] = set()
            human_map[nn1].add(nn2)
            
    for item in populated:
        row_num = int(item['Row'])
        doc_id = item['DocID']
        nn1 = item['NoiNhan1'].strip()
        target_nn2 = item['TargetNoiNhan2'].strip()
        source = item['Source']
        notes = item['Notes']
        
        # Check against ground truth
        clean_doc = doc_id.split('/')[0].strip()
        ground_truth = get_sample_doc_truth(clean_doc)
        
        issue = None
        
        # Check 1: Trailing punctuation / syntax errors
        if target_nn2.endswith(';') or target_nn2.endswith(','):
            issue = f"Syntax error: target has trailing punctuation '{target_nn2[-1]}'"
            findings.append({
                'row': row_num,
                'doc_id': doc_id,
                'nn1': nn1,
                'target': target_nn2,
                'type': 'SYNTAX_ERROR',
                'description': issue
            })
            
        # Check 2: Semantic mismatch / Hallucination
        # E.g. 'Văn phòng Đảng ủy' -> 'Văn phòng Đoàn ĐBQH và HĐND'
        if 'Đảng ủy' in nn1 and 'ĐBQH' in target_nn2:
            issue = "SEMANTIC_FALSE_POSITIVE: Party Committee of PPC mapped to National Assembly Delegation & People's Council!"
            findings.append({
                'row': row_num,
                'doc_id': doc_id,
                'nn1': nn1,
                'target': target_nn2,
                'type': 'CRITICAL_FALSE_MATCH',
                'description': issue
            })
            
        # Check 3: Transmission grid vs distribution grid (Truyền tải điện 3 vs Công ty Điện lực Gia Lai)
        if 'Truyền tải điện' in nn1 and 'Công ty Điện lực Gia Lai' in target_nn2:
            issue = "ENTITY_MISMATCH: PTC3 (Power Transmission Co 3) mapped to PC Gia Lai (Provincial Power Co)"
            findings.append({
                'row': row_num,
                'doc_id': doc_id,
                'nn1': nn1,
                'target': target_nn2,
                'type': 'ENTITY_MISMATCH',
                'description': issue
            })
            
        # Check 4: Plural entity partial mapping (Các Ban QLDA thuộc tỉnh)
        if 'Các Ban QLDA' in nn1 and ';' not in target_nn2:
            # Check ground truth
            for folder_k, gdata in ground_truth.items():
                kq = gdata['ket_qua_gui_di']
                pmb_count = sum(1 for p in ['Ban QLDA các công trình Giao thông và Dân dụng', 'Ban Quản lý Dự án Nông nghiệp', 'Ban Quản lý các dự án đầu tư xây dựng'] if p in kq)
                if pmb_count > 1:
                    issue = f"INCOMPLETE_PLURAL_MAPPING: 'Các Ban QLDA' only mapped to 1 PMB, but ground truth dispatched to {pmb_count} PMBs"
                    findings.append({
                        'row': row_num,
                        'doc_id': doc_id,
                        'nn1': nn1,
                        'target': target_nn2,
                        'type': 'INCOMPLETE_MAPPING',
                        'description': issue
                    })
                    
        # Check 5: If Source is HUMAN_CORRECTION_PRECEDENT, verify if human precedent actually exists
        if source == 'HUMAN_CORRECTION_PRECEDENT':
            # Check if nn1 is in human_map and target_nn2 is in human_map[nn1]
            # Strip trailing semicolon for comparison
            clean_target = target_nn2.rstrip(';')
            clean_human_targets = {t.rstrip(';') for t in human_map.get(nn1, set())}
            
            if nn1 not in human_map:
                issue = f"FALSE_PRECEDENT: nn1 '{nn1}' has NEVER been corrected by human clerical staff in human_red_corrections.json!"
                findings.append({
                    'row': row_num,
                    'doc_id': doc_id,
                    'nn1': nn1,
                    'target': target_nn2,
                    'type': 'FABRICATED_PRECEDENT',
                    'description': issue
                })
            elif clean_target not in clean_human_targets:
                issue = f"PRECEDENT_MISMATCH: Target '{target_nn2}' does not match human corrections for '{nn1}': {human_map[nn1]}"
                findings.append({
                    'row': row_num,
                    'doc_id': doc_id,
                    'nn1': nn1,
                    'target': target_nn2,
                    'type': 'PRECEDENT_MISMATCH',
                    'description': issue
                })
                
        # Check 6: If Source is SAMPLE_DOC_GROUND_TRUTH, verify presence in actual ground truth
        if source == 'SAMPLE_DOC_GROUND_TRUTH':
            if not ground_truth:
                issue = f"MISSING_SAMPLE_DOC: No sample document folder found for doc ID '{clean_doc}'"
                findings.append({
                    'row': row_num,
                    'doc_id': doc_id,
                    'nn1': nn1,
                    'target': target_nn2,
                    'type': 'MISSING_SAMPLE_DOC',
                    'description': issue
                })
            else:
                found_in_truth = False
                for folder_k, gdata in ground_truth.items():
                    kq = gdata['ket_qua_gui_di']
                    if all(sub.strip() in kq for sub in target_nn2.split(';')):
                        found_in_truth = True
                        break
                if not found_in_truth:
                    issue = f"NOT_IN_GROUND_TRUTH: Target '{target_nn2}' not found in ket_qua_gui_di.txt for doc {clean_doc}"
                    findings.append({
                        'row': row_num,
                        'doc_id': doc_id,
                        'nn1': nn1,
                        'target': target_nn2,
                        'type': 'GROUND_TRUTH_ABSENCE',
                        'description': issue
                    })
                    
    print(f"\nTotal findings in {len(populated)} populated rows: {len(findings)}")
    for f in findings:
        print(f"Row {f['row']} ({f['doc_id']}): [{f['type']}] NN1='{f['nn1']}' -> Target='{f['target']}'")
        print(f"   Details: {f['description']}")
        
    return findings

if __name__ == '__main__':
    main()
