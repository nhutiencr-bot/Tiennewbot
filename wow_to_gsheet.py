"""
Lấy dữ liệu lịch sử VN-Midcap (VNMID) và VN-Smallcap (VNSML) từ vnstock,
tính % thay đổi WoW (chỉ số + tổng KLGD cả tuần), rồi ghi kết quả vào Google Sheets.

Cách dùng (local hoặc GitHub Actions):
    python wow_to_gsheet.py

Yêu cầu thư viện:
    pip install vnstock pandas gspread google-auth

Yêu cầu biến môi trường (set trong GitHub Secrets hoặc export local):
    GOOGLE_CREDENTIALS_JSON : toàn bộ nội dung file service-account JSON (dạng string)
    SHEET_ID                : ID của Google Sheet (lấy từ URL của sheet)
    SHEET_TAB_NAME          : (tuỳ chọn) tên tab/worksheet, mặc định "WoW"

Logic tuần:
    - Tuần được gộp theo "W-FRI" (tuần kết thúc vào thứ 6, đúng lịch giao dịch HOSE).
    - Script CHỈ so sánh các tuần đã HOÀN TẤT (đủ >=4 phiên), tự bỏ qua tuần đang
      chạy nửa chừng (ví dụ chạy vào thứ 2-4 đầu tuần) để tránh KLGD bị tính thiếu.
    - KLGD theo tuần = TỔNG (sum) khối lượng khớp lệnh của các phiên trong tuần,
      không phải trung bình/ngày — khớp với cách đọc số liệu trong bảng "KLGD TB tuần"
      gốc (ví dụ 584,114,880 là tổng cả tuần, không phải khối lượng 1 ngày).
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
# Thứ tự nguồn dữ liệu sẽ thử lần lượt — nếu nguồn đầu lỗi/không trả dữ liệu,
# tự động chuyển sang nguồn kế tiếp để không phụ thuộc vào 1 công ty chứng khoán duy nhất.
SOURCES = ["VCI", "TCBS", "KBS"]
LOOKBACK_WEEKS = 5  # lấy dư vài tuần để chắc luôn có >=2 tuần hoàn tất để so sánh
MIN_SESSIONS_FOR_COMPLETE_WEEK = 4  # tuần có từ 4 phiên trở lên mới coi là "đã hoàn tất"
SHEET_TAB_NAME = os.environ.get("SHEET_TAB_NAME", "WoW")


def get_history(symbol: str, weeks: int = LOOKBACK_WEEKS) -> pd.DataFrame:
    """Lấy dữ liệu lịch sử, tự động thử lần lượt các nguồn trong SOURCES."""
    end = date.today()
    start = end - timedelta(weeks=weeks + 1)

    last_error = None
    for source in SOURCES:
        try:
            q = Quote(symbol=symbol, source=source)
            df = q.history(start=start.isoformat(), end=end.isoformat(), interval="1D")
            if df is not None and not df.empty:
                print(f"  -> Lấy thành công từ nguồn: {source}")
                time_col = "time" if "time" in df.columns else df.columns[0]
                df[time_col] = pd.to_datetime(df[time_col])
                df = df.sort_values(time_col).reset_index(drop=True)
                df["week"] = df[time_col].dt.to_period("W-FRI")
                return df
        except Exception as e:
            last_error = e
            print(f"  -> Nguồn {source} lỗi ({e}), thử nguồn kế tiếp...")
            continue

    raise ValueError(f"Không lấy được dữ liệu cho mã {symbol} từ bất kỳ nguồn nào. Lỗi cuối: {last_error}")


def calc_wow(df: pd.DataFrame) -> dict:
    weekly = df.groupby("week").agg(
        close_last=("close", "last"),
        volume_sum=("volume", "sum"),
        n_sessions=("close", "count"),
    ).reset_index()

    # Chỉ giữ các tuần đã hoàn tất (đủ số phiên), bỏ tuần đang chạy nửa chừng
    weekly_complete = weekly[weekly["n_sessions"] >= MIN_SESSIONS_FOR_COMPLETE_WEEK].reset_index(drop=True)

    if len(weekly_complete) < 2:
        raise ValueError("Không đủ 2 tuần đã hoàn tất để so sánh WoW")

    this_week = weekly_complete.iloc[-1]
    last_week = weekly_complete.iloc[-2]

    index_change_pct = (this_week["close_last"] / last_week["close_last"] - 1) * 100
    volume_change_pct = (this_week["volume_sum"] / last_week["volume_sum"] - 1) * 100

    return {
        "Tuần": str(this_week["week"]),
        "Chỉ số cuối tuần": round(this_week["close_last"], 2),
        "% Chỉ số WoW": round(index_change_pct, 2),
        "KLGD tuần (tổng)": int(this_week["volume_sum"]),
        "% KLGD tuần WoW": round(volume_change_pct, 2),
        "Tuần trước": str(last_week["week"]),
        "KLGD tuần trước (tổng)": int(last_week["volume_sum"]),
        "Cập nhật lúc": pd.Timestamp.now(tz="Asia/Ho_Chi_Minh").strftime("%Y-%m-%d %H:%M"),
    }


def get_all_results() -> pd.DataFrame:
    rows = []
    for label, code in INDEX_CODES.items():
        print(f"\n========== Đang lấy dữ liệu {label} ({code}) ==========")
        df = get_history(code)

        # In chi tiết dữ liệu thô từng ngày để đối chiếu với bản tin gốc
        print(f"Dữ liệu thô từng phiên ({label}):")
        time_col = "time" if "time" in df.columns else df.columns[0]
        print(df[[time_col, "close", "volume", "week"]].to_string(index=False))

        stats = calc_wow(df)
        print(f"Kết quả WoW tính được cho {label}:")
        for k, v in stats.items():
            print(f"  {k}: {v}")

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
    print("###### SCRIPT VERSION: v3-sum-fallback-2026-06-29 ######")
    df = get_all_results()
    print(df)
    write_to_gsheet(df)


if __name__ == "__main__":
    main()
