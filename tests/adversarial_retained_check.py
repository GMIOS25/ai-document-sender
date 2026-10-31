import csv
import json
import os
import sys

def main():
    thong_ke_path = r'c:\Workspaces\ai-document-sender\.agents\teamwork\explorer_survey_2\thong_ke.csv'
    human_corrections_path = r'c:\Workspaces\ai-document-sender\.agents\teamwork\explorer_survey_3\human_red_corrections.json'
    retained_path = r'c:\Workspaces\ai-document-sender\.agents\teamwork\explorer_survey_2\retained_rows.csv'
    sample_root = r'c:\Workspaces\ai-document-sender\resources\văn bản mẫu\vpub\Hợp lệ'
    
    with open(human_corrections_path, 'r', encoding='utf-8') as f:
        human_corrections = json.load(f)
        
    human_map = {}
    for hc in human_corrections:
        d = str(hc.get('d', '')).strip()
        e = str(hc.get('e', '')).strip()
        if d:
            if d not in human_map:
                human_map[d] = set()
            human_map[d].add(e)
            
    # Check VT in human corrections
    vt_in_human = [hc for hc in human_corrections if str(hc.get('d', '')).strip() in ['VT', 'Lưu: VT', 'Lưu VT']]
    print(f"VT appearances in human corrections: {len(vt_in_human)}")
    for vh in vt_in_human[:5]:
        print(f"   Row {vh.get('row')}: d='{vh.get('d')}', e='{vh.get('e')}'")
        
    # Read retained rows
    retained = []
    with open(retained_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            retained.append(r)
            
    print(f"\nTotal retained rows: {len(retained)}")
    
    # Categorize and check if any retained row had a match in human_map
    retained_with_human_match = []
    for r in retained:
        row_id = r.get('Row')
        doc_id = r.get('DocID')
        nn1 = r.get('NoiNhan1', '').strip()
        cat = r.get('Category', '')
        
        if nn1 in human_map:
            targets = human_map[nn1]
            # Exclude if human target was '-' or empty
            valid_targets = [t for t in targets if t and t != '-']
            if valid_targets:
                retained_with_human_match.append({
                    'row': row_id,
                    'doc_id': doc_id,
                    'nn1': nn1,
                    'category': cat,
                    'human_targets': valid_targets
                })
                
    print(f"\nRetained rows that actually had positive human corrections in human_red_corrections.json: {len(retained_with_human_match)}")
    for rhm in retained_with_human_match[:20]:
        print(f"Row {rhm['row']} ({rhm['doc_id']}): NN1='{rhm['nn1']}' -> Human target(s): {rhm['human_targets']}")

if __name__ == '__main__':
    main()
