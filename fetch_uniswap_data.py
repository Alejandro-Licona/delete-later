"""
Uniswap V4 Pool Data Fetcher (via GeckoTerminal / CoinGecko)
Fetches: current pool snapshot (TVL, fee rate) + historical OHLCV (volume)
Calculates fee APY = (daily_volume * fee_rate / TVL) * 365
Saves per-pool OHLCV CSVs + combined summary to data/uniswap/.
"""

import os
import time
import requests
import pandas as pd
from datetime import datetime, timezone
from config import (
    COINGECKO_API_KEY, COINGECKO_BASE_URL,
    UNISWAP_POOLS, START_DATE, END_DATE, UNISWAP_DATA_DIR
)

os.makedirs(UNISWAP_DATA_DIR, exist_ok=True)

HEADERS = {
    "Accept": "application/json",
    "x-cg-demo-api-key": COINGECKO_API_KEY,
}

# Unix timestamps for date range
_START_TS = int(datetime.fromisoformat(START_DATE.replace("Z", "+00:00")).timestamp())
_END_TS = int(datetime.fromisoformat(END_DATE.replace("Z", "+00:00")).timestamp())
_PERIOD_DAYS = (_END_TS - _START_TS) // 86400


def fetch_pool_snapshot(network_id: str, address: str) -> dict | None:
    """Fetch current pool snapshot: TVL, fee rate, 24h volume, name."""
    url = f"{COINGECKO_BASE_URL}/networks/{network_id}/pools/{address}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        attr = resp.json()["data"]["attributes"]
        return {
            "name": attr.get("name", ""),
            "pool_name": attr.get("pool_name", ""),
            "fee_pct": float(attr.get("pool_fee_percentage", 0)),
            "tvl_usd": float(attr.get("reserve_in_usd", 0)),
            "volume_24h_usd": float(attr.get("volume_usd", {}).get("h24", 0)),
            "pool_created_at": attr.get("pool_created_at", ""),
        }
    except requests.HTTPError as e:
        print(f"    Snapshot HTTP {e.response.status_code} for {address[:20]}...")
        return None
    except Exception as e:
        print(f"    Snapshot error: {e}")
        return None


def fetch_pool_ohlcv(network_id: str, address: str) -> pd.DataFrame:
    """
    Fetch daily OHLCV for the pool from START_DATE to END_DATE.
    GeckoTerminal returns most-recent-first; we filter to our window.
    Format: [timestamp_unix, open, high, low, close, volume_usd]
    """
    url = f"{COINGECKO_BASE_URL}/networks/{network_id}/pools/{address}/ohlcv/day"
    params = {
        "aggregate": 1,
        "before_timestamp": _END_TS + 86400,  # day after end to include END_DATE
        "limit": _PERIOD_DAYS + 10,            # slight buffer
        "currency": "usd",
    }
    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        raw = resp.json()["data"]["attributes"]["ohlcv_list"]
        if not raw:
            return pd.DataFrame()
        df = pd.DataFrame(raw, columns=["timestamp_unix", "open", "high", "low", "close", "volume_usd"])
        df["date"] = pd.to_datetime(df["timestamp_unix"], unit="s", utc=True).dt.date
        # Filter to our period
        start_dt = datetime.fromisoformat(START_DATE.replace("Z", "+00:00")).date()
        end_dt = datetime.fromisoformat(END_DATE.replace("Z", "+00:00")).date()
        df = df[(df["date"] >= start_dt) & (df["date"] <= end_dt)].copy()
        df = df.sort_values("date").reset_index(drop=True)
        return df
    except requests.HTTPError as e:
        print(f"    OHLCV HTTP {e.response.status_code} for {address[:20]}...")
        return pd.DataFrame()
    except Exception as e:
        print(f"    OHLCV error: {e}")
        return pd.DataFrame()


def calculate_fee_apy(volume_usd: float, fee_pct: float, tvl_usd: float) -> float | None:
    """
    Fee APY = (daily_volume * fee_rate_decimal * 365) / TVL
    Returns annualized % or None if TVL is zero.
    fee_pct is already in percent form (e.g. 0.3 means 0.3%)
    """
    if tvl_usd <= 0:
        return None
    fee_rate = fee_pct / 100.0
    daily_fees = volume_usd * fee_rate
    return (daily_fees * 365 / tvl_usd) * 100  # as %


def process_pool(chain_name: str, network_id: str, pool: dict) -> dict | None:
    """Fetch snapshot + OHLCV, compute APY, save CSV. Returns summary row."""
    label = pool["label"]
    address = pool["address"]
    pool_name = pool["name"]

    print(f"  {chain_name}/{label}...", end=" ", flush=True)

    # Snapshot for fee rate + current TVL
    snapshot = fetch_pool_snapshot(network_id, address)
    time.sleep(0.4)

    if snapshot is None:
        print("Snapshot failed — skipping.")
        return None

    fee_pct = snapshot["fee_pct"]
    tvl_usd = snapshot["tvl_usd"]

    # Historical OHLCV for volume
    ohlcv_df = fetch_pool_ohlcv(network_id, address)
    time.sleep(0.4)

    if ohlcv_df.empty:
        print("No OHLCV data — saving snapshot only.")
        # Still record the snapshot APY using 24h volume
        snap_apy = calculate_fee_apy(snapshot["volume_24h_usd"], fee_pct, tvl_usd)
        return {
            "chain": chain_name,
            "pool_label": label,
            "pool_address": address,
            "pool_name": snapshot.get("name", label),
            "fee_pct": fee_pct,
            "current_tvl_usd": tvl_usd,
            "ohlcv_days": 0,
            "avg_daily_volume_usd": snapshot["volume_24h_usd"],
            "current_fee_apy_pct": snap_apy,
            "avg_fee_apy_pct": snap_apy,
            "min_fee_apy_pct": snap_apy,
            "max_fee_apy_pct": snap_apy,
            "csv_file": "",
        }

    # Add fee APY column to OHLCV
    ohlcv_df["chain"] = chain_name
    ohlcv_df["pool_label"] = label
    ohlcv_df["pool_address"] = address
    ohlcv_df["fee_pct"] = fee_pct
    ohlcv_df["tvl_usd_snapshot"] = tvl_usd  # snapshot TVL used as proxy
    ohlcv_df["fee_apy_pct"] = ohlcv_df["volume_usd"].apply(
        lambda v: calculate_fee_apy(v, fee_pct, tvl_usd)
    )

    # Save CSV
    filename = f"{chain_name}_{pool_name}_ohlcv.csv"
    filepath = os.path.join(UNISWAP_DATA_DIR, filename)
    ohlcv_df.to_csv(filepath, index=False)

    fee_apy_series = ohlcv_df["fee_apy_pct"].dropna()
    avg_vol = ohlcv_df["volume_usd"].mean()

    print(
        f"OK ({len(ohlcv_df)} days, avg_vol=${avg_vol:,.0f}, "
        f"avg_fee_apy={fee_apy_series.mean():.1f}%)"
    )

    return {
        "chain": chain_name,
        "pool_label": label,
        "pool_address": address,
        "pool_name": snapshot.get("name", label),
        "fee_pct": fee_pct,
        "current_tvl_usd": tvl_usd,
        "ohlcv_days": len(ohlcv_df),
        "avg_daily_volume_usd": round(avg_vol, 0),
        "current_fee_apy_pct": calculate_fee_apy(snapshot["volume_24h_usd"], fee_pct, tvl_usd),
        "avg_fee_apy_pct": round(fee_apy_series.mean(), 2) if len(fee_apy_series) else None,
        "min_fee_apy_pct": round(fee_apy_series.min(), 2) if len(fee_apy_series) else None,
        "max_fee_apy_pct": round(fee_apy_series.max(), 2) if len(fee_apy_series) else None,
        "csv_file": filepath,
    }


def fetch_all_uniswap_pools():
    """Main: fetch and save data for all configured Uniswap V4 pools."""
    summary_rows = []

    for chain_name, chain_config in UNISWAP_POOLS.items():
        network_id = chain_config["network_id"]
        pools = chain_config["pools"]
        print(f"\n{'─'*60}")
        print(f"Chain: {chain_name.upper()} (network={network_id}) — {len(pools)} pools")
        print(f"{'─'*60}")

        for pool in pools:
            row = process_pool(chain_name, network_id, pool)
            if row:
                summary_rows.append(row)

    # Save pool summary
    if summary_rows:
        summary_df = pd.DataFrame(summary_rows)
        summary_path = os.path.join(UNISWAP_DATA_DIR, "pool_summary.csv")
        summary_df.to_csv(summary_path, index=False)
        print(f"\nPool summary saved to {summary_path}")
        print(f"\nSummary — {len(summary_df)} pools:")
        display_cols = ["chain", "pool_label", "fee_pct", "current_tvl_usd",
                        "avg_daily_volume_usd", "avg_fee_apy_pct"]
        print(summary_df[display_cols].to_string(index=False))
    else:
        print("\n[WARN] No pool data collected.")

    return summary_rows


if __name__ == "__main__":
    print("=" * 60)
    print("Uniswap V4 Pool Data Fetcher (via GeckoTerminal)")
    print(f"Period: {START_DATE[:10]} → {END_DATE[:10]}")
    print("=" * 60)
    fetch_all_uniswap_pools()
    print("\nDone.")
