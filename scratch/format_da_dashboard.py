import json
import requests
from pathlib import Path

TOKEN_PATH = Path(r"C:\Users\trant\.gemini\antigravity\plugin_data\gsheets\token.json")
SPREADSHEET_ID = "1FTx3IDxfaOadbXmY6BB9pRkRqCdnCter12poQ1txu9s"
SHEET_TITLE = "Thống kê Đánh giá (DA)"

def hex_to_rgb(hex_str):
    hex_str = hex_str.lstrip("#")
    r = int(hex_str[0:2], 16) / 255.0
    g = int(hex_str[2:4], 16) / 255.0
    b = int(hex_str[4:6], 16) / 255.0
    return {"red": round(r, 3), "green": round(g, 3), "blue": round(b, 3)}

def get_valid_token():
    with open(TOKEN_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    token = data["token"]["access_token"]
    refresh_token = data["token"].get("refresh_token")
    client_id = data.get("client_id")
    client_secret = data.get("client_secret")

    test_url = f"https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}?fields=properties.title"
    r = requests.get(test_url, headers={"Authorization": f"Bearer {token}"})
    if r.status_code == 401 and refresh_token and client_id and client_secret:
        rf = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
        )
        if rf.status_code == 200:
            token = rf.json()["access_token"]
            data["token"]["access_token"] = token
            with open(TOKEN_PATH, "w", encoding="utf-8") as f_out:
                json.dump(data, f_out, indent=2)
    return token

def format_dashboard():
    token = get_valid_token()
    headers = {"Authorization": f"Bearer {token}"}

    # Fetch sheet ID
    meta_url = f"https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}?fields=sheets.properties"
    res = requests.get(meta_url, headers=headers).json()
    sheet_id = None
    for s in res.get("sheets", []):
        if s["properties"]["title"] == SHEET_TITLE:
            sheet_id = s["properties"]["sheetId"]
            break
    assert sheet_id is not None, f"Sheet '{SHEET_TITLE}' not found!"
    print(f"Formatting sheet '{SHEET_TITLE}' (ID: {sheet_id})...")

    requests_list = []

    # 1. Unfreeze any existing and freeze rows 1 to 4
    requests_list.append({
        "updateSheetProperties": {
            "properties": {
                "sheetId": sheet_id,
                "gridProperties": {
                    "frozenRowCount": 0, # Don't freeze top rows to keep dashboard flowing naturally
                    "hideGridlines": False
                }
            },
            "fields": "gridProperties.frozenRowCount,gridProperties.hideGridlines"
        }
    })

    # 2. Set Column Widths (A to G)
    col_widths = [
        (0, 1, 28),   # A: Margin
        (1, 2, 275),  # B: Phân loại / Chỉ số
        (2, 3, 175),  # C: Ký hiệu / Phân nhóm
        (3, 4, 125),  # D: Số lượng
        (4, 5, 120),  # E: Tỷ lệ (%)
        (5, 6, 185),  # F: Tiêu chí / Công thức
        (6, 7, 460),  # G: Nhận xét Data Analyst
    ]
    for start_c, end_c, width in col_widths:
        requests_list.append({
            "updateDimensionProperties": {
                "range": {
                    "sheetId": sheet_id,
                    "dimension": "COLUMNS",
                    "startIndex": start_c,
                    "endIndex": end_c
                },
                "properties": {"pixelSize": width},
                "fields": "pixelSize"
            }
        })

    # 3. Set Row Heights
    row_heights = [
        (0, 1, 15),   # R1: Padding
        (1, 2, 44),   # R2: Title
        (2, 3, 28),   # R3: Subtitle
        (3, 4, 32),   # R4: Scope note
        (4, 5, 16),   # R5: Spacing
        (5, 6, 26),   # R6: Card label
        (6, 7, 38),   # R7: Card value
        (7, 8, 24),   # R8: Card sub
        (8, 9, 18),   # R9: Spacing
        (9, 10, 32),  # R10: Sec 1 Header
        (10, 11, 28), # R11: Table 1 Header
        (11, 12, 26), # R12: VB Đúng
        (12, 13, 26), # R13: VB Sai
        (13, 14, 24), # R14: Chỉ Dư
        (14, 15, 24), # R15: Chỉ Thiếu
        (15, 16, 24), # R16: Vừa Dư vừa Thiếu
        (16, 17, 28), # R17: Tổng cộng
        (17, 18, 24), # R18: Tần suất Dư
        (18, 19, 24), # R19: Tần suất Thiếu
        (19, 20, 18), # R20: Spacing
        (20, 21, 32), # R21: Sec 2 Header
        (21, 22, 28), # R22: Table 2 Header
        (22, 23, 26), # R23: Khớp TP
        (23, 24, 26), # R24: Dư FP
        (24, 25, 26), # R25: Thiếu FN
        (25, 26, 28), # R26: Tổng Nơi nhận 2
        (26, 27, 28), # R27: Tổng Đích
        (27, 28, 24), # R28: Ngoại lệ
        (28, 29, 18), # R29: Spacing
        (29, 30, 32), # R30: Sec 3 Header
        (30, 31, 28), # R31: Table 3 Header
        (31, 32, 26), # R32: Precision
        (32, 33, 26), # R33: Recall
        (33, 34, 28), # R34: F1-Score
        (34, 35, 26), # R35: Jaccard
        (35, 36, 26), # R36: Doc Accuracy
        (36, 37, 18), # R37: Spacing
        (37, 38, 32), # R38: Sec 4 Header
        (38, 39, 62), # R39: Note 1
        (39, 40, 85), # R40: Note 2
        (40, 41, 85), # R41: Note 3
    ]
    for start_r, end_r, height in row_heights:
        requests_list.append({
            "updateDimensionProperties": {
                "range": {
                    "sheetId": sheet_id,
                    "dimension": "ROWS",
                    "startIndex": start_r,
                    "endIndex": end_r
                },
                "properties": {"pixelSize": height},
                "fields": "pixelSize"
            }
        })

    # 4. Merges
    merges = [
        (1, 2, 1, 7),   # R2: B2:G2 (Title)
        (2, 3, 1, 7),   # R3: B3:G3 (Subtitle)
        (3, 4, 1, 7),   # R4: B4:G4 (Scope)
        (9, 10, 1, 7),  # R10: B10:G10 (Sec 1)
        (20, 21, 1, 7), # R21: B21:G21 (Sec 2)
        (29, 30, 1, 7), # R30: B30:G30 (Sec 3)
        (37, 38, 1, 7), # R38: B38:G38 (Sec 4)
        (38, 39, 2, 7), # R39: C39:G39 (Note 1 text)
        (39, 40, 2, 7), # R40: C40:G40 (Note 2 text)
        (40, 41, 2, 7), # R41: C41:G41 (Note 3 text)
    ]
    for sr, er, sc, ec in merges:
        requests_list.append({
            "mergeCells": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": sr,
                    "endRowIndex": er,
                    "startColumnIndex": sc,
                    "endColumnIndex": ec
                },
                "mergeType": "MERGE_ALL"
            }
        })

    # 5. Base Font & Alignment for entire grid (B2:G41)
    requests_list.append({
        "repeatCell": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": 1,
                "endRowIndex": 41,
                "startColumnIndex": 1,
                "endColumnIndex": 7
            },
            "cell": {
                "userEnteredFormat": {
                    "textFormat": {
                        "fontFamily": "Segoe UI",
                        "fontSize": 10,
                        "foregroundColor": hex_to_rgb("#2D3748")
                    },
                    "verticalAlignment": "MIDDLE",
                    "wrapStrategy": "WRAP"
                }
            },
            "fields": "userEnteredFormat.textFormat.fontFamily,userEnteredFormat.textFormat.fontSize,userEnteredFormat.verticalAlignment,userEnteredFormat.wrapStrategy"
        }
    })

    # 6. Specific Header Styles
    # Title (R2: B2:G2)
    requests_list.append({
        "repeatCell": {
            "range": {"sheetId": sheet_id, "startRowIndex": 1, "endRowIndex": 2, "startColumnIndex": 1, "endColumnIndex": 7},
            "cell": {
                "userEnteredFormat": {
                    "backgroundColor": hex_to_rgb("#1A365D"),
                    "textFormat": {
                        "fontFamily": "Segoe UI",
                        "fontSize": 15,
                        "bold": True,
                        "foregroundColor": hex_to_rgb("#FFFFFF")
                    },
                    "horizontalAlignment": "CENTER",
                    "verticalAlignment": "MIDDLE"
                }
            },
            "fields": "userEnteredFormat.backgroundColor,userEnteredFormat.textFormat,userEnteredFormat.horizontalAlignment,userEnteredFormat.verticalAlignment"
        }
    })

    # Subtitle (R3: B3:G3)
    requests_list.append({
        "repeatCell": {
            "range": {"sheetId": sheet_id, "startRowIndex": 2, "endRowIndex": 3, "startColumnIndex": 1, "endColumnIndex": 7},
            "cell": {
                "userEnteredFormat": {
                    "backgroundColor": hex_to_rgb("#2B6CB0"),
                    "textFormat": {
                        "fontFamily": "Segoe UI",
                        "fontSize": 10,
                        "italic": True,
                        "foregroundColor": hex_to_rgb("#E2E8F0")
                    },
                    "horizontalAlignment": "CENTER",
                    "verticalAlignment": "MIDDLE"
                }
            },
            "fields": "userEnteredFormat.backgroundColor,userEnteredFormat.textFormat,userEnteredFormat.horizontalAlignment,userEnteredFormat.verticalAlignment"
        }
    })

    # Scope Note (R4: B4:G4)
    requests_list.append({
        "repeatCell": {
            "range": {"sheetId": sheet_id, "startRowIndex": 3, "endRowIndex": 4, "startColumnIndex": 1, "endColumnIndex": 7},
            "cell": {
                "userEnteredFormat": {
                    "backgroundColor": hex_to_rgb("#EDF2F7"),
                    "textFormat": {
                        "fontFamily": "Segoe UI",
                        "fontSize": 9,
                        "italic": True,
                        "foregroundColor": hex_to_rgb("#2D3748")
                    },
                    "horizontalAlignment": "LEFT",
                    "verticalAlignment": "MIDDLE",
                    "wrapStrategy": "WRAP"
                }
            },
            "fields": "userEnteredFormat.backgroundColor,userEnteredFormat.textFormat,userEnteredFormat.horizontalAlignment,userEnteredFormat.verticalAlignment,userEnteredFormat.wrapStrategy"
        }
    })

    # Section Headers (R10, R21, R30, R38)
    for r_idx, title_bg in [(9, "#2B6CB0"), (20, "#2B6CB0"), (29, "#1A365D"), (37, "#2D3748")]:
        requests_list.append({
            "repeatCell": {
                "range": {"sheetId": sheet_id, "startRowIndex": r_idx, "endRowIndex": r_idx + 1, "startColumnIndex": 1, "endColumnIndex": 7},
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": hex_to_rgb(title_bg),
                        "textFormat": {
                            "fontFamily": "Segoe UI",
                            "fontSize": 11,
                            "bold": True,
                            "foregroundColor": hex_to_rgb("#FFFFFF")
                        },
                        "horizontalAlignment": "LEFT",
                        "verticalAlignment": "MIDDLE"
                    }
                },
                "fields": "userEnteredFormat.backgroundColor,userEnteredFormat.textFormat,userEnteredFormat.horizontalAlignment,userEnteredFormat.verticalAlignment"
            }
        })

    # Table Column Headers (R11, R22, R31)
    for r_idx in [10, 21, 30]:
        requests_list.append({
            "repeatCell": {
                "range": {"sheetId": sheet_id, "startRowIndex": r_idx, "endRowIndex": r_idx + 1, "startColumnIndex": 1, "endColumnIndex": 7},
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": hex_to_rgb("#E2E8F0"),
                        "textFormat": {
                            "fontFamily": "Segoe UI",
                            "fontSize": 10,
                            "bold": True,
                            "foregroundColor": hex_to_rgb("#1A202C")
                        },
                        "horizontalAlignment": "CENTER",
                        "verticalAlignment": "MIDDLE"
                    }
                },
                "fields": "userEnteredFormat.backgroundColor,userEnteredFormat.textFormat,userEnteredFormat.horizontalAlignment,userEnteredFormat.verticalAlignment"
            }
        })

    # 7. KPI Summary Cards (Cols B to G, Rows 6 to 8: indices 5 to 8)
    cards_config = [
        (1, "#F7FAFC", "#1A365D", "#4A5568", "#CBD5E0", "NUMBER"),   # Card 1: Total
        (2, "#E6F4EA", "#137333", "#137333", "#A8DAB5", "NUMBER"),   # Card 2: Đúng
        (3, "#FCE8E6", "#C5221F", "#C5221F", "#F5C2C7", "NUMBER"),   # Card 3: Sai
        (4, "#EBF8FF", "#2B6CB0", "#1A365D", "#BEE3F8", "PERCENT"),  # Card 4: Precision
        (5, "#EBF8FF", "#2B6CB0", "#1A365D", "#BEE3F8", "PERCENT"),  # Card 5: Recall
        (6, "#FAF5FF", "#6B46C1", "#553C9A", "#E9D8FD", "PERCENT"),  # Card 6: F1-Score
    ]

    for col_idx, bg_hex, val_color_hex, label_color_hex, border_hex, num_type in cards_config:
        # Card Background & Borders
        requests_list.append({
            "updateBorders": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 5,
                    "endRowIndex": 8,
                    "startColumnIndex": col_idx,
                    "endColumnIndex": col_idx + 1
                },
                "top": {"style": "SOLID", "color": hex_to_rgb(border_hex)},
                "bottom": {"style": "SOLID", "color": hex_to_rgb(border_hex)},
                "left": {"style": "SOLID", "color": hex_to_rgb(border_hex)},
                "right": {"style": "SOLID", "color": hex_to_rgb(border_hex)},
            }
        })
        # Card Label (Row 6, index 5)
        requests_list.append({
            "repeatCell": {
                "range": {"sheetId": sheet_id, "startRowIndex": 5, "endRowIndex": 6, "startColumnIndex": col_idx, "endColumnIndex": col_idx + 1},
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": hex_to_rgb(bg_hex),
                        "textFormat": {
                            "fontFamily": "Segoe UI",
                            "fontSize": 9,
                            "bold": True,
                            "foregroundColor": hex_to_rgb(label_color_hex)
                        },
                        "horizontalAlignment": "CENTER",
                        "verticalAlignment": "BOTTOM"
                    }
                },
                "fields": "userEnteredFormat.backgroundColor,userEnteredFormat.textFormat,userEnteredFormat.horizontalAlignment,userEnteredFormat.verticalAlignment"
            }
        })
        # Card Value (Row 7, index 6)
        num_fmt = {"type": "PERCENT", "pattern": "0.00%"} if num_type == "PERCENT" else {"type": "NUMBER", "pattern": "#,##0"}
        requests_list.append({
            "repeatCell": {
                "range": {"sheetId": sheet_id, "startRowIndex": 6, "endRowIndex": 7, "startColumnIndex": col_idx, "endColumnIndex": col_idx + 1},
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": hex_to_rgb(bg_hex),
                        "textFormat": {
                            "fontFamily": "Segoe UI",
                            "fontSize": 19,
                            "bold": True,
                            "foregroundColor": hex_to_rgb(val_color_hex)
                        },
                        "horizontalAlignment": "CENTER",
                        "verticalAlignment": "MIDDLE",
                        "numberFormat": num_fmt
                    }
                },
                "fields": "userEnteredFormat.backgroundColor,userEnteredFormat.textFormat,userEnteredFormat.horizontalAlignment,userEnteredFormat.verticalAlignment,userEnteredFormat.numberFormat"
            }
        })
        # Card Subtitle (Row 8, index 7)
        requests_list.append({
            "repeatCell": {
                "range": {"sheetId": sheet_id, "startRowIndex": 7, "endRowIndex": 8, "startColumnIndex": col_idx, "endColumnIndex": col_idx + 1},
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": hex_to_rgb(bg_hex),
                        "textFormat": {
                            "fontFamily": "Segoe UI",
                            "fontSize": 9,
                            "italic": True,
                            "foregroundColor": hex_to_rgb(label_color_hex)
                        },
                        "horizontalAlignment": "CENTER",
                        "verticalAlignment": "TOP"
                    }
                },
                "fields": "userEnteredFormat.backgroundColor,userEnteredFormat.textFormat,userEnteredFormat.horizontalAlignment,userEnteredFormat.verticalAlignment"
            }
        })

    # 8. Alignments & Column Styles for Table Data
    # Col B: Left
    # Col C: Center
    # Col D: Center
    # Col E: Center
    # Col F: Center (Tables 1-3)
    # Col G: Left (Wrap)

    # Format numbers in Col D (Counts)
    requests_list.append({
        "repeatCell": {
            "range": {"sheetId": sheet_id, "startRowIndex": 10, "endRowIndex": 36, "startColumnIndex": 3, "endColumnIndex": 4},
            "cell": {
                "userEnteredFormat": {
                    "horizontalAlignment": "CENTER",
                    "numberFormat": {"type": "NUMBER", "pattern": "#,##0"}
                }
            },
            "fields": "userEnteredFormat.horizontalAlignment,userEnteredFormat.numberFormat"
        }
    })

    # Format percents in Col E (R12 to R27)
    requests_list.append({
        "repeatCell": {
            "range": {"sheetId": sheet_id, "startRowIndex": 11, "endRowIndex": 27, "startColumnIndex": 4, "endColumnIndex": 5},
            "cell": {
                "userEnteredFormat": {
                    "horizontalAlignment": "CENTER",
                    "numberFormat": {"type": "PERCENT", "pattern": "0.00%"}
                }
            },
            "fields": "userEnteredFormat.horizontalAlignment,userEnteredFormat.numberFormat"
        }
    })

    # Format percents in Table 3 Col D (R32 to R36: indices 31 to 36)
    requests_list.append({
        "repeatCell": {
            "range": {"sheetId": sheet_id, "startRowIndex": 31, "endRowIndex": 36, "startColumnIndex": 3, "endColumnIndex": 4},
            "cell": {
                "userEnteredFormat": {
                    "horizontalAlignment": "CENTER",
                    "textFormat": {"bold": True, "fontSize": 11},
                    "numberFormat": {"type": "PERCENT", "pattern": "0.00%"}
                }
            },
            "fields": "userEnteredFormat.horizontalAlignment,userEnteredFormat.textFormat.bold,userEnteredFormat.textFormat.fontSize,userEnteredFormat.numberFormat"
        }
    })

    # Format center alignments for Col C and Col F
    requests_list.append({
        "repeatCell": {
            "range": {"sheetId": sheet_id, "startRowIndex": 11, "endRowIndex": 36, "startColumnIndex": 2, "endColumnIndex": 3},
            "cell": {"userEnteredFormat": {"horizontalAlignment": "CENTER"}},
            "fields": "userEnteredFormat.horizontalAlignment"
        }
    })
    requests_list.append({
        "repeatCell": {
            "range": {"sheetId": sheet_id, "startRowIndex": 11, "endRowIndex": 36, "startColumnIndex": 5, "endColumnIndex": 6},
            "cell": {"userEnteredFormat": {"horizontalAlignment": "CENTER"}},
            "fields": "userEnteredFormat.horizontalAlignment"
        }
    })

    # 9. Row Highlights
    # Table 1:
    # R12: VB Đúng -> Light Green
    requests_list.append({
        "repeatCell": {
            "range": {"sheetId": sheet_id, "startRowIndex": 11, "endRowIndex": 12, "startColumnIndex": 1, "endColumnIndex": 7},
            "cell": {
                "userEnteredFormat": {
                    "backgroundColor": hex_to_rgb("#F0FFF4"),
                    "textFormat": {"foregroundColor": hex_to_rgb("#22543D")}
                }
            },
            "fields": "userEnteredFormat.backgroundColor,userEnteredFormat.textFormat.foregroundColor"
        }
    })
    # R12: Bold B12, D12, E12
    requests_list.append({
        "repeatCell": {
            "range": {"sheetId": sheet_id, "startRowIndex": 11, "endRowIndex": 12, "startColumnIndex": 1, "endColumnIndex": 5},
            "cell": {"userEnteredFormat": {"textFormat": {"bold": True}}},
            "fields": "userEnteredFormat.textFormat.bold"
        }
    })

    # R13: VB Sai (Tổng) -> Light Red, Bold
    requests_list.append({
        "repeatCell": {
            "range": {"sheetId": sheet_id, "startRowIndex": 12, "endRowIndex": 13, "startColumnIndex": 1, "endColumnIndex": 7},
            "cell": {
                "userEnteredFormat": {
                    "backgroundColor": hex_to_rgb("#FFF5F5"),
                    "textFormat": {"foregroundColor": hex_to_rgb("#742A2A"), "bold": True}
                }
            },
            "fields": "userEnteredFormat.backgroundColor,userEnteredFormat.textFormat"
        }
    })

    # R17: Tổng cộng tập mẫu -> Soft Gray, Bold All, Double Bottom Border
    requests_list.append({
        "repeatCell": {
            "range": {"sheetId": sheet_id, "startRowIndex": 16, "endRowIndex": 17, "startColumnIndex": 1, "endColumnIndex": 7},
            "cell": {
                "userEnteredFormat": {
                    "backgroundColor": hex_to_rgb("#EDF2F7"),
                    "textFormat": {"bold": True, "foregroundColor": hex_to_rgb("#1A202C")}
                }
            },
            "fields": "userEnteredFormat.backgroundColor,userEnteredFormat.textFormat"
        }
    })

    # R18 & R19: Insights -> Soft Gray, Italic
    requests_list.append({
        "repeatCell": {
            "range": {"sheetId": sheet_id, "startRowIndex": 17, "endRowIndex": 19, "startColumnIndex": 1, "endColumnIndex": 7},
            "cell": {
                "userEnteredFormat": {
                    "backgroundColor": hex_to_rgb("#F7FAFC"),
                    "textFormat": {"italic": True, "foregroundColor": hex_to_rgb("#4A5568")}
                }
            },
            "fields": "userEnteredFormat.backgroundColor,userEnteredFormat.textFormat"
        }
    })

    # Table 2:
    # R23: TP Khớp -> Light Green
    requests_list.append({
        "repeatCell": {
            "range": {"sheetId": sheet_id, "startRowIndex": 22, "endRowIndex": 23, "startColumnIndex": 1, "endColumnIndex": 7},
            "cell": {
                "userEnteredFormat": {
                    "backgroundColor": hex_to_rgb("#F0FFF4"),
                    "textFormat": {"bold": True, "foregroundColor": hex_to_rgb("#22543D")}
                }
            },
            "fields": "userEnteredFormat.backgroundColor,userEnteredFormat.textFormat"
        }
    })
    # R24: FP Dư -> Light Amber
    requests_list.append({
        "repeatCell": {
            "range": {"sheetId": sheet_id, "startRowIndex": 23, "endRowIndex": 24, "startColumnIndex": 1, "endColumnIndex": 7},
            "cell": {
                "userEnteredFormat": {
                    "backgroundColor": hex_to_rgb("#FEFCBF"),
                    "textFormat": {"foregroundColor": hex_to_rgb("#744210")}
                }
            },
            "fields": "userEnteredFormat.backgroundColor,userEnteredFormat.textFormat.foregroundColor"
        }
    })
    # R25: FN Thiếu -> Light Red
    requests_list.append({
        "repeatCell": {
            "range": {"sheetId": sheet_id, "startRowIndex": 24, "endRowIndex": 25, "startColumnIndex": 1, "endColumnIndex": 7},
            "cell": {
                "userEnteredFormat": {
                    "backgroundColor": hex_to_rgb("#FFF5F5"),
                    "textFormat": {"foregroundColor": hex_to_rgb("#C53030")}
                }
            },
            "fields": "userEnteredFormat.backgroundColor,userEnteredFormat.textFormat.foregroundColor"
        }
    })
    # R26 & R27: Totals -> Soft Gray, Bold
    requests_list.append({
        "repeatCell": {
            "range": {"sheetId": sheet_id, "startRowIndex": 25, "endRowIndex": 27, "startColumnIndex": 1, "endColumnIndex": 7},
            "cell": {
                "userEnteredFormat": {
                    "backgroundColor": hex_to_rgb("#EDF2F7"),
                    "textFormat": {"bold": True, "foregroundColor": hex_to_rgb("#1A202C")}
                }
            },
            "fields": "userEnteredFormat.backgroundColor,userEnteredFormat.textFormat"
        }
    })
    # R28: Ngoại lệ -> Italic Gray
    requests_list.append({
        "repeatCell": {
            "range": {"sheetId": sheet_id, "startRowIndex": 27, "endRowIndex": 28, "startColumnIndex": 1, "endColumnIndex": 7},
            "cell": {
                "userEnteredFormat": {
                    "backgroundColor": hex_to_rgb("#F7FAFC"),
                    "textFormat": {"italic": True, "foregroundColor": hex_to_rgb("#718096")}
                }
            },
            "fields": "userEnteredFormat.backgroundColor,userEnteredFormat.textFormat"
        }
    })

    # Table 3:
    # R34: F1-Score Highlight
    requests_list.append({
        "repeatCell": {
            "range": {"sheetId": sheet_id, "startRowIndex": 33, "endRowIndex": 34, "startColumnIndex": 1, "endColumnIndex": 7},
            "cell": {
                "userEnteredFormat": {
                    "backgroundColor": hex_to_rgb("#FAF5FF"),
                    "textFormat": {"bold": True, "foregroundColor": hex_to_rgb("#6B46C1")}
                }
            },
            "fields": "userEnteredFormat.backgroundColor,userEnteredFormat.textFormat"
        }
    })

    # Section 4 Notes (R39 to R41)
    requests_list.append({
        "repeatCell": {
            "range": {"sheetId": sheet_id, "startRowIndex": 38, "endRowIndex": 41, "startColumnIndex": 1, "endColumnIndex": 2},
            "cell": {
                "userEnteredFormat": {
                    "backgroundColor": hex_to_rgb("#EDF2F7"),
                    "textFormat": {"bold": True, "foregroundColor": hex_to_rgb("#1A202C")},
                    "verticalAlignment": "TOP"
                }
            },
            "fields": "userEnteredFormat.backgroundColor,userEnteredFormat.textFormat,userEnteredFormat.verticalAlignment"
        }
    })
    requests_list.append({
        "repeatCell": {
            "range": {"sheetId": sheet_id, "startRowIndex": 38, "endRowIndex": 41, "startColumnIndex": 2, "endColumnIndex": 7},
            "cell": {
                "userEnteredFormat": {
                    "backgroundColor": hex_to_rgb("#F7FAFC"),
                    "textFormat": {"foregroundColor": hex_to_rgb("#2D3748"), "fontSize": 9},
                    "verticalAlignment": "TOP",
                    "wrapStrategy": "WRAP"
                }
            },
            "fields": "userEnteredFormat.backgroundColor,userEnteredFormat.textFormat,userEnteredFormat.verticalAlignment,userEnteredFormat.wrapStrategy"
        }
    })

    # 10. Table Borders
    # Table 1 Borders (R11 to R19: indices 10 to 19, cols 1 to 7)
    requests_list.append({
        "updateBorders": {
            "range": {"sheetId": sheet_id, "startRowIndex": 10, "endRowIndex": 19, "startColumnIndex": 1, "endColumnIndex": 7},
            "top": {"style": "SOLID_MEDIUM", "color": hex_to_rgb("#4A5568")},
            "bottom": {"style": "SOLID_MEDIUM", "color": hex_to_rgb("#4A5568")},
            "left": {"style": "SOLID_MEDIUM", "color": hex_to_rgb("#4A5568")},
            "right": {"style": "SOLID_MEDIUM", "color": hex_to_rgb("#4A5568")},
            "innerHorizontal": {"style": "SOLID", "color": hex_to_rgb("#E2E8F0")},
            "innerVertical": {"style": "SOLID", "color": hex_to_rgb("#E2E8F0")}
        }
    })
    # Table 1 Total Row Double Bottom Border (R17, index 16)
    requests_list.append({
        "updateBorders": {
            "range": {"sheetId": sheet_id, "startRowIndex": 16, "endRowIndex": 17, "startColumnIndex": 1, "endColumnIndex": 7},
            "top": {"style": "SOLID_MEDIUM", "color": hex_to_rgb("#718096")},
            "bottom": {"style": "DOUBLE", "color": hex_to_rgb("#1A202C")},
        }
    })

    # Table 2 Borders (R22 to R28: indices 21 to 28, cols 1 to 7)
    requests_list.append({
        "updateBorders": {
            "range": {"sheetId": sheet_id, "startRowIndex": 21, "endRowIndex": 28, "startColumnIndex": 1, "endColumnIndex": 7},
            "top": {"style": "SOLID_MEDIUM", "color": hex_to_rgb("#4A5568")},
            "bottom": {"style": "SOLID_MEDIUM", "color": hex_to_rgb("#4A5568")},
            "left": {"style": "SOLID_MEDIUM", "color": hex_to_rgb("#4A5568")},
            "right": {"style": "SOLID_MEDIUM", "color": hex_to_rgb("#4A5568")},
            "innerHorizontal": {"style": "SOLID", "color": hex_to_rgb("#E2E8F0")},
            "innerVertical": {"style": "SOLID", "color": hex_to_rgb("#E2E8F0")}
        }
    })

    # Table 3 Borders (R31 to R36: indices 30 to 36, cols 1 to 7)
    requests_list.append({
        "updateBorders": {
            "range": {"sheetId": sheet_id, "startRowIndex": 30, "endRowIndex": 36, "startColumnIndex": 1, "endColumnIndex": 7},
            "top": {"style": "SOLID_MEDIUM", "color": hex_to_rgb("#4A5568")},
            "bottom": {"style": "SOLID_MEDIUM", "color": hex_to_rgb("#4A5568")},
            "left": {"style": "SOLID_MEDIUM", "color": hex_to_rgb("#4A5568")},
            "right": {"style": "SOLID_MEDIUM", "color": hex_to_rgb("#4A5568")},
            "innerHorizontal": {"style": "SOLID", "color": hex_to_rgb("#E2E8F0")},
            "innerVertical": {"style": "SOLID", "color": hex_to_rgb("#E2E8F0")}
        }
    })

    # Section 4 Notes Borders (R39 to R41: indices 38 to 41, cols 1 to 7)
    requests_list.append({
        "updateBorders": {
            "range": {"sheetId": sheet_id, "startRowIndex": 38, "endRowIndex": 41, "startColumnIndex": 1, "endColumnIndex": 7},
            "top": {"style": "SOLID_MEDIUM", "color": hex_to_rgb("#4A5568")},
            "bottom": {"style": "SOLID_MEDIUM", "color": hex_to_rgb("#4A5568")},
            "left": {"style": "SOLID_MEDIUM", "color": hex_to_rgb("#4A5568")},
            "right": {"style": "SOLID_MEDIUM", "color": hex_to_rgb("#4A5568")},
            "innerHorizontal": {"style": "SOLID", "color": hex_to_rgb("#E2E8F0")},
            "innerVertical": {"style": "SOLID", "color": hex_to_rgb("#E2E8F0")}
        }
    })

    print(f"Sending batchUpdate with {len(requests_list)} formatting requests...")
    batch_url = f"https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}:batchUpdate"
    resp = requests.post(batch_url, headers=headers, json={"requests": requests_list})
    assert resp.status_code == 200, f"batchUpdate failed: {resp.text}"
    print("Formatting applied successfully!")

if __name__ == "__main__":
    format_dashboard()
