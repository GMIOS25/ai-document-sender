import json
import zipfile
import xml.etree.ElementTree as ET
import re

def deep_check():
    with open('mismatched_docs.json', 'r', encoding='utf-8') as f:
        mismatched = json.load(f)
        
    print(f"Total mismatched docs loaded: {len(mismatched)}")
    
    # Categorize them strictly:
    # 1. Has exception (act_exception > 0)
    # 2. Has yellow diff (yellow_diff != 0)
    # 3. Has thieu diff (thieu_diff != 0)
    
    cat_exception = []
    cat_yellow_diff = []
    cat_thieu_diff = []
    
    for d in mismatched:
        stt = d['stt']
        y_diff = d['yellow_diff']
        t_diff = d['thieu_diff']
        e_diff = d['exception_diff']
        act_e = d['act_exception']
        
        flags = []
        if act_e > 0:
            flags.append(f"act_e={act_e}")
        if y_diff != 0:
            flags.append(f"y_diff={y_diff}")
        if t_diff != 0:
            flags.append(f"t_diff={t_diff}")
            
        print(f"STT {stt} ({d['so_hieu']}, R:{d['range']}): {', '.join(flags)} | H_du={d['h_du']}, Act_y={d['act_yellow']} | H_th={d['h_thieu']}, Act_r={d['act_red']} | H_ex={d['h_ngoai_le']}, Act_ex={d['act_exception']}")

if __name__ == '__main__':
    deep_check()
