"""
Model Portfolio Builder
Loads saved Pendle and Uniswap CSVs and builds equal-weighted model portfolios.

Strategy 1 — Uniswap V4 Market Making:
  - Tracks fee APY per pool per day
  - Equal-weighted across pools with available data
  - APY = (daily_volume * fee_rate / TVL) * 365

Strategy 2a — Pendle PT Hold-to-Maturity:
  - Entry APY = implied APY on Jan 1 (or first available data point)
  - Fixed yield locked in at entry; does not change with market
  - Shows which markets would have given best fixed-income return

Strategy 2b — Pendle LP Provision:
  - Tracks baseApy (swap fees + underlying + Pendle rewards, no boost)
  - Equal-weighted across markets with available data
  - Variable return, shows daily range

Output CSVs and a printed report.
"""

import os
import glob
import pandas as pd
from tabulate import tabulate
from config import PENDLE_DATA_DIR, UNISWAP_DATA_DIR, DATA_DIR, START_DATE, END_DATE

os.makedirs(DATA_DIR, exist_ok=True)

START_DATE_STR = START_DATE[:10]
END_DATE_STR = END_DATE[:10]

from datetime import datetime, timezone
_START_TS = int(datetime.fromisoformat(START_DATE.replace("Z", "+00:00")).timestamp())
_END_TS = int(datetime.fromisoformat(END_DATE.replace("Z", "+00:00")).timestamp())

# Minimum TVL to treat a data point as valid (avoids launch-day APY noise)
MIN_TVL_USD = 50_000


# ──────────────────────────────────────────────────────────────────────────────
# Loaders
# ──────────────────────────────────────────────────────────────────────────────

def load_pendle_data() -> pd.DataFrame:
    """Load all per-market Pendle CSVs (excluding metadata)."""
    pattern = os.path.join(PENDLE_DATA_DIR, "*.csv")
    files = [f for f in glob.glob(pattern) if "metadata" not in f]
    if not files:
        print("[WARN] No Pendle CSVs found. Run fetch_pendle_data.py first.")
        return pd.DataFrame()
    frames = []
    for f in files:
        try:
            df = pd.read_csv(f, parse_dates=["timestamp"])
            frames.append(df)
        except Exception as e:
            print(f"  [WARN] Could not load {f}: {e}")
    if not frames:
        return pd.DataFrame()
    combined = pd.concat(frames, ignore_index=True)
    combined["date"] = combined["timestamp"].dt.date
    combined["date"] = pd.to_datetime(combined["date"])
    return combined


def load_uniswap_data() -> pd.DataFrame:
    """Load all per-pool Uniswap OHLCV CSVs (excluding summary)."""
    pattern = os.path.join(UNISWAP_DATA_DIR, "*_ohlcv.csv")
    files = glob.glob(pattern)
    if not files:
        print("[WARN] No Uniswap OHLCV CSVs found. Run fetch_uniswap_data.py first.")
        return pd.DataFrame()
    frames = []
    for f in files:
        try:
            df = pd.read_csv(f, parse_dates=["date"])
            frames.append(df)
        except Exception as e:
            print(f"  [WARN] Could not load {f}: {e}")
    if not frames:
        return pd.DataFrame()
    combined = pd.concat(frames, ignore_index=True)
    combined["date"] = pd.to_datetime(combined["date"])
    return combined


# ──────────────────────────────────────────────────────────────────────────────
# Strategy 1 — Uniswap V4 Market Making
# ──────────────────────────────────────────────────────────────────────────────

def build_uniswap_strategy(uni_df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute daily equal-weighted portfolio APY across all Uniswap pools.
    Returns daily portfolio APY time series.
    """
    if uni_df.empty:
        return pd.DataFrame()

    # Per-pool daily APY is already in fee_apy_pct
    # Equal weight: average APY across all pools with data on each day
    daily = (
        uni_df.groupby("date")["fee_apy_pct"]
        .agg(["mean", "min", "max", "count"])
        .reset_index()
        .rename(columns={"mean": "portfolio_fee_apy_pct", "count": "active_pools"})
    )
    daily["strategy"] = "Uniswap_V4_MM"
    return daily


def build_uniswap_pool_summary(uni_df: pd.DataFrame) -> pd.DataFrame:
    """Per-pool summary over the full period."""
    if uni_df.empty:
        return pd.DataFrame()
    summary = (
        uni_df.groupby(["chain", "pool_label", "fee_pct"])["fee_apy_pct"]
        .agg(avg="mean", med="median", lo="min", hi="max", n="count")
        .reset_index()
        .sort_values("avg", ascending=False)
    )
    summary.columns = ["chain", "pool", "fee_pct_%", "avg_apy_%", "median_apy_%",
                        "min_apy_%", "max_apy_%", "days_data"]
    return summary


# ──────────────────────────────────────────────────────────────────────────────
# Strategy 2a — Pendle PT Hold-to-Maturity
# ──────────────────────────────────────────────────────────────────────────────

def build_pendle_pt_strategy(pendle_df: pd.DataFrame) -> pd.DataFrame:
    """
    For each market, extract the entry implied APY (first data point on or after START_DATE).
    This represents the fixed yield locked in by buying PT on Jan 1.
    """
    if pendle_df.empty:
        return pd.DataFrame()

    rows = []
    for (chain, label), grp in pendle_df.groupby(["chain", "label"]):
        grp = grp.sort_values("date")
        if grp.empty:
            continue
        entry = grp.iloc[0]
        underlying = grp["underlying"].iloc[0] if "underlying" in grp.columns else ""
        category = grp["category"].iloc[0] if "category" in grp.columns else ""
        expiry = grp["expiry"].iloc[0] if "expiry" in grp.columns else ""
        expired = grp["expired_in_period"].iloc[0] if "expired_in_period" in grp.columns else False

        entry_date = entry["date"]
        entry_implied_apy = entry.get("impliedApy", None)
        entry_underlying_apy = entry.get("underlyingApy", None)

        # If market expired in period, the actual hold return = implied APY at entry
        # (PT accretes to par regardless of intermediate price)
        avg_tvl = grp["tvl"].mean() if "tvl" in grp.columns else None
        avg_implied = grp["impliedApy"].mean() if "impliedApy" in grp.columns else None

        rows.append({
            "chain": chain,
            "market": label,
            "underlying": underlying,
            "category": category,
            "expiry": expiry,
            "expired_in_period": expired,
            "entry_date": str(entry_date)[:10],
            "entry_implied_apy_pct": round(float(entry_implied_apy), 2) if entry_implied_apy is not None else None,
            "entry_underlying_apy_pct": round(float(entry_underlying_apy), 2) if entry_underlying_apy is not None else None,
            "avg_implied_apy_pct": round(float(avg_implied), 2) if avg_implied is not None else None,
            "avg_tvl_usd": round(float(avg_tvl), 0) if avg_tvl is not None else None,
            "data_days": len(grp),
        })

    df = pd.DataFrame(rows).sort_values("entry_implied_apy_pct", ascending=False)
    return df


# ──────────────────────────────────────────────────────────────────────────────
# Strategy 2b — Pendle LP Provision
# ──────────────────────────────────────────────────────────────────────────────

def build_pendle_lp_strategy(pendle_df: pd.DataFrame) -> pd.DataFrame:
    """
    Equal-weighted daily LP APY across all tracked Pendle markets.
    baseApy = swapFeeApy + underlyingApy + pendleApy (no veBoost).
    """
    if pendle_df.empty:
        return pd.DataFrame()

    daily = (
        pendle_df.groupby("date")["baseApy"]
        .agg(["mean", "min", "max", "count"])
        .reset_index()
        .rename(columns={"mean": "portfolio_lp_apy_pct", "count": "active_markets"})
    )
    daily["strategy"] = "Pendle_LP"
    return daily


def build_pendle_lp_market_summary(pendle_df: pd.DataFrame) -> pd.DataFrame:
    """Per-market LP APY summary."""
    if pendle_df.empty:
        return pd.DataFrame()
    summary = (
        pendle_df.groupby(["chain", "label", "underlying", "category"])["baseApy"]
        .agg(avg="mean", med="median", lo="min", hi="max", n="count")
        .reset_index()
        .sort_values("avg", ascending=False)
    )
    summary.columns = ["chain", "market", "underlying", "category",
                        "avg_lp_apy_%", "median_lp_apy_%", "min_lp_apy_%", "max_lp_apy_%", "days_data"]
    return summary


# ──────────────────────────────────────────────────────────────────────────────
# White Star Portfolio — APY ≥ 14% threshold filter
# ──────────────────────────────────────────────────────────────────────────────

WS_APY_THRESHOLD = 14.0  # default minimum APY (%) to qualify for capital allocation


def build_ws_portfolio(uni_df: pd.DataFrame, pendle_df: pd.DataFrame, threshold: float = WS_APY_THRESHOLD) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    White Star Portfolio: equal-weight only positions clearing the APY threshold each day.

    Position types:
      - Uniswap pool-day: qualifies if fee_apy_pct >= threshold on that day
      - Pendle LP market-day: qualifies if baseApy >= threshold on that day
      - Pendle PT market: qualifies if entry implied APY >= threshold;
          contributes its fixed entry APY every day until expiry

    Returns:
      (daily_df, positions_df)
      daily_df    — one row per date: portfolio APY, position count, breakdown
      positions_df — long-form of all qualifying position-days
    """
    position_rows = []

    # ── 1. Uniswap qualifying pool-days ──────────────────────────────────────
    if not uni_df.empty:
        uni_q = uni_df[uni_df["fee_apy_pct"] >= threshold].copy()
        uni_q["position_type"] = "Uniswap_MM"
        uni_q["apy_pct"] = uni_q["fee_apy_pct"]
        uni_q["position_id"] = uni_q["chain"] + " " + uni_q["pool_label"]
        position_rows.append(uni_q[["date", "position_id", "position_type", "apy_pct"]])

    # ── 2. Pendle LP qualifying market-days ──────────────────────────────────
    if not pendle_df.empty:
        lp_q = pendle_df[pendle_df["baseApy"] >= threshold].copy()
        lp_q["position_type"] = "Pendle_LP"
        lp_q["apy_pct"] = lp_q["baseApy"]
        lp_q["position_id"] = lp_q["chain"] + " " + lp_q["label"]
        position_rows.append(lp_q[["date", "position_id", "position_type", "apy_pct"]])

    # ── 3. Pendle PT qualifying markets (fixed APY, active until expiry) ─────
    if not pendle_df.empty:
        # Get all trading dates in the dataset
        all_dates = pd.to_datetime(sorted(pendle_df["date"].unique()))

        for (chain, label), grp in pendle_df.groupby(["chain", "label"]):
            grp = grp.sort_values("date")
            if grp.empty:
                continue
            entry_implied = float(grp.iloc[0].get("impliedApy", 0))
            if entry_implied < threshold:
                continue  # doesn't qualify

            expiry_str = grp["expiry"].iloc[0] if "expiry" in grp.columns else None
            expiry_date = pd.to_datetime(expiry_str) if expiry_str else all_dates[-1]

            # PT is active from first data point through expiry (or end of period)
            first_date = grp["date"].min()
            active_dates = all_dates[(all_dates >= first_date) & (all_dates <= expiry_date)]

            for d in active_dates:
                position_rows.append(pd.DataFrame([{
                    "date": d,
                    "position_id": f"{chain} {label}",
                    "position_type": "Pendle_PT",
                    "apy_pct": entry_implied,
                }]))

    if not position_rows:
        return pd.DataFrame(), pd.DataFrame()

    positions_df = pd.concat(position_rows, ignore_index=True)
    positions_df["date"] = pd.to_datetime(positions_df["date"])
    positions_df = positions_df.sort_values(["date", "position_id"])

    # ── Daily portfolio: equal-weight across all qualifying positions ─────────
    daily_agg = (
        positions_df.groupby("date")
        .agg(
            portfolio_apy_pct=("apy_pct", "mean"),
            n_positions=("position_id", "count"),
            n_uniswap=("position_type", lambda x: (x == "Uniswap_MM").sum()),
            n_pendle_lp=("position_type", lambda x: (x == "Pendle_LP").sum()),
            n_pendle_pt=("position_type", lambda x: (x == "Pendle_PT").sum()),
            min_position_apy=("apy_pct", "min"),
            max_position_apy=("apy_pct", "max"),
        )
        .reset_index()
        .sort_values("date")
    )

    return daily_agg, positions_df


def build_ws_position_summary(positions_df: pd.DataFrame) -> pd.DataFrame:
    """Per-position summary: how many days it qualified and its avg APY."""
    if positions_df.empty:
        return pd.DataFrame()
    summary = (
        positions_df.groupby(["position_id", "position_type"])["apy_pct"]
        .agg(days_qualified="count", avg_apy="mean", min_apy="min", max_apy="max")
        .reset_index()
        .sort_values("avg_apy", ascending=False)
    )
    return summary


# ──────────────────────────────────────────────────────────────────────────────
# Daily Comparison CSV
# ──────────────────────────────────────────────────────────────────────────────

def build_daily_comparison(
    uni_df: pd.DataFrame,
    pendle_df: pd.DataFrame,
    ws_daily: pd.DataFrame,
) -> pd.DataFrame:
    """
    Build a single wide-format daily comparison CSV with one row per date.

    Column groups:
      1. Uniswap MM  — portfolio avg + per-pool daily fee APY
      2. Pendle LP   — portfolio avg + per-market daily baseApy
      3. Pendle PT   — per-market daily implied APY (current market rate) + WS-qualifying flag
      4. White Star  — portfolio APY + position counts by type
    """
    # ── Master date index ────────────────────────────────────────────────────
    all_dates = set()
    if not uni_df.empty:
        all_dates |= set(uni_df["date"].unique())
    if not pendle_df.empty:
        all_dates |= set(pendle_df["date"].unique())
    idx = pd.DataFrame({"date": sorted(pd.to_datetime(list(all_dates)))})

    # ── 1. Uniswap: portfolio avg ─────────────────────────────────────────────
    if not uni_df.empty:
        uni_port = (
            uni_df.groupby("date")["fee_apy_pct"]
            .agg(uni_portfolio_apy=("mean"), uni_n_active_pools=("count"))
            .reset_index()
        )
        idx = idx.merge(uni_port, on="date", how="left")

        # Per-pool columns: uni_{chain}_{pool_name}_apy
        for _, pool_day in uni_df.groupby(["chain", "pool_label"]):
            break  # just checking structure
        pool_pivot = uni_df.pivot_table(
            index="date", columns=["chain", "pool_label"],
            values="fee_apy_pct", aggfunc="mean"
        )
        pool_pivot.columns = [
            f"uni_{chain}_{pool.replace('/', '_')}_apy"
            for chain, pool in pool_pivot.columns
        ]
        pool_pivot = pool_pivot.reset_index()
        idx = idx.merge(pool_pivot, on="date", how="left")

    # ── 2. Pendle LP: portfolio avg ───────────────────────────────────────────
    if not pendle_df.empty:
        lp_port = (
            pendle_df.groupby("date")["baseApy"]
            .agg(pendle_lp_portfolio_apy="mean", pendle_lp_n_active_markets="count")
            .reset_index()
        )
        idx = idx.merge(lp_port, on="date", how="left")

        # Per-market LP columns: pendle_lp_{chain}_{label}_apy
        lp_pivot = pendle_df.pivot_table(
            index="date", columns=["chain", "label"],
            values="baseApy", aggfunc="mean"
        )
        lp_pivot.columns = [
            f"pendle_lp_{chain}_{label}_apy"
            for chain, label in lp_pivot.columns
        ]
        lp_pivot = lp_pivot.reset_index()
        idx = idx.merge(lp_pivot, on="date", how="left")

    # ── 3. Pendle PT: per-market current implied APY ──────────────────────────
    if not pendle_df.empty:
        pt_pivot = pendle_df.pivot_table(
            index="date", columns=["chain", "label"],
            values="impliedApy", aggfunc="mean"
        )
        pt_pivot.columns = [
            f"pendle_pt_{chain}_{label}_implied_apy"
            for chain, label in pt_pivot.columns
        ]
        pt_pivot = pt_pivot.reset_index()
        idx = idx.merge(pt_pivot, on="date", how="left")

        # Portfolio avg implied APY (across all markets with data that day)
        pt_port = (
            pendle_df.groupby("date")["impliedApy"]
            .agg(pendle_pt_portfolio_avg_implied_apy="mean",
                 pendle_pt_n_markets="count")
            .reset_index()
        )
        idx = idx.merge(pt_port, on="date", how="left")

    # ── 4. White Star Portfolio ────────────────────────────────────────────────
    if not ws_daily.empty:
        ws_cols = ["date", "portfolio_apy_pct", "n_positions",
                   "n_uniswap", "n_pendle_lp", "n_pendle_pt",
                   "min_position_apy", "max_position_apy"]
        ws_merge = ws_daily[ws_cols].rename(columns={
            "portfolio_apy_pct": "ws_portfolio_apy",
            "n_positions": "ws_n_positions",
            "n_uniswap": "ws_n_uniswap_qualifying",
            "n_pendle_lp": "ws_n_pendle_lp_qualifying",
            "n_pendle_pt": "ws_n_pendle_pt_qualifying",
            "min_position_apy": "ws_min_position_apy",
            "max_position_apy": "ws_max_position_apy",
        })
        idx = idx.merge(ws_merge, on="date", how="left")

    idx["date"] = pd.to_datetime(idx["date"]).dt.strftime("%Y-%m-%d")
    idx = idx.sort_values("date").reset_index(drop=True)

    # Round all numeric columns to 2 dp
    num_cols = idx.select_dtypes(include="number").columns
    idx[num_cols] = idx[num_cols].round(2)

    return idx


# ──────────────────────────────────────────────────────────────────────────────
# Combined Portfolio
# ──────────────────────────────────────────────────────────────────────────────

def build_combined_portfolio(uni_daily: pd.DataFrame, pendle_lp_daily: pd.DataFrame) -> pd.DataFrame:
    """50/50 allocation between Uniswap MM and Pendle LP strategies."""
    if uni_daily.empty and pendle_lp_daily.empty:
        return pd.DataFrame()

    frames = []
    if not uni_daily.empty:
        u = uni_daily[["date", "portfolio_fee_apy_pct"]].rename(
            columns={"portfolio_fee_apy_pct": "uniswap_apy_pct"})
        frames.append(u.set_index("date"))
    if not pendle_lp_daily.empty:
        p = pendle_lp_daily[["date", "portfolio_lp_apy_pct"]].rename(
            columns={"portfolio_lp_apy_pct": "pendle_lp_apy_pct"})
        frames.append(p.set_index("date"))

    combined = pd.concat(frames, axis=1).reset_index()

    cols = [c for c in ["uniswap_apy_pct", "pendle_lp_apy_pct"] if c in combined.columns]
    combined["combined_50_50_apy_pct"] = combined[cols].mean(axis=1)
    return combined.sort_values("date")


# ──────────────────────────────────────────────────────────────────────────────
# Report
# ──────────────────────────────────────────────────────────────────────────────

def print_ws_report(
    ws_daily: pd.DataFrame,
    ws_positions: pd.DataFrame,
    ws_position_summary: pd.DataFrame,
    threshold: float = WS_APY_THRESHOLD,
):
    sep = "─" * 70
    total_days = (_END_TS - _START_TS) // 86400 + 1
    active_days = len(ws_daily)

    print(f"\n{'═' * 70}")
    print(f"  WHITE STAR PORTFOLIO  (≥ {threshold}% APY threshold)")
    print(f"  Equal-weight: Uniswap MM + Pendle PT + Pendle LP — qualifying only")
    print(f"{'═' * 70}")

    if ws_daily.empty:
        print("  No qualifying positions found.")
        return

    avg_apy = ws_daily["portfolio_apy_pct"].mean()
    med_apy = ws_daily["portfolio_apy_pct"].median()
    lo_apy = ws_daily["portfolio_apy_pct"].min()
    hi_apy = ws_daily["portfolio_apy_pct"].max()
    avg_pos = ws_daily["n_positions"].mean()
    pct_deployed = active_days / total_days * 100

    print(f"\n  Period coverage : {active_days}/{total_days} days with qualifying positions ({pct_deployed:.0f}%)")
    print(f"  Portfolio APY   : avg={avg_apy:.1f}%  median={med_apy:.1f}%  range=[{lo_apy:.1f}%, {hi_apy:.1f}%]")
    print(f"  Avg positions   : {avg_pos:.1f} per active day")
    print(f"\n  Breakdown — avg daily position count by type:")
    print(f"    Uniswap MM   : {ws_daily['n_uniswap'].mean():.1f}")
    print(f"    Pendle LP    : {ws_daily['n_pendle_lp'].mean():.1f}")
    print(f"    Pendle PT    : {ws_daily['n_pendle_pt'].mean():.1f}")

    print(f"\n{sep}")
    print("  Qualifying Positions — days active & avg APY while qualifying")
    print(sep)
    if not ws_position_summary.empty:
        ws_position_summary["avg_apy"] = ws_position_summary["avg_apy"].round(1)
        ws_position_summary["min_apy"] = ws_position_summary["min_apy"].round(1)
        ws_position_summary["max_apy"] = ws_position_summary["max_apy"].round(1)
        print(tabulate(
            ws_position_summary.rename(columns={
                "position_id": "position",
                "position_type": "type",
                "days_qualified": "days",
                "avg_apy": "avg_%",
                "min_apy": "min_%",
                "max_apy": "max_%",
            }),
            headers="keys", tablefmt="simple", showindex=False
        ))

    print(f"\n{sep}")
    print("  Daily Portfolio Snapshot (first 10 and last 10 active days)")
    print(sep)
    display_cols = ["date", "portfolio_apy_pct", "n_positions", "n_uniswap", "n_pendle_lp", "n_pendle_pt"]
    ws_disp = ws_daily[display_cols].copy()
    ws_disp["date"] = ws_disp["date"].dt.strftime("%Y-%m-%d")
    ws_disp = ws_disp.rename(columns={
        "portfolio_apy_pct": "apy_%",
        "n_positions": "n_pos",
        "n_uniswap": "n_uni",
        "n_pendle_lp": "n_lp",
        "n_pendle_pt": "n_pt",
    })
    ws_disp["apy_%"] = ws_disp["apy_%"].round(1)
    head_tail = pd.concat([ws_disp.head(10), ws_disp.tail(10)]).drop_duplicates()
    print(tabulate(head_tail, headers="keys", tablefmt="simple", showindex=False))


def print_report(
    uni_pool_summary: pd.DataFrame,
    pt_summary: pd.DataFrame,
    lp_market_summary: pd.DataFrame,
    uni_daily: pd.DataFrame,
    pendle_lp_daily: pd.DataFrame,
    combined: pd.DataFrame,
):
    sep = "=" * 70

    print(f"\n{sep}")
    print("  WHITE STAR CAPITAL — DeFi Strategy Tracker YTD Report")
    print(f"  Period: {START_DATE_STR} → {END_DATE_STR}")
    print(sep)

    # ── Strategy 1: Uniswap V4 MM ────────────────────────────────────────────
    print("\n── STRATEGY 1: Uniswap V4 Market Making ──────────────────────────")
    print("Model: Equal-weighted fee APY across all tracked V4 pools.")
    print("Hedge assumption: Delta-neutral (IL hedged out); fee income captured.\n")

    if not uni_pool_summary.empty:
        print(tabulate(uni_pool_summary.round(2), headers="keys", tablefmt="simple", showindex=False))
    if not uni_daily.empty:
        avg = uni_daily["portfolio_fee_apy_pct"].mean()
        med = uni_daily["portfolio_fee_apy_pct"].median()
        lo = uni_daily["portfolio_fee_apy_pct"].min()
        hi = uni_daily["portfolio_fee_apy_pct"].max()
        print(f"\nPortfolio (equal-weight): avg={avg:.1f}%  median={med:.1f}%  range=[{lo:.1f}%, {hi:.1f}%]")

    # ── Strategy 2a: Pendle PT Hold-to-Maturity ──────────────────────────────
    print("\n── STRATEGY 2a: Pendle PT Hold-to-Maturity ───────────────────────")
    print("Model: Enter PT on Jan 1 at implied APY. Hold to expiry for fixed yield.\n")

    if not pt_summary.empty:
        display = pt_summary[["chain", "market", "underlying", "category", "expiry",
                               "expired_in_period", "entry_implied_apy_pct",
                               "entry_underlying_apy_pct", "avg_tvl_usd"]].copy()
        print(tabulate(display, headers="keys", tablefmt="simple", showindex=False))
        mean_pt = pt_summary["entry_implied_apy_pct"].mean()
        print(f"\nAverage entry implied APY across tracked markets: {mean_pt:.2f}%")

    # ── Strategy 2b: Pendle LP ───────────────────────────────────────────────
    print("\n── STRATEGY 2b: Pendle LP Provision ──────────────────────────────")
    print("Model: Equal-weighted baseApy (fees + underlying + Pendle rewards, no boost).\n")

    if not lp_market_summary.empty:
        print(tabulate(lp_market_summary.round(2), headers="keys", tablefmt="simple", showindex=False))
    if not pendle_lp_daily.empty:
        avg = pendle_lp_daily["portfolio_lp_apy_pct"].mean()
        med = pendle_lp_daily["portfolio_lp_apy_pct"].median()
        lo = pendle_lp_daily["portfolio_lp_apy_pct"].min()
        hi = pendle_lp_daily["portfolio_lp_apy_pct"].max()
        print(f"\nPortfolio (equal-weight): avg={avg:.1f}%  median={med:.1f}%  range=[{lo:.1f}%, {hi:.1f}%]")

    # ── Combined Portfolio ───────────────────────────────────────────────────
    print("\n── COMBINED PORTFOLIO (50% Uniswap MM + 50% Pendle LP) ───────────")
    if not combined.empty and "combined_50_50_apy_pct" in combined.columns:
        avg = combined["combined_50_50_apy_pct"].mean()
        med = combined["combined_50_50_apy_pct"].median()
        lo = combined["combined_50_50_apy_pct"].min()
        hi = combined["combined_50_50_apy_pct"].max()
        print(f"  avg={avg:.1f}%  median={med:.1f}%  range=[{lo:.1f}%, {hi:.1f}%]")
    else:
        print("  (Insufficient data for combined view)")

    print(f"\n{sep}")
    print("  Disclaimer: Model portfolio. Assumes delta-neutral hedging for Uniswap.")
    print("  Uniswap APY uses snapshot TVL as proxy (TVL varies intraday).")
    print("  Pendle LP uses baseApy (unboosted). Actual returns may differ.")
    print(sep)


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

def build_model_portfolio(threshold: float = WS_APY_THRESHOLD):
    print("=" * 70)
    print("Model Portfolio Builder")
    print(f"Period: {START_DATE_STR} → {END_DATE_STR}")
    print(f"White Star APY threshold: {threshold}%")
    print("=" * 70)

    # Load data
    print("\nLoading Pendle data...")
    pendle_df = load_pendle_data()
    if not pendle_df.empty:
        before = len(pendle_df)
        pendle_df = pendle_df[pendle_df["tvl"] >= MIN_TVL_USD].copy()
        dropped = before - len(pendle_df)
        if dropped:
            print(f"  Filtered {dropped} rows with TVL < ${MIN_TVL_USD:,} (launch-day noise)")
    print(f"  Loaded {len(pendle_df)} rows from {pendle_df['label'].nunique() if not pendle_df.empty else 0} markets")

    print("Loading Uniswap data...")
    uni_df = load_uniswap_data()
    n_pools = len(uni_df[["chain", "pool_label"]].drop_duplicates()) if not uni_df.empty else 0
    print(f"  Loaded {len(uni_df)} rows from {n_pools} pools")

    # Build strategies
    uni_daily = build_uniswap_strategy(uni_df)
    uni_pool_summary = build_uniswap_pool_summary(uni_df)
    pt_summary = build_pendle_pt_strategy(pendle_df)
    pendle_lp_daily = build_pendle_lp_strategy(pendle_df)
    lp_market_summary = build_pendle_lp_market_summary(pendle_df)
    combined = build_combined_portfolio(uni_daily, pendle_lp_daily)

    # White Star Portfolio
    print(f"Building White Star Portfolio (threshold={threshold}%)...")
    ws_daily, ws_positions = build_ws_portfolio(uni_df, pendle_df, threshold=threshold)
    ws_pos_summary = build_ws_position_summary(ws_positions)

    # Save outputs
    if not uni_daily.empty:
        uni_daily.to_csv(os.path.join(DATA_DIR, "uniswap_daily_portfolio.csv"), index=False)
    if not pendle_lp_daily.empty:
        pendle_lp_daily.to_csv(os.path.join(DATA_DIR, "pendle_lp_daily_portfolio.csv"), index=False)
    if not pt_summary.empty:
        pt_summary.to_csv(os.path.join(DATA_DIR, "pendle_pt_summary.csv"), index=False)
    if not combined.empty:
        combined.to_csv(os.path.join(DATA_DIR, "combined_portfolio.csv"), index=False)
    if not ws_daily.empty:
        ws_daily.to_csv(os.path.join(DATA_DIR, "ws_portfolio_daily.csv"), index=False)
    if not ws_positions.empty:
        ws_positions.to_csv(os.path.join(DATA_DIR, "ws_qualifying_positions.csv"), index=False)

    # Daily comparison across all strategies
    print("Building daily strategy comparison...")
    comparison_df = build_daily_comparison(uni_df, pendle_df, ws_daily)
    if not comparison_df.empty:
        out_path = os.path.join(DATA_DIR, "daily_strategy_comparison.csv")
        comparison_df.to_csv(out_path, index=False)
        print(f"  Saved {len(comparison_df)} rows × {len(comparison_df.columns)} columns → {out_path}")

    print(f"\nOutputs saved to {DATA_DIR}/")

    # Print report
    print_report(uni_pool_summary, pt_summary, lp_market_summary,
                 uni_daily, pendle_lp_daily, combined)
    print_ws_report(ws_daily, ws_positions, ws_pos_summary, threshold=threshold)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Build White Star model portfolio from saved CSV data.")
    parser.add_argument(
        "--threshold", type=float, default=WS_APY_THRESHOLD,
        help=f"Minimum APY (%%) for White Star Portfolio inclusion (default: {WS_APY_THRESHOLD})"
    )
    args = parser.parse_args()
    build_model_portfolio(threshold=args.threshold)
