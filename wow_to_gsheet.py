"""
Lấy dữ liệu lịch sử VN-Midcap (VNMID) và VN-Smallcap (VNSML) từ vnstock,
tính % thay đổi WoW (chỉ số + KLGD TB tuần), rồi ghi kết quả vào Google Sheets.

Cách dùng (local hoặc GitHub Actions):
    python wow_to_gsheet.py

Yêu cầu thư viện:
    pip install vnstock pandas gspread google-auth

Yêu cầu biến môi trường (set trong GitHub Secrets hoặc export local):
    GOOGLE_CREDENTIALS_JSON : toàn bộ nội dung file service-account JSON (dạng string)
    SHEET_ID                : ID của Google Sheet (lấy từ URL của sheet)
    SHEET_TAB_NAME          : (tuỳ chọn) tên tab/worksheet, mặc định "WoW"
"""

import os
import json
from datetime import date, timedelta

import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from vnstock.api.quote import Quote

# ----------------------------
# CẤU HÌNH
# ----------------------------
INDEX_CODES = {
    "VN-Midcap": "VNMID",
    "VN-Smallcap": "VNSML",
}
SOURCE = "VCI"
LOOKBACK_WEEKS = 4
SHEET_TAB_NAME = os.environ.get("SHEET_TAB_NAME", "WoW")


def get_history(symbol: str, weeks: int = LOOKBACK_WEEKS) -> pd.DataFrame:
    end = date.today()
    start = end - timedelta(weeks=weeks + 1)

    q = Quote(symbol=symbol, source=SOURCE)
    df = q.history(start=start.isoformat(), end=end.isoformat(), interval="1D")

    if df is None or df.empty:
        raise ValueError(f"Không lấy được dữ liệu cho mã {symbol}")

    time_col = "time" if "time" in df.columns else df.columns[0]
    df[time_col] = pd.to_datetime(df[time_col])
    df = df.sort_values(time_col).reset_index(drop=True)
    df["week"] = df[time_col].dt.to_period("W-FRI")
    return df


def calc_wow(df: pd.DataFrame) -> dict:
    weekly = df.groupby("week").agg(
        close_last=("close", "last"),
        volume_avg=("volume", "mean"),
    ).reset_index()

    if len(weekly) < 2:
        raise ValueError("Không đủ dữ liệu 2 tuần để so sánh WoW")

    this_week = weekly.iloc[-1]
    last_week = weekly.iloc[-2]

    index_change_pct = (this_week["close_last"] / last_week["close_last"] - 1) * 100
    volume_change_pct = (this_week["volume_avg"] / last_week["volume_avg"] - 1) * 100

    return {
        "Tuần": str(this_week["week"]),
        "Chỉ số cuối tuần": round(this_week["close_last"], 2),
        "% Chỉ số WoW": round(index_change_pct, 2),
        "KLGD TB tuần": int(this_week["volume_avg"]),
        "% KLGD TB tuần WoW": round(volume_change_pct, 2),
        "Cập nhật lúc": pd.Timestamp.now(tz="Asia/Ho_Chi_Minh").strftime("%Y-%m-%d %H:%M"),
    }


def get_all_results() -> pd.DataFrame:
    rows = []
    for label, code in INDEX_CODES.items():
        print(f"Đang lấy dữ liệu {label} ({code})...")
        df = get_history(code)
        stats = calc_wow(df)
        stats_row = {"Chỉ số": label, **stats}
        rows.append(stats_row)
    return pd.DataFrame(rows)


def write_to_gsheet(df: pd.DataFrame):
    creds_json = os.environ["GOOGLE_CREDENTIALS_JSON"]
    sheet_id = os.environ["SHEET_ID"]

    creds_dict = json.loads(creds_json)
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)

    sh = client.open_by_key(sheet_id)
    try:
        ws = sh.worksheet(SHEET_TAB_NAME)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=SHEET_TAB_NAME, rows=100, cols=20)

    ws.clear()
    ws.update([df.columns.values.tolist()] + df.values.tolist())
    print(f"Đã ghi {len(df)} dòng vào tab '{SHEET_TAB_NAME}' của Google Sheet.")


def main():
    df = get_all_results()
    print(df)
    write_to_gsheet(df)


if __name__ == "__main__":
    main()
