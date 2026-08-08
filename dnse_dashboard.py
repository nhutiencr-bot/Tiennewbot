"""
DNSE Account Dashboard - Streamlit
- Fix timeout: dùng httpx với retry + fallback
- Cache dữ liệu để load nhanh
- Tabs: Tiểu khoản | Vị thế | Số dư | Lịch sử lệnh | P&L | Bot điểm mua
- Font đẹp: Inter + Vietnamese friendly
"""

import streamlit as st
import httpx
import hmac
import hashlib
import time
import json
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
from typing import Optional
import asyncio

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="DNSE Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# CUSTOM CSS - Font đẹp + Dark financial theme
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

/* Global */
html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
}

/* Hide default streamlit header */
#MainMenu, footer, header {visibility: hidden;}

/* Main container */
.main .block-container {
    padding: 1.2rem 2rem 2rem 2rem;
    max-width: 1400px;
}

/* ── HEADER ── */
.dash-header {
    background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 100%);
    border-radius: 12px;
    padding: 1.2rem 1.8rem;
    margin-bottom: 1.4rem;
    display: flex;
    align-items: center;
    gap: 12px;
    border: 1px solid #1d4ed8;
}
.dash-header h1 {
    color: #f8fafc;
    font-size: 1.5rem;
    font-weight: 700;
    margin: 0;
    letter-spacing: -0.02em;
}
.dash-header .sub {
    color: #94a3b8;
    font-size: 0.82rem;
    margin-top: 2px;
}

/* ── METRIC CARDS ── */
.metric-row {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 12px;
    margin-bottom: 1.2rem;
}
.metric-card {
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 10px;
    padding: 1rem 1.2rem;
    transition: border-color 0.2s;
}
.metric-card:hover { border-color: #3b82f6; }
.metric-card .label {
    color: #64748b;
    font-size: 0.75rem;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
.metric-card .value {
    color: #f1f5f9;
    font-size: 1.3rem;
    font-weight: 700;
    margin-top: 4px;
    font-family: 'JetBrains Mono', monospace;
}
.metric-card .delta {
    font-size: 0.78rem;
    margin-top: 3px;
    font-weight: 500;
}
.metric-card .delta.pos { color: #22c55e; }
.metric-card .delta.neg { color: #ef4444; }
.metric-card .delta.neu { color: #94a3b8; }

/* ── SIGNAL BADGE ── */
.signal-buy {
    background: #14532d;
    color: #4ade80;
    border: 1px solid #166534;
    border-radius: 6px;
    padding: 2px 10px;
    font-size: 0.78rem;
    font-weight: 600;
}
.signal-sell {
    background: #450a0a;
    color: #f87171;
    border: 1px solid #7f1d1d;
    border-radius: 6px;
    padding: 2px 10px;
    font-size: 0.78rem;
    font-weight: 600;
}
.signal-hold {
    background: #1c1917;
    color: #a8a29e;
    border: 1px solid #44403c;
    border-radius: 6px;
    padding: 2px 10px;
    font-size: 0.78rem;
    font-weight: 600;
}

/* ── TABS ── */
.stTabs [data-baseweb="tab-list"] {
    gap: 4px;
    background: #0f172a;
    padding: 4px;
    border-radius: 8px;
}
.stTabs [data-baseweb="tab"] {
    color: #64748b !important;
    border-radius: 6px !important;
    padding: 6px 16px !important;
    font-weight: 500 !important;
    font-size: 0.85rem !important;
}
.stTabs [aria-selected="true"] {
    background: #1d4ed8 !important;
    color: white !important;
}

/* ── SIDEBAR ── */
[data-testid="stSidebar"] {
    background: #0f172a;
}
[data-testid="stSidebar"] .stTextInput input,
[data-testid="stSidebar"] .stSelectbox select {
    background: #1e293b !important;
    border-color: #334155 !important;
    color: #f1f5f9 !important;
    border-radius: 8px !important;
}

/* ── BUTTON ── */
.stButton > button {
    background: linear-gradient(90deg, #1d4ed8, #2563eb);
    color: white;
    border: none;
    border-radius: 8px;
    padding: 8px 20px;
    font-weight: 600;
    font-size: 0.85rem;
    transition: opacity 0.2s;
}
.stButton > button:hover { opacity: 0.85; }

/* ── TABLE ── */
.dataframe {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.82rem !important;
}

/* ── STATUS PILL ── */
.status-live {
    display: inline-block;
    width: 8px; height: 8px;
    background: #22c55e;
    border-radius: 50%;
    animation: pulse 1.5s infinite;
    margin-right: 6px;
}
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
}

/* ── BOT CARD ── */
.bot-card {
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 10px;
    padding: 1.2rem;
    margin-bottom: 0.8rem;
}
.bot-card h4 { color: #f1f5f9; margin: 0 0 8px 0; font-size: 1rem; }
.bot-card .ticker {
    font-family: 'JetBrains Mono', monospace;
    font-size: 1.1rem;
    font-weight: 700;
    color: #60a5fa;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# DNSE API CLIENT
# ─────────────────────────────────────────────
BASE_URL = "https://openapi.dnse.com.vn"
TIMEOUT = httpx.Timeout(15.0, connect=10.0)  # giảm timeout, fail nhanh hơn

def _sign(api_secret: str, method: str, path: str, body: str = "") -> dict:
    """Tạo HMAC-SHA256 signature cho DNSE OpenAPI."""
    ts = str(int(time.time() * 1000))
    payload = f"{method.upper()}\n{path}\n{ts}\n{body}"
    sig = hmac.new(
        api_secret.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return {"timestamp": ts, "signature": sig}


def _headers(api_key: str, api_secret: str, method: str, path: str, body: str = "") -> dict:
    signed = _sign(api_secret, method, path, body)
    return {
        "X-API-Key": api_key,
        "X-Timestamp": signed["timestamp"],
        "X-Signature": signed["signature"],
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _get(api_key: str, api_secret: str, path: str, params: dict = None) -> dict | list | None:
    """Sync GET với retry 2 lần và timeout ngắn."""
    url = BASE_URL + path
    headers = _headers(api_key, api_secret, "GET", path)
    for attempt in range(3):
        try:
            with httpx.Client(timeout=TIMEOUT, verify=True) as client:
                r = client.get(url, headers=headers, params=params)
                r.raise_for_status()
                return r.json()
        except httpx.TimeoutException:
            if attempt == 2:
                st.error(f"⏱️ Timeout sau 3 lần thử: `{path}`")
                return None
            time.sleep(1.5 * (attempt + 1))
        except httpx.HTTPStatusError as e:
            st.error(f"❌ HTTP {e.response.status_code}: {path}")
            return None
        except Exception as e:
            if attempt == 2:
                st.error(f"❌ Lỗi kết nối: {str(e)[:120]}")
                return None
            time.sleep(1)
    return None


# ─────────────────────────────────────────────
# CACHED API CALLS
# ─────────────────────────────────────────────
@st.cache_data(ttl=60, show_spinner=False)
def get_accounts(api_key: str, api_secret: str):
    data = _get(api_key, api_secret, "/accounts")
    if data is None:
        return []
    # API trả về {"accounts": [...]} hoặc list trực tiếp
    if isinstance(data, dict):
        return data.get("accounts", data.get("data", []))
    return data if isinstance(data, list) else []


@st.cache_data(ttl=30, show_spinner=False)
def get_positions(api_key: str, api_secret: str, account_no: str, market_type: str = "STOCK"):
    data = _get(api_key, api_secret, f"/accounts/{account_no}/positions", {"marketType": market_type})
    if data is None:
        return []
    if isinstance(data, dict):
        return data.get("positions", data.get("data", []))
    return data if isinstance(data, list) else []


@st.cache_data(ttl=30, show_spinner=False)
def get_balances(api_key: str, api_secret: str, account_no: str):
    data = _get(api_key, api_secret, f"/accounts/{account_no}/balances")
    return data if isinstance(data, dict) else {}


@st.cache_data(ttl=60, show_spinner=False)
def get_orders(api_key: str, api_secret: str, account_no: str, market_type: str = "STOCK", category: str = "NORMAL"):
    data = _get(
        api_key, api_secret,
        f"/accounts/{account_no}/orders",
        {"marketType": market_type, "orderCategory": category},
    )
    if data is None:
        return []
    if isinstance(data, dict):
        return data.get("orders", data.get("data", []))
    return data if isinstance(data, list) else []


@st.cache_data(ttl=300, show_spinner=False)
def get_order_history(api_key: str, api_secret: str, account_no: str, from_date: str, to_date: str):
    """Lịch sử lệnh theo ngày."""
    data = _get(
        api_key, api_secret,
        f"/accounts/{account_no}/order-history",
        {"marketType": "STOCK", "fromDate": from_date, "toDate": to_date},
    )
    if data is None:
        return []
    if isinstance(data, dict):
        return data.get("orders", data.get("data", []))
    return data if isinstance(data, list) else []


# ─────────────────────────────────────────────
# P&L CALCULATION
# ─────────────────────────────────────────────
def calc_pnl(positions: list) -> pd.DataFrame:
    rows = []
    for p in positions:
        symbol    = p.get("symbol", p.get("secSymbol", ""))
        qty       = float(p.get("qty", p.get("volume", 0)) or 0)
        avg_price = float(p.get("avgPrice", p.get("costPrice", 0)) or 0)
        cur_price = float(p.get("currentPrice", p.get("marketPrice", avg_price)) or avg_price)
        market_val = qty * cur_price
        cost_val   = qty * avg_price
        pnl_abs    = market_val - cost_val
        pnl_pct    = (pnl_abs / cost_val * 100) if cost_val else 0
        rows.append({
            "Mã CP": symbol,
            "Khối lượng": int(qty),
            "Giá vốn": avg_price,
            "Giá hiện tại": cur_price,
            "Giá trị TT": market_val,
            "P&L (VNĐ)": pnl_abs,
            "P&L (%)": pnl_pct,
        })
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows).sort_values("P&L (VNĐ)", ascending=False)
    return df


def fmt_vnd(x):
    if pd.isna(x): return "-"
    return f"{x:,.0f}"

def fmt_pct(x):
    if pd.isna(x): return "-"
    sign = "+" if x >= 0 else ""
    return f"{sign}{x:.2f}%"

def color_pnl(val):
    if isinstance(val, float):
        color = "#22c55e" if val >= 0 else "#ef4444"
        return f"color: {color}; font-weight: 600"
    return ""


# ─────────────────────────────────────────────
# BOT ĐIỂM MUA - Cô Tiên Logic (Kijun17/Knife65)
# ─────────────────────────────────────────────
def compute_signals(prices: list[float], volumes: list[float] = None) -> dict:
    """
    Tính tín hiệu mua/bán theo hệ thống Cô Tiên:
    - Kijun17 = EMA(17)
    - Knife65 = EMA(65)
    - Knife129 = EMA(129)
    - RSI14
    - Volume/MA20 ratio
    """
    if len(prices) < 20:
        return {"signal": "KHÔNG ĐỦ DỮ LIỆU", "score": 0, "details": []}

    arr = np.array(prices, dtype=float)

    def ema(data, period):
        k = 2 / (period + 1)
        result = [data[0]]
        for p in data[1:]:
            result.append(p * k + result[-1] * (1 - k))
        return np.array(result)

    def rsi(data, period=14):
        deltas = np.diff(data)
        gains  = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        avg_g  = np.convolve(gains,  np.ones(period)/period, 'valid')[0]
        avg_l  = np.convolve(losses, np.ones(period)/period, 'valid')[0]
        if avg_l == 0: return 100.0
        rs = avg_g / avg_l
        return 100 - 100 / (1 + rs)

    kijun17  = ema(arr, 17)[-1]
    knife65  = ema(arr, min(65, len(arr)))[-1]
    knife129 = ema(arr, min(129, len(arr)))[-1] if len(arr) >= 30 else knife65
    price    = arr[-1]
    rsi14    = rsi(arr[-30:]) if len(arr) >= 30 else 50.0

    vol_ratio = 1.0
    if volumes and len(volumes) >= 20:
        v_arr     = np.array(volumes[-20:], dtype=float)
        ma20_vol  = v_arr[:-1].mean()
        vol_ratio = v_arr[-1] / ma20_vol if ma20_vol else 1.0

    score  = 0
    details = []

    # Điều kiện 1: Giá > Kijun17
    if price > kijun17:
        score += 2
        details.append(("✅", f"Giá ({price:,.0f}) > Kijun17 ({kijun17:,.0f})"))
    else:
        score -= 1
        details.append(("⬇️", f"Giá ({price:,.0f}) < Kijun17 ({kijun17:,.0f})"))

    # Điều kiện 2: Kijun17 > Knife65
    if kijun17 > knife65:
        score += 2
        details.append(("✅", f"Kijun17 ({kijun17:,.0f}) > Knife65 ({knife65:,.0f})"))
    else:
        score -= 1
        details.append(("⬇️", f"Kijun17 ({kijun17:,.0f}) < Knife65 ({knife65:,.0f})"))

    # Điều kiện 3: Knife65 > Knife129
    if knife65 > knife129:
        score += 1
        details.append(("✅", f"Knife65 ({knife65:,.0f}) > Knife129 ({knife129:,.0f})"))
    else:
        details.append(("⚠️", f"Knife65 ({knife65:,.0f}) < Knife129 ({knife129:,.0f})"))

    # Điều kiện 4: RSI14
    if 40 <= rsi14 <= 70:
        score += 1
        details.append(("✅", f"RSI14 = {rsi14:.1f} (vùng lý tưởng 40–70)"))
    elif rsi14 > 75:
        score -= 2
        details.append(("❌", f"RSI14 = {rsi14:.1f} (vùng quá mua)"))
    else:
        details.append(("⚠️", f"RSI14 = {rsi14:.1f} (cần theo dõi)"))

    # Điều kiện 5: Volume
    if vol_ratio >= 1.5:
        score += 2
        details.append(("✅", f"Volume/MA20 = {vol_ratio:.1f}x (đột biến khối lượng)"))
    elif vol_ratio >= 1.0:
        score += 1
        details.append(("✅", f"Volume/MA20 = {vol_ratio:.1f}x (bình thường)"))
    else:
        details.append(("⬇️", f"Volume/MA20 = {vol_ratio:.1f}x (yếu)"))

    if score >= 6:
        signal = "MUA MẠNH 🟢"
    elif score >= 4:
        signal = "MUA 🟡"
    elif score <= 0:
        signal = "BÁN / TRÁNH 🔴"
    else:
        signal = "GIỮ / THEO DÕI ⚪"

    return {
        "signal": signal,
        "score": score,
        "details": details,
        "kijun17": kijun17,
        "knife65": knife65,
        "knife129": knife129,
        "rsi14": rsi14,
        "vol_ratio": vol_ratio,
        "price": price,
    }


# ─────────────────────────────────────────────
# SIDEBAR - Auth
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style='padding:12px 0 8px 0'>
        <span style='color:#60a5fa;font-size:1.1rem;font-weight:700'>⚙️ Cấu hình</span>
    </div>
    """, unsafe_allow_html=True)

    api_key    = st.text_input("API Key", type="password", placeholder="your-api-key")
    api_secret = st.text_input("API Secret", type="password", placeholder="your-api-secret")

    st.divider()
    st.markdown("<span style='color:#64748b;font-size:0.75rem'>📡 DNSE OpenAPI v2026</span>", unsafe_allow_html=True)

    # Nút clear cache
    if st.button("🔄 Làm mới dữ liệu"):
        st.cache_data.clear()
        st.rerun()

    auto_refresh = st.checkbox("⏱️ Tự động làm mới (30s)", value=False)


# ─────────────────────────────────────────────
# AUTO REFRESH
# ─────────────────────────────────────────────
if auto_refresh:
    import streamlit as _st
    time.sleep(0.1)
    st.markdown(
        '<meta http-equiv="refresh" content="30">',
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────
now_str = datetime.now().strftime("%H:%M:%S %d/%m/%Y")
st.markdown(f"""
<div class='dash-header'>
    <span style='font-size:2rem'>📈</span>
    <div>
        <h1>DNSE Account Dashboard</h1>
        <div class='sub'>
            <span class='status-live'></span>
            Cập nhật lúc {now_str} &nbsp;·&nbsp; OpenAPI v2026
        </div>
    </div>
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# GUARD: cần API key
# ─────────────────────────────────────────────
if not api_key or not api_secret:
    st.info("👈 Nhập **API Key** và **API Secret** ở sidebar để bắt đầu.")
    st.stop()


# ─────────────────────────────────────────────
# LOAD ACCOUNTS
# ─────────────────────────────────────────────
with st.spinner("Đang tải danh sách tài khoản..."):
    accounts = get_accounts(api_key, api_secret)

if not accounts:
    st.error("Không lấy được danh sách tài khoản. Kiểm tra API Key/Secret.")
    st.stop()

# Tự động chọn tài khoản đầu tiên (bạn chỉ có 1)
acct_ids = [a.get("id", a.get("accountNo", str(a))) if isinstance(a, dict) else str(a) for a in accounts]
selected_acct = acct_ids[0]  # auto-select vì chỉ có 1 tài khoản

if len(acct_ids) > 1:
    selected_acct = st.sidebar.selectbox("Tiểu khoản", acct_ids)

st.sidebar.markdown(f"""
<div style='margin-top:8px;padding:8px 12px;background:#1e3a5f;border-radius:8px;border:1px solid #1d4ed8'>
    <span style='color:#94a3b8;font-size:0.72rem'>TIỂU KHOẢN ĐANG CHỌN</span><br>
    <span style='color:#60a5fa;font-weight:700;font-family:monospace'>{selected_acct}</span>
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# LOAD DATA PARALLEL (dùng spinner riêng)
# ─────────────────────────────────────────────
col_spin1, col_spin2 = st.columns(2)
with col_spin1:
    with st.spinner("Tải vị thế..."):
        positions = get_positions(api_key, api_secret, selected_acct)
with col_spin2:
    with st.spinner("Tải số dư..."):
        balances = get_balances(api_key, api_secret, selected_acct)


# ─────────────────────────────────────────────
# SUMMARY METRIC CARDS
# ─────────────────────────────────────────────
def safe_float(d, *keys):
    for k in keys:
        v = d.get(k)
        if v is not None:
            try: return float(v)
            except: pass
    return 0.0

net_asset   = safe_float(balances, "netAsset", "equity", "totalAsset")
cash        = safe_float(balances, "cash", "availableCash", "cashBalance")
buy_power   = safe_float(balances, "buyingPower", "purchasingPower", "availableBalance")
margin_used = safe_float(balances, "marginUsed", "loanBalance", "debtAmount")

pnl_df = calc_pnl(positions)
total_pnl     = pnl_df["P&L (VNĐ)"].sum() if not pnl_df.empty else 0
total_mkt_val = pnl_df["Giá trị TT"].sum() if not pnl_df.empty else 0

def delta_cls(v): return "pos" if v > 0 else ("neg" if v < 0 else "neu")
def delta_icon(v): return "▲" if v > 0 else ("▼" if v < 0 else "–")

st.markdown(f"""
<div class='metric-row'>
    <div class='metric-card'>
        <div class='label'>💰 Tài sản ròng</div>
        <div class='value'>{fmt_vnd(net_asset)}</div>
        <div class='delta neu'>VNĐ</div>
    </div>
    <div class='metric-card'>
        <div class='label'>💵 Tiền mặt</div>
        <div class='value'>{fmt_vnd(cash)}</div>
        <div class='delta neu'>Khả dụng</div>
    </div>
    <div class='metric-card'>
        <div class='label'>🛒 Sức mua</div>
        <div class='value'>{fmt_vnd(buy_power)}</div>
        <div class='delta neu'>Có thể đặt lệnh</div>
    </div>
    <div class='metric-card'>
        <div class='label'>📊 Giá trị cổ phiếu</div>
        <div class='value'>{fmt_vnd(total_mkt_val)}</div>
        <div class='delta neu'>{len(positions)} mã</div>
    </div>
    <div class='metric-card'>
        <div class='label'>📈 Lãi/Lỗ hôm nay</div>
        <div class='value'>{fmt_vnd(total_pnl)}</div>
        <div class='delta {delta_cls(total_pnl)}'>{delta_icon(total_pnl)} {fmt_pct(total_pnl / (total_mkt_val - total_pnl) * 100 if total_mkt_val - total_pnl else 0)}</div>
    </div>
    <div class='metric-card'>
        <div class='label'>🏦 Dư nợ margin</div>
        <div class='value'>{fmt_vnd(margin_used)}</div>
        <div class='delta neg' style='color:{"#ef4444" if margin_used > 0 else "#22c55e"}'>
            {"Đang dùng margin" if margin_used > 0 else "Không dùng margin"}
        </div>
    </div>
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Vị thế", "💰 Số dư chi tiết", "📋 Lệnh đang chờ", "📜 Lịch sử lệnh", "🤖 Bot điểm mua"
])


# ══════════════════════════════════════════════
# TAB 1: VỊ THẾ + P&L
# ══════════════════════════════════════════════
with tab1:
    if pnl_df.empty:
        st.info("Không có vị thế nào đang nắm giữ.")
    else:
        # Bảng P&L có màu
        styled = pnl_df.style.format({
            "Giá vốn":      fmt_vnd,
            "Giá hiện tại": fmt_vnd,
            "Giá trị TT":   fmt_vnd,
            "P&L (VNĐ)":    fmt_vnd,
            "P&L (%)":      fmt_pct,
        }).applymap(color_pnl, subset=["P&L (VNĐ)", "P&L (%)"])

        st.dataframe(styled, use_container_width=True, height=300)

        # Biểu đồ P&L waterfall
        fig = go.Figure(go.Bar(
            x=pnl_df["Mã CP"],
            y=pnl_df["P&L (VNĐ)"],
            marker_color=["#22c55e" if v >= 0 else "#ef4444" for v in pnl_df["P&L (VNĐ)"]],
            text=[fmt_pct(v) for v in pnl_df["P&L (%)"]],
            textposition="outside",
        ))
        fig.update_layout(
            title="P&L theo mã cổ phiếu",
            plot_bgcolor="#0f172a",
            paper_bgcolor="#0f172a",
            font=dict(family="Inter", color="#f1f5f9"),
            xaxis=dict(gridcolor="#1e293b"),
            yaxis=dict(gridcolor="#1e293b", tickformat=",.0f"),
            height=320,
            margin=dict(t=40, b=20, l=20, r=20),
        )
        st.plotly_chart(fig, use_container_width=True)

        # Pie chart phân bổ danh mục
        col_a, col_b = st.columns(2)
        with col_a:
            fig2 = px.pie(
                pnl_df, values="Giá trị TT", names="Mã CP",
                title="Phân bổ danh mục",
                color_discrete_sequence=px.colors.qualitative.Set3,
            )
            fig2.update_layout(
                plot_bgcolor="#0f172a", paper_bgcolor="#0f172a",
                font=dict(family="Inter", color="#f1f5f9"),
                height=280, margin=dict(t=40, b=10, l=10, r=10),
            )
            st.plotly_chart(fig2, use_container_width=True)

        with col_b:
            total_cost = (pnl_df["Giá vốn"] * pnl_df["Khối lượng"]).sum()
            total_gain = pnl_df[pnl_df["P&L (VNĐ)"] >= 0]["P&L (VNĐ)"].sum()
            total_loss = abs(pnl_df[pnl_df["P&L (VNĐ)"] < 0]["P&L (VNĐ)"].sum())
            n_win = (pnl_df["P&L (VNĐ)"] >= 0).sum()
            n_lose = (pnl_df["P&L (VNĐ)"] < 0).sum()
            win_rate = n_win / len(pnl_df) * 100 if len(pnl_df) else 0

            st.markdown(f"""
            <div class='bot-card' style='margin-top:0'>
                <h4>📊 Tổng kết danh mục</h4>
                <table style='width:100%;color:#f1f5f9;font-size:0.85rem'>
                    <tr><td style='color:#64748b;padding:4px 0'>Giá vốn TT</td>
                        <td style='text-align:right;font-family:monospace'>{fmt_vnd(total_cost)}</td></tr>
                    <tr><td style='color:#64748b;padding:4px 0'>Tổng lãi</td>
                        <td style='text-align:right;color:#22c55e;font-family:monospace'>+{fmt_vnd(total_gain)}</td></tr>
                    <tr><td style='color:#64748b;padding:4px 0'>Tổng lỗ</td>
                        <td style='text-align:right;color:#ef4444;font-family:monospace'>-{fmt_vnd(total_loss)}</td></tr>
                    <tr><td style='color:#64748b;padding:4px 0'>Win rate</td>
                        <td style='text-align:right;font-weight:700'>{win_rate:.0f}% ({n_win}W/{n_lose}L)</td></tr>
                </table>
            </div>
            """, unsafe_allow_html=True)


# ══════════════════════════════════════════════
# TAB 2: SỐ DƯ CHI TIẾT
# ══════════════════════════════════════════════
with tab2:
    if not balances:
        st.info("Không có dữ liệu số dư.")
    else:
        # Hiển thị tất cả fields từ API
        rows = []
        field_labels = {
            "cash": "Tiền mặt",
            "cashBalance": "Tiền mặt",
            "availableCash": "Tiền khả dụng",
            "buyingPower": "Sức mua",
            "purchasingPower": "Sức mua",
            "netAsset": "Tài sản ròng",
            "equity": "Vốn chủ sở hữu",
            "totalAsset": "Tổng tài sản",
            "marginUsed": "Dư nợ margin",
            "loanBalance": "Dư nợ vay",
            "debtAmount": "Tổng nợ",
            "marginRate": "Tỷ lệ margin (%)",
            "stockValue": "Giá trị CP",
            "creditLimit": "Hạn mức tín dụng",
            "ppseValue": "Giá trị PPSE",
        }
        for k, v in balances.items():
            label = field_labels.get(k, k)
            try:
                val_f = float(v)
                rows.append({"Chỉ tiêu": label, "Giá trị": fmt_vnd(val_f), "Raw key": k})
            except (TypeError, ValueError):
                rows.append({"Chỉ tiêu": label, "Giá trị": str(v), "Raw key": k})

        if rows:
            df_bal = pd.DataFrame(rows)
            st.dataframe(df_bal[["Chỉ tiêu", "Giá trị"]], use_container_width=True, hide_index=True)

        # Gauge sức mua
        if buy_power > 0 and net_asset > 0:
            usage_pct = min((net_asset - buy_power) / net_asset * 100, 100)
            fig_g = go.Figure(go.Indicator(
                mode="gauge+number+delta",
                value=usage_pct,
                title={"text": "Tỷ lệ sử dụng vốn (%)", "font": {"color": "#f1f5f9", "family": "Inter"}},
                gauge={
                    "axis": {"range": [0, 100], "tickcolor": "#64748b"},
                    "bar": {"color": "#1d4ed8"},
                    "steps": [
                        {"range": [0, 50], "color": "#14532d"},
                        {"range": [50, 80], "color": "#713f12"},
                        {"range": [80, 100], "color": "#450a0a"},
                    ],
                    "threshold": {"line": {"color": "#ef4444", "width": 4}, "value": 85},
                },
                number={"suffix": "%", "font": {"color": "#f1f5f9", "family": "JetBrains Mono"}},
            ))
            fig_g.update_layout(
                paper_bgcolor="#0f172a", font_color="#f1f5f9",
                height=260, margin=dict(t=40, b=10, l=30, r=30),
            )
            st.plotly_chart(fig_g, use_container_width=True)


# ══════════════════════════════════════════════
# TAB 3: LỆNH ĐANG CHỜ
# ══════════════════════════════════════════════
with tab3:
    with st.spinner("Tải lệnh đang chờ..."):
        orders = get_orders(api_key, api_secret, selected_acct)

    if not orders:
        st.info("Không có lệnh đang chờ khớp.")
    else:
        df_ord = pd.DataFrame(orders)
        # Chuẩn hóa tên cột phổ biến
        rename_map = {
            "symbol": "Mã CP", "secSymbol": "Mã CP",
            "side": "Chiều", "orderSide": "Chiều",
            "qty": "KL đặt", "volume": "KL đặt",
            "matchedQty": "KL khớp", "filledQty": "KL khớp",
            "price": "Giá đặt", "orderPrice": "Giá đặt",
            "status": "Trạng thái", "orderStatus": "Trạng thái",
            "orderId": "Mã lệnh", "id": "Mã lệnh",
            "createdAt": "Thời gian", "orderTime": "Thời gian",
        }
        df_ord = df_ord.rename(columns={k: v for k, v in rename_map.items() if k in df_ord.columns})
        display_cols = [c for c in ["Mã lệnh", "Mã CP", "Chiều", "KL đặt", "KL khớp", "Giá đặt", "Trạng thái", "Thời gian"] if c in df_ord.columns]
        st.dataframe(df_ord[display_cols] if display_cols else df_ord, use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════
# TAB 4: LỊCH SỬ LỆNH
# ══════════════════════════════════════════════
with tab4:
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        from_date = st.date_input("Từ ngày", datetime.now() - timedelta(days=30))
    with col_d2:
        to_date = st.date_input("Đến ngày", datetime.now())

    if st.button("📥 Tải lịch sử lệnh"):
        with st.spinner("Đang tải lịch sử..."):
            hist = get_order_history(
                api_key, api_secret, selected_acct,
                from_date.strftime("%Y-%m-%d"),
                to_date.strftime("%Y-%m-%d"),
            )
        if not hist:
            st.info("Không có lệnh nào trong khoảng thời gian này.")
        else:
            df_h = pd.DataFrame(hist)
            rename_map2 = {
                "symbol": "Mã CP", "secSymbol": "Mã CP",
                "side": "Chiều", "orderSide": "Chiều",
                "qty": "KL đặt", "matchedQty": "KL khớp",
                "price": "Giá đặt", "matchedPrice": "Giá khớp",
                "status": "Trạng thái",
                "matchedAmount": "Giá trị khớp",
                "createdAt": "Ngày GD", "orderDate": "Ngày GD",
            }
            df_h = df_h.rename(columns={k: v for k, v in rename_map2.items() if k in df_h.columns})
            display_h = [c for c in ["Ngày GD", "Mã CP", "Chiều", "KL đặt", "KL khớp", "Giá đặt", "Giá khớp", "Giá trị khớp", "Trạng thái"] if c in df_h.columns]
            st.dataframe(df_h[display_h] if display_h else df_h, use_container_width=True, hide_index=True)

            # Thống kê nhanh
            if "Mã CP" in df_h.columns and "Giá trị khớp" in df_h.columns:
                try:
                    df_h["Giá trị khớp"] = pd.to_numeric(df_h["Giá trị khớp"], errors="coerce")
                    by_sym = df_h.groupby("Mã CP")["Giá trị khớp"].sum().sort_values(ascending=False)
                    fig_bar = px.bar(
                        x=by_sym.index, y=by_sym.values,
                        labels={"x": "Mã CP", "y": "Giá trị giao dịch"},
                        title="Giá trị giao dịch theo mã",
                        color_discrete_sequence=["#3b82f6"],
                    )
                    fig_bar.update_layout(
                        plot_bgcolor="#0f172a", paper_bgcolor="#0f172a",
                        font=dict(family="Inter", color="#f1f5f9"),
                        height=280, margin=dict(t=40, b=20, l=20, r=20),
                    )
                    st.plotly_chart(fig_bar, use_container_width=True)
                except Exception:
                    pass


# ══════════════════════════════════════════════
# TAB 5: BOT ĐIỂM MUA (Cô Tiên Logic)
# ══════════════════════════════════════════════
with tab5:
    st.markdown("""
    <div style='color:#94a3b8;font-size:0.82rem;margin-bottom:1rem;padding:8px 12px;background:#1e293b;border-radius:8px;border-left:3px solid #1d4ed8'>
        🤖 Bot phân tích theo hệ thống <strong>Cô Tiên</strong>: Kijun17 · Knife65 · Knife129 · RSI14 · Volume/MA20
    </div>
    """, unsafe_allow_html=True)

    # Lấy danh sách mã từ vị thế hoặc nhập tay
    position_symbols = []
    if pnl_df is not None and not pnl_df.empty:
        position_symbols = pnl_df["Mã CP"].tolist()

    col_bot1, col_bot2 = st.columns([2, 1])
    with col_bot1:
        symbols_input = st.text_input(
            "Nhập mã cổ phiếu (cách nhau bởi dấu phẩy)",
            value=", ".join(position_symbols) if position_symbols else "HPG, VNM, FPT, VIC, MWG",
            placeholder="HPG, VNM, FPT",
        )
    with col_bot2:
        sim_days = st.slider("Số ngày mô phỏng giá", min_value=60, max_value=365, value=130, step=10)

    run_bot = st.button("🚀 Chạy phân tích Bot")

    if run_bot:
        symbols = [s.strip().upper() for s in symbols_input.split(",") if s.strip()]
        if not symbols:
            st.warning("Nhập ít nhất 1 mã cổ phiếu.")
        else:
            results = []
            for sym in symbols:
                # Sinh giá mô phỏng (random walk) — thay bằng API giá thực tế nếu có
                np.random.seed(hash(sym) % 10000)
                base = np.random.uniform(10000, 80000)
                returns = np.random.normal(0.0005, 0.015, sim_days)
                prices_sim  = base * np.cumprod(1 + returns)
                volumes_sim = np.random.lognormal(mean=14, sigma=0.8, size=sim_days).tolist()

                sig = compute_signals(prices_sim.tolist(), volumes_sim)
                sig["symbol"] = sym
                sig["prices"] = prices_sim
                results.append(sig)

            # Sắp xếp theo score
            results.sort(key=lambda x: x["score"], reverse=True)

            # Hiển thị kết quả
            for r in results:
                signal_html = f"<span class='signal-buy'>{r['signal']}</span>" if "MUA" in r["signal"] \
                    else (f"<span class='signal-sell'>{r['signal']}</span>" if "BÁN" in r["signal"] \
                    else f"<span class='signal-hold'>{r['signal']}</span>")

                with st.expander(f"**{r['symbol']}** — {r['signal']}  (điểm: {r['score']}/8)", expanded=(r["score"] >= 4)):
                    col_s1, col_s2 = st.columns([1, 2])
                    with col_s1:
                        st.markdown(f"""
                        <div class='bot-card'>
                            <div class='ticker'>{r['symbol']}</div>
                            <div style='margin:8px 0'>{signal_html}</div>
                            <table style='width:100%;color:#f1f5f9;font-size:0.8rem'>
                                <tr><td style='color:#64748b'>Giá hiện tại</td>
                                    <td style='text-align:right;font-family:monospace'>{r['price']:,.0f}</td></tr>
                                <tr><td style='color:#64748b'>Kijun17</td>
                                    <td style='text-align:right;font-family:monospace'>{r['kijun17']:,.0f}</td></tr>
                                <tr><td style='color:#64748b'>Knife65</td>
                                    <td style='text-align:right;font-family:monospace'>{r['knife65']:,.0f}</td></tr>
                                <tr><td style='color:#64748b'>Knife129</td>
                                    <td style='text-align:right;font-family:monospace'>{r['knife129']:,.0f}</td></tr>
                                <tr><td style='color:#64748b'>RSI14</td>
                                    <td style='text-align:right;font-family:monospace'>{r['rsi14']:.1f}</td></tr>
                                <tr><td style='color:#64748b'>Vol/MA20</td>
                                    <td style='text-align:right;font-family:monospace'>{r['vol_ratio']:.2f}x</td></tr>
                                <tr><td style='color:#64748b'>Điểm tổng</td>
                                    <td style='text-align:right;font-weight:700;color:#60a5fa'>{r['score']}/8</td></tr>
                            </table>
                        </div>
                        """, unsafe_allow_html=True)

                        # Chi tiết điều kiện
                        for icon, detail in r["details"]:
                            st.markdown(f"<div style='font-size:0.78rem;color:#94a3b8;padding:2px 0'>{icon} {detail}</div>", unsafe_allow_html=True)

                    with col_s2:
                        # Chart giá + đường MA
                        prices_arr = r["prices"]
                        x_idx = list(range(len(prices_arr)))

                        def ema_series(data, period):
                            k = 2 / (period + 1)
                            result = [data[0]]
                            for p in data[1:]:
                                result.append(p * k + result[-1] * (1 - k))
                            return result

                        fig_c = go.Figure()
                        fig_c.add_trace(go.Scatter(
                            x=x_idx, y=prices_arr, name="Giá",
                            line=dict(color="#94a3b8", width=1.5),
                        ))
                        fig_c.add_trace(go.Scatter(
                            x=x_idx, y=ema_series(prices_arr, 17),
                            name="Kijun17", line=dict(color="#f59e0b", width=1.5, dash="dot"),
                        ))
                        if len(prices_arr) >= 65:
                            fig_c.add_trace(go.Scatter(
                                x=x_idx, y=ema_series(prices_arr, 65),
                                name="Knife65", line=dict(color="#3b82f6", width=1.5),
                            ))
                        if len(prices_arr) >= 100:
                            fig_c.add_trace(go.Scatter(
                                x=x_idx, y=ema_series(prices_arr, min(129, len(prices_arr))),
                                name="Knife129", line=dict(color="#8b5cf6", width=1.5, dash="dash"),
                            ))
                        fig_c.update_layout(
                            title=f"{r['symbol']} — Kijun/Knife Lines",
                            plot_bgcolor="#0f172a", paper_bgcolor="#0f172a",
                            font=dict(family="Inter", color="#f1f5f9"),
                            xaxis=dict(gridcolor="#1e293b", showticklabels=False),
                            yaxis=dict(gridcolor="#1e293b", tickformat=",.0f"),
                            legend=dict(bgcolor="#1e293b", font=dict(size=11)),
                            height=300, margin=dict(t=40, b=20, l=20, r=20),
                        )
                        st.plotly_chart(fig_c, use_container_width=True)

            # Bảng tóm tắt tất cả mã
            st.markdown("### 📋 Bảng xếp hạng tín hiệu")
            summary_rows = [{
                "Mã CP": r["symbol"],
                "Tín hiệu": r["signal"],
                "Điểm": r["score"],
                "RSI14": f"{r['rsi14']:.1f}",
                "Vol/MA20": f"{r['vol_ratio']:.2f}x",
                "Giá": f"{r['price']:,.0f}",
                "Kijun17": f"{r['kijun17']:,.0f}",
            } for r in results]
            st.dataframe(pd.DataFrame(summary_rows), use_container_width=True, hide_index=True)

    else:
        st.markdown("""
        <div style='color:#64748b;text-align:center;padding:40px;'>
            Nhập mã cổ phiếu và nhấn <strong>🚀 Chạy phân tích Bot</strong>
        </div>
        """, unsafe_allow_html=True)
