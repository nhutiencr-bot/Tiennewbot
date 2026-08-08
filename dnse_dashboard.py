"""
DNSE Account Dashboard
Xem thông tin tài khoản và vị thế nắm giữ qua DNSE OpenAPI
"""
import json
import streamlit as st
import pandas as pd
from dnse.api.client import DNSEClient

# ── Page config ──────────────────────────────────────────────
st.set_page_config(
    page_title="DNSE Dashboard",
    page_icon="📈",
    layout="wide",
)

# ── Custom CSS ────────────────────────────────────────────────
st.markdown("""
<style>
    .metric-card {
        background: #1e2130;
        border-radius: 10px;
        padding: 16px 20px;
        border-left: 4px solid #00d4aa;
        margin-bottom: 8px;
    }
    .metric-label { color: #8892a4; font-size: 13px; margin-bottom: 4px; }
    .metric-value { color: #ffffff; font-size: 22px; font-weight: 700; }
    .positive { color: #00d4aa !important; }
    .negative { color: #ff5252 !important; }
    .stDataFrame { font-size: 13px; }
    div[data-testid="stSidebar"] { background: #131722; }
    .sidebar-title { color: #00d4aa; font-weight: 700; font-size: 18px; }
</style>
""", unsafe_allow_html=True)

# ── Sidebar: Credentials ──────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="sidebar-title">🔐 DNSE API Credentials</div>', unsafe_allow_html=True)
    st.markdown("---")

    api_key = st.text_input(
        "API Key (X-API-Key)",
        type="password",
        placeholder="eyJvcmciOiJkbnNlIiwi...",
        help="API Key được cấp từ DNSE Developer Portal",
    )
    api_secret = st.text_input(
        "API Secret",
        type="password",
        placeholder="Nhập API Secret của bạn",
        help="Secret dùng để ký HMAC-SHA256",
    )

    st.markdown("---")
    st.markdown("**API Version**")
    api_version = st.text_input("Version (YYYY-MM-DD)", value="2026-07-23")

    st.markdown("---")
    st.caption("🔒 Credentials chỉ lưu trong session, không được ghi ra bất kỳ đâu.")
    st.caption("📖 [Tài liệu DNSE API](https://developers.dnse.com.vn/docs/dnse/account)")

# ── Helper: build client ──────────────────────────────────────
def get_client():
    if not api_key or not api_secret:
        return None
    return DNSEClient(
        api_key=api_key,
        api_secret=api_secret,
        base_url="https://openapi.dnse.com.vn",
        api_version=api_version or "2026-07-23",
    )


def safe_call(fn, *args, **kwargs):
    """Gọi API và trả về (status, data_dict | None, error_msg | None)"""
    try:
        status, body = fn(*args, **kwargs)
        if body:
            data = json.loads(body)
        else:
            data = {}
        if status and status >= 400:
            return status, None, data.get("message") or body
        return status, data, None
    except Exception as e:
        return None, None, str(e)


def fmt_money(val, unit=1000):
    """Format số tiền VND"""
    if val is None:
        return "—"
    try:
        v = float(val) * unit
        if abs(v) >= 1e9:
            return f"{v/1e9:,.2f} tỷ"
        if abs(v) >= 1e6:
            return f"{v/1e6:,.0f} tr"
        return f"{v:,.0f}"
    except Exception:
        return str(val)


def pnl_color(val):
    """CSS class theo lãi/lỗ"""
    try:
        return "positive" if float(val) >= 0 else "negative"
    except Exception:
        return ""


# ── Main UI ───────────────────────────────────────────────────
st.title("📈 DNSE Account Dashboard")

if not api_key or not api_secret:
    st.info("👈 Nhập **API Key** và **API Secret** trong thanh bên trái để bắt đầu.")
    st.stop()

client = get_client()

# ── Tabs ──────────────────────────────────────────────────────
tab_accounts, tab_positions, tab_balances = st.tabs(
    ["🏦 Tài khoản", "📊 Vị thế nắm giữ", "💰 Số dư tài khoản"]
)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TAB 1: Danh sách tài khoản
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with tab_accounts:
    st.subheader("Danh sách tiểu khoản")
    if st.button("🔄 Tải danh sách tài khoản", key="load_accounts"):
        with st.spinner("Đang lấy dữ liệu..."):
            status, data, err = safe_call(client.get_accounts)

        if err:
            st.error(f"❌ Lỗi {status}: {err}")
        elif data:
            accounts = data if isinstance(data, list) else data.get("accounts", [data])
            st.session_state["accounts"] = accounts
            st.success(f"✅ Tìm thấy **{len(accounts)}** tiểu khoản")

    accounts = st.session_state.get("accounts", [])
    if accounts:
        rows = []
        for acc in accounts:
            rows.append({
                "Số tiểu khoản": acc.get("accountNo") or acc.get("id") or acc.get("subAccountId", "—"),
                "Tên": acc.get("name") or acc.get("accountName", "—"),
                "Loại": acc.get("type") or acc.get("accountType", "—"),
                "Trạng thái": acc.get("status", "—"),
            })
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)

        # Lưu account_no để dùng ở tab khác
        account_nos = [r["Số tiểu khoản"] for r in rows if r["Số tiểu khoản"] != "—"]
        if account_nos:
            st.session_state["account_nos"] = account_nos

        with st.expander("Raw JSON"):
            st.json(accounts)
    else:
        st.caption("Nhấn nút **Tải danh sách tài khoản** để xem dữ liệu.")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TAB 2: Vị thế nắm giữ
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with tab_positions:
    st.subheader("Vị thế nắm giữ")

    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        account_nos = st.session_state.get("account_nos", [])
        if account_nos:
            account_no = st.selectbox("Chọn tiểu khoản", account_nos, key="pos_account")
        else:
            account_no = st.text_input(
                "Số tiểu khoản",
                placeholder="0001179019",
                help="Nhập số tiểu khoản hoặc tải danh sách ở tab Tài khoản trước",
                key="pos_account_manual",
            )
    with col2:
        market_type = st.selectbox(
            "Loại thị trường",
            ["STOCK", "DERIVATIVE"],
            key="pos_market",
        )
    with col3:
        page_size = st.number_input("Page size", min_value=1, max_value=100, value=20, key="pos_page")

    if st.button("🔄 Tải vị thế", key="load_positions", type="primary"):
        acc = account_no if isinstance(account_no, str) else str(account_no)
        if not acc:
            st.warning("⚠️ Vui lòng nhập số tiểu khoản.")
        else:
            with st.spinner("Đang lấy vị thế..."):
                status, data, err = safe_call(
                    client.get_positions, acc, market_type
                )
            if err:
                st.error(f"❌ Lỗi {status}: {err}")
            else:
                st.session_state["positions_data"] = data
                st.session_state["positions_market"] = market_type

    # Render positions
    data = st.session_state.get("positions_data")
    if data:
        positions = data.get("positions", [])
        market = st.session_state.get("positions_market", "STOCK")

        # KPI row
        if positions:
            total_market_val = sum(
                float(p.get("marketValue") or p.get("mktValue") or 0) for p in positions
            )
            total_cost = sum(
                float(p.get("costValue") or p.get("avgPrice", 0)) * float(p.get("quantity") or p.get("qty") or 0)
                for p in positions
            )
            total_pnl = sum(
                float(p.get("unrealizedPnL") or p.get("unrealizedPnl") or p.get("pnl") or 0)
                for p in positions
            )

            kpi1, kpi2, kpi3, kpi4 = st.columns(4)
            kpi1.metric("Số mã nắm giữ", len(positions))
            kpi2.metric("Tổng giá trị TT", f"{total_market_val:,.0f}")
            kpi3.metric("Tổng vốn", f"{total_cost:,.0f}")
            pnl_sign = "+" if total_pnl >= 0 else ""
            kpi4.metric("Lãi/Lỗ chưa thực hiện", f"{pnl_sign}{total_pnl:,.0f}")

            st.markdown("---")

        if positions:
            # Build table với STOCK fields
            if market == "STOCK":
                rows = []
                for p in positions:
                    symbol = p.get("symbol") or p.get("instrumentId", "—")
                    qty = p.get("quantity") or p.get("qty") or 0
                    avail = p.get("availableQuantity") or p.get("availQty") or qty
                    avg = p.get("averagePrice") or p.get("avgPrice") or 0
                    mkt = p.get("currentPrice") or p.get("marketPrice") or p.get("closePrice") or 0
                    cost_val = p.get("costValue") or (float(qty) * float(avg) if qty and avg else 0)
                    mkt_val = p.get("marketValue") or p.get("mktValue") or (float(qty) * float(mkt) if qty and mkt else 0)
                    pnl = p.get("unrealizedPnL") or p.get("unrealizedPnl") or p.get("pnl") or 0
                    pnl_pct = p.get("unrealizedPnLPct") or p.get("pnlPct") or (
                        (float(pnl) / float(cost_val) * 100) if cost_val and float(cost_val) != 0 else 0
                    )
                    rows.append({
                        "Mã CK": symbol,
                        "KL sở hữu": int(float(qty)) if qty else 0,
                        "KL khả dụng": int(float(avail)) if avail else 0,
                        "Giá vốn": round(float(avg), 2) if avg else 0,
                        "Giá TT": round(float(mkt), 2) if mkt else 0,
                        "Giá trị vốn": round(float(cost_val), 0) if cost_val else 0,
                        "Giá trị TT": round(float(mkt_val), 0) if mkt_val else 0,
                        "Lãi/Lỗ": round(float(pnl), 0) if pnl else 0,
                        "%": round(float(pnl_pct), 2) if pnl_pct else 0,
                    })

                df = pd.DataFrame(rows)

                # Color formatting
                def highlight_pnl(row):
                    styles = [""] * len(row)
                    idx = df.columns.get_loc("Lãi/Lỗ")
                    val = row["Lãi/Lỗ"]
                    color = "color: #00d4aa" if val >= 0 else "color: #ff5252"
                    styles[idx] = color
                    idx2 = df.columns.get_loc("%")
                    styles[idx2] = color
                    return styles

                styled = df.style.apply(highlight_pnl, axis=1).format({
                    "Giá vốn": "{:,.2f}",
                    "Giá TT": "{:,.2f}",
                    "Giá trị vốn": "{:,.0f}",
                    "Giá trị TT": "{:,.0f}",
                    "Lãi/Lỗ": "{:+,.0f}",
                    "%": "{:+.2f}%",
                })
                st.dataframe(styled, use_container_width=True, hide_index=True)

            else:
                # DERIVATIVE — hiển thị raw vì field khác nhau tùy version
                st.dataframe(pd.json_normalize(positions), use_container_width=True, hide_index=True)

            # Phân trang info (phái sinh)
            if market == "DERIVATIVE":
                meta_cols = st.columns(4)
                meta_cols[0].metric("pageIndex", data.get("pageIndex", 0))
                meta_cols[1].metric("pageSize", data.get("pageSize", 20))
                meta_cols[2].metric("pageNumber", data.get("pageNumber", 1))
                meta_cols[3].metric("Tổng", data.get("total", len(positions)))

        else:
            st.info("📭 Không có vị thế nào trong tài khoản này.")

        with st.expander("Raw JSON"):
            st.json(data)
    else:
        st.caption("Chọn tiểu khoản và nhấn **Tải vị thế** để xem.")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TAB 3: Số dư tài khoản
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with tab_balances:
    st.subheader("Số dư tài khoản")

    account_nos = st.session_state.get("account_nos", [])
    if account_nos:
        bal_account = st.selectbox("Chọn tiểu khoản", account_nos, key="bal_account")
    else:
        bal_account = st.text_input(
            "Số tiểu khoản",
            placeholder="0001179019",
            key="bal_account_manual",
        )

    if st.button("🔄 Tải số dư", key="load_balances", type="primary"):
        acc = bal_account if isinstance(bal_account, str) else str(bal_account)
        if not acc:
            st.warning("⚠️ Vui lòng nhập số tiểu khoản.")
        else:
            with st.spinner("Đang lấy số dư..."):
                status, data, err = safe_call(client.get_balances, acc)
            if err:
                st.error(f"❌ Lỗi {status}: {err}")
            else:
                st.session_state["balances_data"] = data

    data = st.session_state.get("balances_data")
    if data:
        # Hiển thị các field phổ biến
        field_map = {
            "cash": "Tiền mặt",
            "availableCash": "Tiền khả dụng",
            "equity": "Tổng tài sản ròng",
            "totalAsset": "Tổng tài sản",
            "stockValue": "Giá trị chứng khoán",
            "debtValue": "Giá trị nợ",
            "marginRate": "Tỷ lệ ký quỹ (%)",
            "buyingPower": "Sức mua",
        }

        display = {}
        flat = data if isinstance(data, dict) else {}
        for k, label in field_map.items():
            if k in flat:
                display[label] = flat[k]

        if display:
            cols = st.columns(min(len(display), 4))
            for i, (label, val) in enumerate(display.items()):
                with cols[i % 4]:
                    try:
                        fval = float(val)
                        if "%" not in label:
                            sign = "+" if fval > 0 else ""
                            display_val = f"{fval:,.0f}"
                        else:
                            display_val = f"{fval:.2f}%"
                    except Exception:
                        display_val = str(val)
                    st.metric(label, display_val)

        with st.expander("Raw JSON"):
            st.json(data)
    else:
        st.caption("Nhấn **Tải số dư** để xem thông tin tài sản.")
