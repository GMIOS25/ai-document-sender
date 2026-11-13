import json

def check_day_du():
    with open('verified_58_docs.json', 'r', encoding='utf-8') as f:
        mismatched = json.load(f)
    print("Mismatched STTs:", [m['stt'] for m in mismatched])
    
    # Are any of the mismatched docs currently labeled "Đầy đủ" in Column H?
    # Let's check!
    # If a doc was labeled "Đầy đủ", but had Yellow or Red or Exception, it would be in mismatched!
    # Did any mismatched doc have h_du == 0 and h_thieu == 0?
    labeled_day_du_but_mismatched = [m for m in mismatched if m['h_du'] == 0 and m['h_thieu'] == 0]
    print(f"Docs labeled 'Đầy đủ' but actually mismatched: {len(labeled_day_du_but_mismatched)}")
    for m in labeled_day_du_but_mismatched:
        print(f"  STT {m['stt']} ({m['so_hieu']}): act_y={m['act_y']}, act_r={m['act_r']}, act_ex={m['act_ex']}")

if __name__ == '__main__':
    check_day_du()
