"""
DNSE Account Dashboard  ·  Cô Tiên 🧚
Xem thông tin tài khoản & vị thế nắm giữ qua DNSE OpenAPI
"""
import json
import streamlit as st
import pandas as pd
from dnse.api.client import DNSEClient

# ─────────────────────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="DNSE Dashboard · Cô Tiên",
    page_icon="🧚",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Sidebar */
    [data-testid="stSidebar"] { background: #131722; }
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 { color: #00d4aa; }

    /* Positive / Negative */
    .pos { color: #00d4aa; font-weight: 700; }
    .neg { color: #ff5252; font-weight: 700; }

    /* Table tweaks */
    .stDataFrame thead th { background: #1e2130 !important; }
    .stDataFrame { font-size: 13px; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# Sidebar – Credentials
# ─────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🧚 DNSE Dashboard")
    st.caption("by Cô Tiên")
    st.divider()

    st.subheader("🔐 API Credentials")

    # Streamlit Secrets support (for Cloud deploy)
    _secrets = st.secrets if hasattr(st, "secrets") else {}
    default_key    = _secrets.get("DNSE_API_KEY", "")
    default_secret = _secrets.get("DNSE_API_SECRET", "")
    default_ver    = _secrets.get("DNSE_API_VERSION", "2026-07-23")

    api_key = st.text_input(
        "API Key",
        value=default_key,
        type="password",
        placeholder="eyJvcmciOiJkbnNlIiwi...",
        help="Lấy từ DNSE Developer Portal",
    )
    api_secret = st.text_input(
        "API Secret",
        value=default_secret,
        type="password",
        placeholder="Secret HMAC-SHA256",
    )
    api_version = st.text_input("API Version", value=default_ver)

    st.divider()
    st.caption("🔒 Credentials chỉ tồn tại trong session này.")
    st.caption("📖 [DNSE API Docs](https://developers.dnse.com.vn/docs/dnse/account)")

# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────
@st.cache_resource(show_spinner=False)
def make_client(key, secret, version):
    return DNSEClient(
        api_key=key,
        api_secret=secret,
        base_url="https://openapi.dnse.com.vn",
        api_version=version or "2026-07-23",
    )


def api_call(fn, *args, **kwargs):
    """Gọi API → (data | None, error_str | None)"""
    try:
        status, body = fn(*args, **kwargs)
        data = json.loads(body) if body else {}
        if status and status >= 400:
            msg = data.get("message") or data.get("error") or body or f"HTTP {status}"
            return None, f"[{status}] {msg}"
        return data, None
    except Exception as exc:
        return None, str(exc)


def _float(v, default=0.0):
    try:
        return float(v)
    except Exception:
        return default


def fmt_vnd(v):
    try:
        return f"{float(v):,.0f}"
    except Exception:
        return "—"


def pnl_html(val):
    v = _float(val)
    cls = "pos" if v >= 0 else "neg"
    sign = "+" if v >= 0 else ""
    return f'<span class="{cls}">{sign}{v:,.0f}</span>'


def pct_html(val):
    v = _float(val)
    cls = "pos" if v >= 0 else "neg"
    sign = "+" if v >= 0 else ""
    return f'<span class="{cls}">{sign}{v:.2f}%</span>'


# ─────────────────────────────────────────────────────────────
# Auth guard
# ─────────────────────────────────────────────────────────────
st.title("📈 DNSE Account Dashboard")

if not api_key or not api_secret:
    st.info("👈 Nhập **API Key** và **API Secret** trong sidebar để bắt đầu.")
    st.stop()

client = make_client(api_key, api_secret, api_version)

# ─────────────────────────────────────────────────────────────
# Tabs
# ─────────────────────────────────────────────────────────────
t_acc, t_pos, t_bal = st.tabs(
    ["🏦 Tiểu khoản", "📊 Vị thế nắm giữ", "💰 Số dư"]
)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TAB 1 – Danh sách tiểu khoản
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with t_acc:
    st.subheader("Danh sách tiểu khoản")

    if st.button("🔄 Tải danh sách", key="btn_accounts"):
        with st.spinner("Đang kết nối DNSE..."):
            data, err = api_call(client.get_accounts)
        if err:
            st.error(f"❌ {err}")
        else:
            accs = data if isinstance(data, list) else data.get("accounts", [data])
            st.session_state["accounts"] = accs
            # Cache account numbers
            nos = []
            for a in accs:
                no = a.get("accountNo") or a.get("id") or a.get("subAccountId")
                if no:
                    nos.append(str(no))
            st.session_state["account_nos"] = nos
            st.success(f"✅ Tìm thấy **{len(accs)}** tiểu khoản")

    accs = st.session_state.get("accounts", [])
    if accs:
        rows = []
        for a in accs:
            rows.append({
                "Số tiểu khoản": a.get("accountNo") or a.get("id") or a.get("subAccountId", "—"),
                "Tên tài khoản": a.get("name") or a.get("accountName", "—"),
                "Loại":          a.get("type") or a.get("accountType", "—"),
                "Trạng thái":    a.get("status", "—"),
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        with st.expander("📋 Raw JSON"):
            st.json(accs)
    else:
        st.caption("Nhấn **Tải danh sách** để xem.")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TAB 2 – Vị thế nắm giữ
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with t_pos:
    st.subheader("Vị thế nắm giữ")

    nos = st.session_state.get("account_nos", [])
    c1, c2 = st.columns([2, 1])
    with c1:
        if nos:
            pos_acc = st.selectbox("Tiểu khoản", nos, key="pos_acc")
        else:
            pos_acc = st.text_input("Số tiểu khoản", placeholder="0001179019", key="pos_acc_txt")
    with c2:
        mkt = st.selectbox("Thị trường", ["STOCK", "DERIVATIVE"], key="pos_mkt")

    if st.button("🔄 Tải vị thế", key="btn_positions", type="primary"):
        acc = str(pos_acc).strip() if pos_acc else ""
        if not acc:
            st.warning("⚠️ Vui lòng nhập số tiểu khoản.")
        else:
            with st.spinner("Đang lấy vị thế..."):
                data, err = api_call(client.get_positions, acc, mkt)
            if err:
                st.error(f"❌ {err}")
            else:
                st.session_state["pos_data"] = data
                st.session_state["pos_mkt_label"] = mkt

    pos_data = st.session_state.get("pos_data")
    if pos_data is not None:
        positions = pos_data.get("positions", [])
        cur_mkt = st.session_state.get("pos_mkt_label", "STOCK")

        # ── KPI strip
        if positions:
            total_mkt  = sum(_float(p.get("marketValue") or p.get("mktValue") or 0) for p in positions)
            total_cost = sum(
                _float(p.get("costValue") or 0) or
                (_float(p.get("averagePrice") or p.get("avgPrice") or 0) * _float(p.get("quantity") or p.get("qty") or 0))
                for p in positions
            )
            total_pnl  = sum(_float(p.get("unrealizedPnL") or p.get("unrealizedPnl") or p.get("pnl") or 0) for p in positions)

            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Số mã", len(positions))
            k2.metric("Giá trị TT", fmt_vnd(total_mkt))
            k3.metric("Tổng vốn", fmt_vnd(total_cost))
            delta_color = "normal" if total_pnl >= 0 else "inverse"
            k4.metric(
                "Lãi/Lỗ chưa TH",
                fmt_vnd(total_pnl),
                delta=f"{total_pnl/total_cost*100:+.2f}%" if total_cost else None,
                delta_color=delta_color,
            )
            st.divider()

        # ── Table
        if positions:
            if cur_mkt == "STOCK":
                rows = []
                for p in positions:
                    sym    = p.get("symbol") or p.get("instrumentId", "—")
                    qty    = _float(p.get("quantity") or p.get("qty") or 0)
                    avail  = _float(p.get("availableQuantity") or p.get("availQty") or qty)
                    avg    = _float(p.get("averagePrice") or p.get("avgPrice") or 0)
                    mktpx  = _float(p.get("currentPrice") or p.get("marketPrice") or p.get("closePrice") or 0)
                    cost_v = _float(p.get("costValue") or 0) or qty * avg
                    mkt_v  = _float(p.get("marketValue") or p.get("mktValue") or 0) or qty * mktpx
                    pnl    = _float(p.get("unrealizedPnL") or p.get("unrealizedPnl") or p.get("pnl") or 0)
                    pnl_p  = _float(p.get("unrealizedPnLPct") or p.get("pnlPct") or 0) or (
                        (pnl / cost_v * 100) if cost_v else 0
                    )
                    rows.append({
                        "Mã CK":         sym,
                        "KL sở hữu":     int(qty),
                        "KL khả dụng":   int(avail),
                        "Giá vốn":       round(avg, 2),
                        "Giá TT":        round(mktpx, 2),
                        "Giá trị vốn":   round(cost_v, 0),
                        "Giá trị TT":    round(mkt_v, 0),
                        "Lãi/Lỗ":        round(pnl, 0),
                        "%":             round(pnl_p, 2),
                    })

                df = pd.DataFrame(rows)

                def _style_pnl(row):
                    styles = [""] * len(row)
                    for col in ("Lãi/Lỗ", "%"):
                        if col in df.columns:
                            idx = df.columns.get_loc(col)
                            styles[idx] = "color:#00d4aa;font-weight:700" if row[col] >= 0 else "color:#ff5252;font-weight:700"
                    return styles

                styled = (
                    df.style
                    .apply(_style_pnl, axis=1)
                    .format({
                        "Giá vốn":     "{:,.2f}",
                        "Giá TT":      "{:,.2f}",
                        "Giá trị vốn": "{:,.0f}",
                        "Giá trị TT":  "{:,.0f}",
                        "Lãi/Lỗ":      "{:+,.0f}",
                        "%":           "{:+.2f}%",
                    })
                )
                st.dataframe(styled, use_container_width=True, hide_index=True)

            else:
                # DERIVATIVE – raw normalize
                st.dataframe(pd.json_normalize(positions), use_container_width=True, hide_index=True)

                # Pagination meta
                if any(k in pos_data for k in ("pageIndex", "pageSize", "total")):
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("pageIndex",  pos_data.get("pageIndex", 0))
                    m2.metric("pageSize",   pos_data.get("pageSize", 20))
                    m3.metric("pageNumber", pos_data.get("pageNumber", 1))
                    m4.metric("Tổng",       pos_data.get("total", len(positions)))

        else:
            st.info("📭 Không có vị thế nào trong tài khoản này.")

        with st.expander("📋 Raw JSON"):
            st.json(pos_data)

    else:
        st.caption("Chọn tiểu khoản → nhấn **Tải vị thế**.")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TAB 3 – Số dư
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with t_bal:
    st.subheader("Số dư tài khoản")

    nos = st.session_state.get("account_nos", [])
    if nos:
        bal_acc = st.selectbox("Tiểu khoản", nos, key="bal_acc")
    else:
        bal_acc = st.text_input("Số tiểu khoản", placeholder="0001179019", key="bal_acc_txt")

    if st.button("🔄 Tải số dư", key="btn_balances", type="primary"):
        acc = str(bal_acc).strip() if bal_acc else ""
        if not acc:
            st.warning("⚠️ Vui lòng nhập số tiểu khoản.")
        else:
            with st.spinner("Đang lấy số dư..."):
                data, err = api_call(client.get_balances, acc)
            if err:
                st.error(f"❌ {err}")
            else:
                st.session_state["bal_data"] = data

    bal_data = st.session_state.get("bal_data")
    if bal_data:
        FIELD_MAP = {
            "cash":           "Tiền mặt",
            "availableCash":  "Tiền khả dụng",
            "equity":         "Tổng tài sản ròng",
            "totalAsset":     "Tổng tài sản",
            "stockValue":     "Giá trị chứng khoán",
            "debtValue":      "Giá trị nợ",
            "buyingPower":    "Sức mua",
            "marginRate":     "Tỷ lệ ký quỹ (%)",
            "withdrawable":   "Tiền rút được",
        }
        items = {label: bal_data[k] for k, label in FIELD_MAP.items() if k in bal_data}

        if items:
            cols = st.columns(min(len(items), 4))
            for i, (label, val) in enumerate(items.items()):
                with cols[i % 4]:
                    try:
                        fval = float(val)
                        display = f"{fval:.2f}%" if "%" in label else f"{fval:,.0f}"
                    except Exception:
                        display = str(val)
                    st.metric(label, display)
        else:
            # Fallback: show all numeric fields
            numeric = {k: v for k, v in bal_data.items() if isinstance(v, (int, float, str)) and k != "accountNo"}
            if numeric:
                st.dataframe(
                    pd.DataFrame([{"Chỉ tiêu": k, "Giá trị": v} for k, v in numeric.items()]),
                    use_container_width=True,
                    hide_index=True,
                )

        with st.expander("📋 Raw JSON"):
            st.json(bal_data)
    else:
        st.caption("Nhấn **Tải số dư** để xem thông tin tài sản.")
