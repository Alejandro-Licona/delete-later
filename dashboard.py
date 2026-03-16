"""
White Star Capital — DeFi Strategy Tracker Dashboard
Institutional-grade Streamlit dashboard for strategy performance comparison.
"""

import os
import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from ws_exclusions import WS_EXCLUDE_PENDLE_PT, WS_EXCLUDE_PENDLE_LP

# Plotly chart config: use Streamlit theme so charts load reliably on Cloud
_PLOTLY_CHART_CONFIG = {"displayModeBar": True, "responsive": True}

# ─── Page config (must be first Streamlit call) ──────────────────────────────
st.set_page_config(
    page_title="White Star Capital | Strategy Tracker",
    page_icon="⭐",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─── White Star Portfolio threshold — adjust here ────────────────────────────
WS_APY_THRESHOLD = 6.5   # minimum APY (%) for a position to qualify

# ─── Password gate (hardcoded) ───────────────────────────────────────────────
DASHBOARD_PASSWORD = "0xyield"

# ─── Colour palette (strategy colours are theme-agnostic) ────────────────────
# C_WS        = "#1E40AF"   # blue — White Star Portfolio
C_WS = "#FFFFFF"

# C_UNI       = "#6D28D9"   # purple — Uniswap MM
# C_UNI = "#802FFF"
C_UNI = "#7DF9FF"

# C_PENDLE    = "#047857"   # green — Pendle LP
C_PENDLE    = "#2FFF2F"

# C_PT        = "#B45309"   # amber — Pendle PT
C_PT        = "#FF760D"

C_INACTIVE  = "#94A3B8"   # non-qualifying bars (visible but muted)
C_THRESHOLD = "#EF4444"   # red — threshold line

# Light theme (default)
C_BG_LIGHT        = "#F8F9FB"
C_CARD_BG_LIGHT   = "#FFFFFF"
C_TEXT_LIGHT      = "#1A1A2E"
C_SUBTEXT_LIGHT   = "#6B7280"
C_BORDER_LIGHT    = "#E5E7EB"
C_GRID_LIGHT      = "#D1D5DB"
C_AXIS_LIGHT      = "#6B7280"
C_HEADER_LIGHT    = "#0F172A"
C_HEADER_BORDER_LIGHT = "#E5E7EB"

# Dark theme (follows Streamlit dark / system dark)
C_BG_DARK         = "#0E1117"   # Streamlit dark main
C_CARD_BG_DARK    = "#1E293B"
C_TEXT_DARK       = "#F1F5F9"
C_SUBTEXT_DARK    = "#94A3B8"
C_BORDER_DARK     = "#334155"
C_GRID_DARK       = "#475569"
C_AXIS_DARK       = "#94A3B8"
C_HEADER_DARK     = "#F1F5F9"
C_HEADER_BORDER_DARK = "#475569"

DATA_DIR    = "data"
PENDLE_DIR  = f"{DATA_DIR}/pendle"
UNISWAP_DIR = f"{DATA_DIR}/uniswap"


# ─── Data loaders (cached) ────────────────────────────────────────────────────

@st.cache_data
def load_comparison() -> pd.DataFrame:
    path = os.path.join(DATA_DIR, "daily_strategy_comparison.csv")
    if not os.path.exists(path):
        return pd.DataFrame()
    df = pd.read_csv(path, parse_dates=["date"])
    return df.sort_values("date").reset_index(drop=True)


@st.cache_data
def load_pt_summary() -> pd.DataFrame:
    path = os.path.join(DATA_DIR, "pendle_pt_summary.csv")
    if not os.path.exists(path):
        return pd.DataFrame()
    return pd.read_csv(path)


@st.cache_data
def load_pool_summary() -> pd.DataFrame:
    path = os.path.join(UNISWAP_DIR, "pool_summary.csv")
    if not os.path.exists(path):
        return pd.DataFrame()
    return pd.read_csv(path)


@st.cache_data
def load_pendle_metadata() -> pd.DataFrame:
    path = os.path.join(PENDLE_DIR, "markets_metadata.csv")
    if not os.path.exists(path):
        return pd.DataFrame()
    return pd.read_csv(path)


# ─── White Star recomputation ─────────────────────────────────────────────────

def _build_pt_positions(pt_summary: pd.DataFrame, threshold: float) -> list[dict]:
    """Return list of qualifying PT position metadata, honouring WS exclusion list."""
    positions = []
    if pt_summary.empty:
        return positions
    for _, row in pt_summary.iterrows():
        if pd.isna(row.get("entry_implied_apy_pct")):
            continue
        entry_apy = float(row["entry_implied_apy_pct"])
        if entry_apy < threshold:
            continue
        label = str(row.get("market", ""))
        if label in WS_EXCLUDE_PENDLE_PT:
            continue   # excluded from White Star Portfolio
        positions.append({
            "label":      label,
            "chain":      str(row.get("chain", "")),
            "entry_apy":  entry_apy,
            "expiry":     pd.to_datetime(row["expiry"]) if pd.notna(row.get("expiry")) else None,
            "entry_date": pd.to_datetime(row["entry_date"]) if pd.notna(row.get("entry_date")) else None,
        })
    return positions


def compute_ws(
    comparison_df: pd.DataFrame,
    pt_summary: pd.DataFrame,
    threshold: float,
) -> pd.DataFrame:
    """
    Recompute White Star daily aggregate from the comparison CSV.
    Returns one row per active date: portfolio_apy_pct, n_positions, breakdown.
    """
    if comparison_df.empty:
        return pd.DataFrame()

    uni_cols = [c for c in comparison_df.columns
                if c.startswith("uni_") and c.endswith("_apy")
                and "_portfolio_" not in c and "_n_active" not in c]
    lp_cols  = [c for c in comparison_df.columns
                if c.startswith("pendle_lp_") and c.endswith("_apy")
                and "_portfolio_" not in c and "_n_active" not in c]

    pt_positions = _build_pt_positions(pt_summary, threshold)
    rows = []

    # Build set of excluded LP columns — exclude if market is in either LP or PT exclusion
    # list (a Pendle market exclusion covers both its PT and LP positions)
    excluded_lp_cols = set()
    for col in lp_cols:
        # col format: pendle_lp_{chain}_{label}_apy
        s = col.replace("pendle_lp_", "").replace("_apy", "")
        _, market = s.split("_", 1) if "_" in s else (s, s)
        if market in WS_EXCLUDE_PENDLE_LP or market in WS_EXCLUDE_PENDLE_PT:
            excluded_lp_cols.add(col)

    for _, day_row in comparison_df.iterrows():
        date = day_row["date"]
        uni_apys = [day_row[c] for c in uni_cols if pd.notna(day_row[c]) and day_row[c] >= threshold]
        lp_apys  = [day_row[c] for c in lp_cols
                    if c not in excluded_lp_cols and pd.notna(day_row[c]) and day_row[c] >= threshold]
        pt_apys  = []
        for pt in pt_positions:
            if pt["entry_date"] is not None and date < pt["entry_date"]:
                continue
            if pt["expiry"] is not None and date > pt["expiry"]:
                continue
            pt_apys.append(pt["entry_apy"])

        all_apys = uni_apys + lp_apys + pt_apys
        if not all_apys:
            continue
        rows.append({
            "date":              date,
            "portfolio_apy_pct": float(np.mean(all_apys)),
            "n_positions":       len(all_apys),
            "n_uniswap":         len(uni_apys),
            "n_pendle_lp":       len(lp_apys),
            "n_pendle_pt":       len(pt_apys),
            "min_position_apy":  float(np.min(all_apys)),
            "max_position_apy":  float(np.max(all_apys)),
        })

    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values("date").reset_index(drop=True)


def compute_ws_positions(
    comparison_df: pd.DataFrame,
    pt_summary: pd.DataFrame,
    threshold: float,
) -> pd.DataFrame:
    """
    Long-form position-level detail for the White Star Portfolio.
    Returns one row per (date, position) with: date, position, type, apy_pct, weight_pct.
    """
    if comparison_df.empty:
        return pd.DataFrame()

    uni_cols = [c for c in comparison_df.columns
                if c.startswith("uni_") and c.endswith("_apy")
                and "_portfolio_" not in c and "_n_active" not in c]
    lp_cols  = [c for c in comparison_df.columns
                if c.startswith("pendle_lp_") and c.endswith("_apy")
                and "_portfolio_" not in c and "_n_active" not in c]

    # Map column name → readable label
    def uni_label(col):
        # uni_arbitrum_ETH_USDC_apy → arbitrum / ETH/USDC
        parts = col.replace("uni_", "").replace("_apy", "").split("_", 1)
        chain = parts[0]
        pool  = parts[1].replace("_", "/") if len(parts) > 1 else parts[0]
        return chain, pool

    def lp_label(col):
        # pendle_lp_arbitrum_PT-USDai-18JUN2026_apy → arbitrum, PT-USDai-18JUN2026
        s = col.replace("pendle_lp_", "").replace("_apy", "")
        parts = s.split("_", 1)
        chain  = parts[0]
        market = parts[1] if len(parts) > 1 else s
        return chain, market

    pt_positions = _build_pt_positions(pt_summary, threshold)
    rows = []

    for _, day_row in comparison_df.iterrows():
        date = day_row["date"]
        day_positions = []

        # Uniswap
        for col in uni_cols:
            val = day_row[col]
            if pd.notna(val) and val >= threshold:
                chain, pool = uni_label(col)
                day_positions.append({
                    "type":    "Uniswap MM",
                    "chain":   chain,
                    "market":  pool,
                    "apy_pct": round(float(val), 2),
                })

        # Pendle LP
        for col in lp_cols:
            val = day_row[col]
            if pd.notna(val) and val >= threshold:
                chain, market = lp_label(col)
                if market in WS_EXCLUDE_PENDLE_LP or market in WS_EXCLUDE_PENDLE_PT:
                    continue   # excluded from White Star Portfolio
                day_positions.append({
                    "type":    "Pendle LP",
                    "chain":   chain,
                    "market":  market,
                    "apy_pct": round(float(val), 2),
                })

        # Pendle PT
        for pt in pt_positions:
            if pt["entry_date"] is not None and date < pt["entry_date"]:
                continue
            if pt["expiry"] is not None and date > pt["expiry"]:
                continue
            day_positions.append({
                "type":    "Pendle PT",
                "chain":   pt["chain"],
                "market":  pt["label"],
                "apy_pct": round(float(pt["entry_apy"]), 2),
            })

        if not day_positions:
            continue
        n = len(day_positions)
        for pos in day_positions:
            rows.append({
                "Date":       date.strftime("%Y-%m-%d") if hasattr(date, "strftime") else str(date)[:10],
                "Type":       pos["type"],
                "Chain":      pos["chain"],
                "Market":     pos["market"],
                "APY %":      pos["apy_pct"],
                "Weight %":   round(100.0 / n, 2),
            })

    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values(["Date", "Type", "Market"]).reset_index(drop=True)


# ─── Theme detection (Streamlit 1.46+ exposes st.context.theme) ────────────────

def _get_theme() -> str:
    """Return 'light' or 'dark' from Streamlit theme; default 'light' if not available."""
    try:
        return getattr(st.context.theme, "type", "light") or "light"
    except Exception:
        return "light"


def _theme_colors(theme: str) -> dict:
    """Return dict of theme-dependent UI colors (bg, card_bg, text, subtext, border, grid, axis, header, header_border)."""
    if theme == "dark":
        return {
            "bg": C_BG_DARK,
            "card_bg": C_CARD_BG_DARK,
            "text": C_TEXT_DARK,
            "subtext": C_SUBTEXT_DARK,
            "border": C_BORDER_DARK,
            "grid": C_GRID_DARK,
            "axis": C_AXIS_DARK,
            "header": C_HEADER_DARK,
            "header_border": C_HEADER_BORDER_DARK,
        }
    return {
        "bg": C_BG_LIGHT,
        "card_bg": C_CARD_BG_LIGHT,
        "text": C_TEXT_LIGHT,
        "subtext": C_SUBTEXT_LIGHT,
        "border": C_BORDER_LIGHT,
        "grid": C_GRID_LIGHT,
        "axis": C_AXIS_LIGHT,
        "header": C_HEADER_LIGHT,
        "header_border": C_HEADER_BORDER_LIGHT,
    }


def _plotly_layout(theme: str) -> dict:
    """Build Plotly layout dict for the given theme (paper/plot bg and axis colors)."""
    c = _theme_colors(theme)
    paper = c["card_bg"] if theme == "dark" else "white"
    return dict(
        font=dict(family="Inter, sans-serif", size=12, color=c["text"]),
        paper_bgcolor=paper,
        plot_bgcolor=paper,
        margin=dict(l=48, r=24, t=40, b=40),
        legend=dict(
            orientation="h",
            yanchor="bottom", y=1.02,
            xanchor="left", x=0,
            bgcolor="rgba(0,0,0,0)",
            font=dict(size=11, color=c["text"]),
        ),
        hovermode="x unified",
        xaxis=dict(
            showgrid=False, zeroline=False, linecolor=c["axis"],
            tickfont=dict(color=c["axis"], size=11),
            title_font=dict(color=c["axis"], size=12),
        ),
        yaxis=dict(
            showgrid=True, gridcolor=c["grid"], gridwidth=1,
            zeroline=False, linecolor=c["axis"], ticksuffix="%",
            tickfont=dict(color=c["axis"], size=11),
            title_font=dict(color=c["axis"], size=12),
        ),
    )


def fmt_apy(val):
    return f"{val:.1f}%" if pd.notna(val) else "—"


def kpi_card(label: str, value: str, sub: str = "", color: str = C_TEXT_DARK) -> str:
    return f"""
    <div class="kpi-card">
      <div class="kpi-label">{label}</div>
      <div class="kpi-value" style="color:{color}">{value}</div>
      <div class="kpi-sub">{sub}</div>
    </div>"""


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN APP
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    # ─── Password gate ────────────────────────────────────────────────────────
    if st.session_state.get("_dashboard_authenticated") is not True:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown(
            "<h2 style='text-align:center; color:#1E40AF;'>White Star Capital — Strategy Tracker</h2>",
            unsafe_allow_html=True,
        )
        st.markdown("<p style='text-align:center; color:#94A3B8;'>Enter password to continue.</p>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            pwd = st.text_input("Password", type="password", key="dashboard_pwd", label_visibility="collapsed", placeholder="Password")
            submitted = st.button("Unlock")
        if submitted:
            if pwd == DASHBOARD_PASSWORD:
                st.session_state["_dashboard_authenticated"] = True
                st.rerun()
            else:
                st.error("Incorrect password.")
        st.stop()

    threshold = WS_APY_THRESHOLD
    theme = "dark"
    c = _theme_colors(theme)
    plotly_layout = _plotly_layout(theme)
    chart_bg = c["card_bg"] if theme == "dark" else "white"

    # ─── Inject theme-dependent CSS (supports light and dark) ─────────────────
    st.markdown(f"""
    <style>
      html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; }}
      .main {{ background-color: {c["bg"]}; }}

      .kpi-card {{
        background: {c["card_bg"]};
        border: 1px solid {c["border"]};
        border-radius: 10px;
        padding: 20px 24px;
        text-align: center;
        box-shadow: 0 1px 4px rgba(0,0,0,0.06);
      }}
      .kpi-label {{ font-size: 11px; font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase; color: {c["subtext"]}; margin-bottom: 6px; }}
      .kpi-value {{ font-size: 28px; font-weight: 700; color: {c["text"]}; }}
      .kpi-sub {{ font-size: 12px; color: {c["subtext"]}; margin-top: 4px; }}

      .section-header {{ font-size: 16px; font-weight: 700; color: {c["header"]}; margin-top: 8px; margin-bottom: 4px; border-bottom: 2px solid {c["header_border"]}; padding-bottom: 6px; }}

      .footer {{ font-size: 10px; color: {c["subtext"]}; border-top: 1px solid {c["border"]}; padding-top: 12px; margin-top: 24px; line-height: 1.6; }}
    </style>
    """, unsafe_allow_html=True)

    # ── Load data ────────────────────────────────────────────────────────────
    comparison_df = load_comparison()
    pt_summary    = load_pt_summary()
    pool_summary  = load_pool_summary()
    pendle_meta   = load_pendle_metadata()

    if comparison_df.empty:
        st.error("No data found. Run `python run_all.py` first to fetch and build the portfolio data.")
        st.stop()

    period_start = comparison_df["date"].min().strftime("%b %d, %Y")
    period_end   = comparison_df["date"].max().strftime("%b %d, %Y")

    # ── Compute WS portfolio ─────────────────────────────────────────────────
    ws_daily     = compute_ws(comparison_df, pt_summary, threshold)
    ws_positions = compute_ws_positions(comparison_df, pt_summary, threshold)

    # ── Header ───────────────────────────────────────────────────────────────
    st.markdown(f"""
    <h1 style='font-size:26px; font-weight:800; color:{C_WS}; margin-bottom:2px;'>
      White Star Capital — DeFi Strategy Tracker
    </h1>
    <p style='color:{c["subtext"]}; font-size:13px; margin-top:0;'>
      {period_start} &nbsp;→&nbsp; {period_end} &nbsp;·&nbsp;
      Uniswap V4 Market Making &nbsp;·&nbsp; Pendle PT &nbsp;·&nbsp; Pendle LP
    </p>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # ═══════════════════════════════════════════════════════════════════════════
    # KPI Cards
    # ═══════════════════════════════════════════════════════════════════════════

    uni_avg    = comparison_df["uni_portfolio_apy"].mean()
    lp_avg     = comparison_df["pendle_lp_portfolio_apy"].mean()
    pt_avg     = comparison_df["pendle_pt_portfolio_avg_implied_apy"].mean() \
                 if "pendle_pt_portfolio_avg_implied_apy" in comparison_df.columns else None
    ws_avg     = ws_daily["portfolio_apy_pct"].mean() if not ws_daily.empty else None
    ws_days    = len(ws_daily)
    total_days = len(comparison_df)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(kpi_card(
            "White Star Portfolio",
            fmt_apy(ws_avg),
            "Average Daily APY",
            C_WS,
        ), unsafe_allow_html=True)
    with c2:
        st.markdown(kpi_card(
            "Uniswap V4 Market Making",
            fmt_apy(uni_avg),
            "Average Daily APY",
            C_UNI,
        ), unsafe_allow_html=True)
    with c3:
        st.markdown(kpi_card(
            "Pendle LP",
            fmt_apy(lp_avg),
            "Average Daily APY",
            C_PENDLE,
        ), unsafe_allow_html=True)
    with c4:
        st.markdown(kpi_card(
            "Pendle PT (Entry Implied)",
            fmt_apy(pt_avg),
            "Average Daily APY",
            C_PT,
        ), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════════════════════════
    # Section 1 — Portfolio APY Comparison
    # ═══════════════════════════════════════════════════════════════════════════

    st.markdown(
        f'<div class="section-header" style="font-size:17px; font-weight:700; color:{c["header"]}; margin-top:12px; margin-bottom:6px; border-bottom:2px solid {c["header_border"]}; padding-bottom:6px;">Portfolio APY — Strategy Comparison</div>',
        unsafe_allow_html=True,
    )

    fig_compare = go.Figure()

    fig_compare.add_trace(go.Scatter(
        x=comparison_df["date"], y=comparison_df["uni_portfolio_apy"],
        name="Uniswap V4 MM",
        line=dict(color=C_UNI, width=1.8),
        hovertemplate="%{y:.1f}%",
    ))
    fig_compare.add_trace(go.Scatter(
        x=comparison_df["date"], y=comparison_df["pendle_lp_portfolio_apy"],
        name="Pendle LP",
        line=dict(color=C_PENDLE, width=1.8),
        hovertemplate="%{y:.1f}%",
    ))
    if "pendle_pt_portfolio_avg_implied_apy" in comparison_df.columns:
        fig_compare.add_trace(go.Scatter(
            x=comparison_df["date"], y=comparison_df["pendle_pt_portfolio_avg_implied_apy"],
            name="Pendle PT (implied)",
            line=dict(color=C_PT, width=1.8, dash="dot"),
            hovertemplate="%{y:.1f}%",
        ))
    if not ws_daily.empty:
        fig_compare.add_trace(go.Scatter(
            x=ws_daily["date"], y=ws_daily["portfolio_apy_pct"],
            name="White Star Portfolio",
            line=dict(color=C_WS, width=2.8),
            hovertemplate="%{y:.1f}%",
        ))
    fig_compare.update_layout(
        **plotly_layout,
        height=380,
        title=dict(text="", font=dict(size=13, color=c["subtext"]), x=0),
        yaxis_title="APY (%)",
    )
    st.plotly_chart(fig_compare, use_container_width=True, theme="streamlit", config=_PLOTLY_CHART_CONFIG)

    # ═══════════════════════════════════════════════════════════════════════════
    # Section 2 — White Star Composition
    # ═══════════════════════════════════════════════════════════════════════════

    st.markdown(
        f'<div class="section-header" style="font-size:17px; font-weight:700; color:{c["header"]}; margin-top:12px; margin-bottom:6px; border-bottom:2px solid {c["header_border"]}; padding-bottom:6px;">White Star Portfolio — Daily Composition & APY</div>',
        unsafe_allow_html=True,
    )

    if ws_daily.empty:
        st.info("No qualifying positions.")
    else:
        fig_ws = make_subplots(specs=[[{"secondary_y": True}]])

        fig_ws.add_trace(go.Bar(
            x=ws_daily["date"], y=ws_daily["n_uniswap"],
            name="Uniswap MM", marker_color=C_UNI, opacity=0.85,
        ), secondary_y=False)
        fig_ws.add_trace(go.Bar(
            x=ws_daily["date"], y=ws_daily["n_pendle_lp"],
            name="Pendle LP", marker_color=C_PENDLE, opacity=0.85,
        ), secondary_y=False)
        fig_ws.add_trace(go.Bar(
            x=ws_daily["date"], y=ws_daily["n_pendle_pt"],
            name="Pendle PT", marker_color=C_PT, opacity=0.85,
        ), secondary_y=False)
        fig_ws.add_trace(go.Scatter(
            x=ws_daily["date"], y=ws_daily["portfolio_apy_pct"],
            name="Portfolio APY",
            line=dict(color=C_WS, width=2.5),
            hovertemplate="%{y:.1f}%",
        ), secondary_y=True)

        layout_ws = {
            **plotly_layout,
            "barmode": "stack",
            "height": 350,
            "legend": dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, font=dict(size=11, color=c["text"])),
            "title": dict(text="", font=dict(size=13, color=c["subtext"]), x=0),
            "xaxis": dict(showgrid=False, zeroline=False, linecolor=c["axis"], tickfont=dict(color=c["axis"]), title_font=dict(color=c["axis"])),
        }
        fig_ws.update_layout(**layout_ws)
        fig_ws.update_yaxes(title_text="# Qualifying Positions", showgrid=True, gridcolor=c["grid"], linecolor=c["axis"], tickfont=dict(color=c["axis"]), title_font=dict(color=c["axis"]), secondary_y=False)
        fig_ws.update_yaxes(title_text="Portfolio APY (%)", ticksuffix="%", showgrid=False, linecolor=c["axis"], tickfont=dict(color=c["axis"]), title_font=dict(color=c["axis"]), secondary_y=True)
        st.plotly_chart(fig_ws, use_container_width=True, theme="streamlit", config=_PLOTLY_CHART_CONFIG)

    # ═══════════════════════════════════════════════════════════════════════════
    # Section 3 — Pool & Market Performance
    # ═══════════════════════════════════════════════════════════════════════════

    st.markdown(
        f'<div class="section-header" style="font-size:17px; font-weight:700; color:{c["header"]}; margin-top:12px; margin-bottom:6px; border-bottom:2px solid {c["header_border"]}; padding-bottom:6px;">Pool & Market Performance</div>',
        unsafe_allow_html=True,
    )
    col_uni, col_pendle = st.columns(2)

    with col_uni:
        st.markdown(f"<p style='font-weight:600; color:{C_UNI}; font-size:13px;'>Uniswap V4 — Avg Fee APY by Pool</p>", unsafe_allow_html=True)
        if not pool_summary.empty:
            ps = pool_summary.sort_values("avg_fee_apy_pct", ascending=True).tail(20)
            labels = ps.apply(lambda r: f"{r['chain']}/{r['pool_label']}", axis=1).tolist()
            colors = [C_UNI if v >= threshold else C_INACTIVE for v in ps["avg_fee_apy_pct"]]
            fig_u = go.Figure(go.Bar(
                x=ps["avg_fee_apy_pct"], y=labels, orientation="h",
                marker_color=colors,
                text=[f"{v:.1f}%" for v in ps["avg_fee_apy_pct"]], textposition="outside",
            ))
            fig_u.update_layout(
                paper_bgcolor=chart_bg, plot_bgcolor=chart_bg,
                margin=dict(l=0, r=60, t=10, b=40), height=340,
                font=dict(family="Inter, sans-serif", size=11, color=c["axis"]),
                xaxis=dict(showgrid=True, gridcolor=c["grid"], linecolor=c["axis"], tickfont=dict(color=c["axis"]), ticksuffix="%", zeroline=False),
                yaxis=dict(showgrid=False, linecolor=c["axis"], tickfont=dict(color=c["axis"])), showlegend=False,
            )
            st.plotly_chart(fig_u, use_container_width=True, theme="streamlit", config=_PLOTLY_CHART_CONFIG)
        else:
            st.info("Pool summary not found.")

    with col_pendle:
        st.markdown(f"<p style='font-weight:600; color:{C_PENDLE}; font-size:13px;'>Pendle LP — Avg baseApy by Market</p>", unsafe_allow_html=True)
        if not pendle_meta.empty:
            pm = pendle_meta.sort_values("avg_base_lp_apy_pct", ascending=True).tail(20)
            colors_p = [C_PENDLE if v >= threshold else C_INACTIVE for v in pm["avg_base_lp_apy_pct"]]
            fig_p = go.Figure(go.Bar(
                x=pm["avg_base_lp_apy_pct"], y=pm["label"].tolist(), orientation="h",
                marker_color=colors_p,
                text=[f"{v:.1f}%" for v in pm["avg_base_lp_apy_pct"]], textposition="outside",
            ))
            fig_p.update_layout(
                paper_bgcolor=chart_bg, plot_bgcolor=chart_bg,
                margin=dict(l=0, r=80, t=10, b=40), height=340,
                font=dict(family="Inter, sans-serif", size=11, color=c["axis"]),
                xaxis=dict(showgrid=True, gridcolor=c["grid"], linecolor=c["axis"], tickfont=dict(color=c["axis"]), ticksuffix="%", zeroline=False),
                yaxis=dict(showgrid=False, linecolor=c["axis"], tickfont=dict(color=c["axis"])), showlegend=False,
            )
            st.plotly_chart(fig_p, use_container_width=True, theme="streamlit", config=_PLOTLY_CHART_CONFIG)
        else:
            st.info("Pendle metadata not found.")

    # ═══════════════════════════════════════════════════════════════════════════
    # Section 4 — Pendle PT Entry APY
    # ═══════════════════════════════════════════════════════════════════════════

    st.markdown(
        f'<div class="section-header" style="font-size:17px; font-weight:700; color:{c["header"]}; margin-top:12px; margin-bottom:6px; border-bottom:2px solid {c["header_border"]}; padding-bottom:6px;">Pendle PT — Entry Implied APY at Jan 1</div>',
        unsafe_allow_html=True,
    )

    if not pt_summary.empty:
        pt_plot  = pt_summary.dropna(subset=["entry_implied_apy_pct"]).sort_values("entry_implied_apy_pct", ascending=True)
        pt_cols  = [C_PT if v >= threshold else C_INACTIVE for v in pt_plot["entry_implied_apy_pct"]]
        fig_pt   = go.Figure(go.Bar(
            x=pt_plot["entry_implied_apy_pct"], y=pt_plot["market"],
            orientation="h", marker_color=pt_cols,
            text=[f"{v:.1f}%" for v in pt_plot["entry_implied_apy_pct"]], textposition="outside",
        ))
        fig_pt.update_layout(
            paper_bgcolor=chart_bg, plot_bgcolor=chart_bg,
            margin=dict(l=0, r=80, t=10, b=40),
            height=max(280, len(pt_plot) * 28),
            font=dict(family="Inter, sans-serif", size=11, color=c["axis"]),
            xaxis=dict(showgrid=True, gridcolor=c["grid"], linecolor=c["axis"], tickfont=dict(color=c["axis"]), ticksuffix="%", zeroline=False),
            yaxis=dict(showgrid=False, linecolor=c["axis"], tickfont=dict(color=c["axis"])), showlegend=False,
        )
        st.plotly_chart(fig_pt, use_container_width=True, theme="streamlit", config=_PLOTLY_CHART_CONFIG)

    # ═══════════════════════════════════════════════════════════════════════════
    # Section 5 — Data Tables
    # ═══════════════════════════════════════════════════════════════════════════

    st.markdown(
        f'<div class="section-header" style="font-size:17px; font-weight:700; color:{c["header"]}; margin-top:12px; margin-bottom:6px; border-bottom:2px solid {c["header_border"]}; padding-bottom:6px;">Daily Data Tables</div>',
        unsafe_allow_html=True,
    )

    tab_ws, tab_alloc, tab_uni, tab_lp, tab_pt = st.tabs([
        "White Star Detail",
        "Daily Allocations",
        "Global Uniswap Pools",
        "Global Pendle LP Markets",
        "Global Pendle PT Markets",
    ])

    # ── Tab 1: White Star Detail ──────────────────────────────────────────────
    with tab_ws:
        if not ws_daily.empty:
            ws_disp = ws_daily.copy()
            ws_disp["date"] = ws_disp["date"].dt.strftime("%Y-%m-%d")
            ws_disp = ws_disp.rename(columns={
                "date":              "Date",
                "portfolio_apy_pct": "Portfolio APY %",
                "n_positions":       "# Positions",
                "n_uniswap":         "# Uni",
                "n_pendle_lp":       "# LP",
                "n_pendle_pt":       "# PT",
                "min_position_apy":  "Min APY %",
                "max_position_apy":  "Max APY %",
            })
            for col in ["Portfolio APY %", "Min APY %", "Max APY %"]:
                if col in ws_disp.columns:
                    ws_disp[col] = ws_disp[col].round(2)
            st.dataframe(ws_disp, use_container_width=True, height=420)
        else:
            st.info("No qualifying positions.")

    # ── Tab 2: Daily Allocations ──────────────────────────────────────────────
    with tab_alloc:
        if not ws_positions.empty:
            st.caption(
                "Position-level detail for qualifying days. "
                "Equal-weighted allocation — each position receives 100% ÷ # positions that day."
            )
            # Colour-code type column with a style map
            type_color_map = {
                "Uniswap MM": C_UNI,
                "Pendle LP":  C_PENDLE,
                "Pendle PT":  C_PT,
            }
            st.dataframe(
                ws_positions,
                use_container_width=True,
                height=480,
                column_config={
                    "APY %":    st.column_config.NumberColumn("APY %",    format="%.2f%%"),
                    "Weight %": st.column_config.NumberColumn("Weight %", format="%.2f%%"),
                },
            )
        else:
            st.info("No qualifying positions.")

    # ── Tab 3: Global Uniswap Pools ───────────────────────────────────────────
    with tab_uni:
        uni_pool_cols = [c for c in comparison_df.columns
                         if c.startswith("uni_") and c.endswith("_apy") and "_portfolio_" not in c]
        uni_tab = comparison_df[["date"] + uni_pool_cols].copy()
        uni_tab["date"] = uni_tab["date"].dt.strftime("%Y-%m-%d")
        uni_tab.columns = [
            c.replace("uni_", "").replace("_apy", " APY %").replace("_", "/", 2) if c != "date" else "Date"
            for c in uni_tab.columns
        ]
        st.dataframe(uni_tab, use_container_width=True, height=420)

    # ── Tab 4: Global Pendle LP Markets ──────────────────────────────────────
    with tab_lp:
        lp_cols_tab = [c for c in comparison_df.columns
                       if c.startswith("pendle_lp_") and c.endswith("_apy") and "_portfolio_" not in c]
        lp_tab = comparison_df[["date"] + lp_cols_tab].copy()
        lp_tab["date"] = lp_tab["date"].dt.strftime("%Y-%m-%d")
        lp_tab.columns = [
            c.replace("pendle_lp_", "").replace("_apy", " APY %") if c != "date" else "Date"
            for c in lp_tab.columns
        ]
        st.dataframe(lp_tab, use_container_width=True, height=420)

    # ── Tab 5: Global Pendle PT Markets ──────────────────────────────────────
    with tab_pt:
        if not pt_summary.empty:
            pt_disp = pt_summary[[
                "chain", "market", "underlying", "category", "expiry",
                "expired_in_period", "entry_date",
                "entry_implied_apy_pct", "entry_underlying_apy_pct",
            ]].copy()
            pt_disp["qualifies"] = pt_disp["entry_implied_apy_pct"] >= threshold
            pt_disp["ws_excluded"] = pt_disp["market"].isin(WS_EXCLUDE_PENDLE_PT)
            pt_disp = pt_disp.sort_values("entry_implied_apy_pct", ascending=False)
            st.dataframe(
                pt_disp, use_container_width=True, height=420,
                column_config={
                    "entry_implied_apy_pct":    st.column_config.NumberColumn("Entry Implied APY %", format="%.2f%%"),
                    "entry_underlying_apy_pct": st.column_config.NumberColumn("Entry Underlying APY %", format="%.2f%%"),
                    "qualifies":                st.column_config.CheckboxColumn("In portfolio"),
                    "ws_excluded":              st.column_config.CheckboxColumn("WS Excluded"),
                },
            )
        else:
            st.info("PT summary not found.")

if __name__ == "__main__":
    main()
