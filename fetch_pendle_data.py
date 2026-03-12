"""
Pendle Historical Data Fetcher
Fetches historical APY and price data for tracked PT/LP markets.
Saves per-market CSVs + combined metadata CSV to data/pendle/.
"""

import os
import time
import requests
import pandas as pd
from config import (
    PENDLE_BASE_URL, PENDLE_MARKETS, PENDLE_FIELDS,
    START_DATE, END_DATE, PENDLE_DATA_DIR
)

os.makedirs(PENDLE_DATA_DIR, exist_ok=True)

HEADERS = {"Accept": "application/json"}


def fetch_market_historical(chain_id: int, address: str, start: str, end: str) -> list[dict]:
    """Fetch daily historical data for a Pendle market."""
    url = f"{PENDLE_BASE_URL}/v2/{chain_id}/markets/{address}/historical-data"
    params = {
        "time_frame": "day",
        "timestamp_start": start,
        "timestamp_end": end,
        "fields": PENDLE_FIELDS,
    }
    resp = requests.get(url, params=params, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    data = resp.json()
    return data.get("results", [])


def save_market_csv(chain_name: str, market: dict, records: list[dict]) -> str:
    """Save market historical data to CSV. Returns the file path."""
    label = market["label"].replace("/", "_").replace(" ", "_")
    filename = f"{chain_name}_{label}.csv"
    filepath = os.path.join(PENDLE_DATA_DIR, filename)

    if not records:
        print(f"  [WARN] No data for {market['label']} — skipping CSV write.")
        return ""

    df = pd.DataFrame(records)
    df["chain"] = chain_name
    df["market_address"] = market["address"]
    df["label"] = market["label"]
    df["underlying"] = market["underlying"]
    df["category"] = market["category"]
    df["expiry"] = market["expiry"]
    df["expired_in_period"] = market["expired"]

    # Convert APY columns from decimal to percentage
    apy_cols = [c for c in df.columns if "apy" in c.lower() or "apr" in c.lower()]
    for col in apy_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce") * 100

    df["tvl"] = pd.to_numeric(df.get("tvl", 0), errors="coerce")
    df["ptPrice"] = pd.to_numeric(df.get("ptPrice", None), errors="coerce")
    df["lpPrice"] = pd.to_numeric(df.get("lpPrice", None), errors="coerce")
    df["tradingVolume"] = pd.to_numeric(df.get("tradingVolume", 0), errors="coerce")

    df.to_csv(filepath, index=False)
    return filepath


def fetch_all_pendle_markets():
    """Main: fetch and save historical data for all configured Pendle markets."""
    metadata_rows = []

    for chain_name, chain_config in PENDLE_MARKETS.items():
        chain_id = chain_config["chain_id"]
        markets = chain_config["markets"]
        print(f"\n{'─'*60}")
        print(f"Chain: {chain_name.upper()} (id={chain_id}) — {len(markets)} markets")
        print(f"{'─'*60}")

        for market in markets:
            label = market["label"]
            address = market["address"]
            print(f"  Fetching {label}...", end=" ", flush=True)

            try:
                records = fetch_market_historical(chain_id, address, START_DATE, END_DATE)
                filepath = save_market_csv(chain_name, market, records)

                if records:
                    df_tmp = pd.DataFrame(records)
                    apy_cols = [c for c in df_tmp.columns if "apy" in c.lower()]
                    tvl_vals = pd.to_numeric(df_tmp.get("tvl", pd.Series([0])), errors="coerce")
                    implied_vals = pd.to_numeric(df_tmp.get("impliedApy", pd.Series([0])), errors="coerce")
                    base_vals = pd.to_numeric(df_tmp.get("baseApy", pd.Series([0])), errors="coerce")
                    # Clip outliers so bad API values (e.g. PT-jrNUSD early days) cannot blow up avg
                    base_vals = base_vals.clip(upper=2.0)  # 200% max in decimal form

                    meta = {
                        "chain": chain_name,
                        "label": label,
                        "address": address,
                        "underlying": market["underlying"],
                        "category": market["category"],
                        "expiry": market["expiry"],
                        "expired_in_period": market["expired"],
                        "data_points": len(records),
                        "date_start": df_tmp["timestamp"].min() if "timestamp" in df_tmp.columns else "",
                        "date_end": df_tmp["timestamp"].max() if "timestamp" in df_tmp.columns else "",
                        "avg_tvl_usd": round(tvl_vals.mean(), 0),
                        "max_tvl_usd": round(tvl_vals.max(), 0),
                        "avg_implied_apy_pct": round(implied_vals.mean() * 100, 2),
                        "avg_base_lp_apy_pct": round(base_vals.mean() * 100, 2),
                        "entry_implied_apy_pct": round(float(implied_vals.iloc[0]) * 100, 2) if len(implied_vals) else None,
                        "csv_file": filepath,
                    }
                    metadata_rows.append(meta)
                    print(f"OK ({len(records)} days, avg_tvl=${tvl_vals.mean():,.0f})")
                else:
                    print("No data returned.")

            except requests.HTTPError as e:
                print(f"HTTP Error {e.response.status_code}: {e}")
            except Exception as e:
                print(f"Error: {e}")

            time.sleep(0.3)  # rate limit courtesy

    # Save metadata summary
    if metadata_rows:
        meta_df = pd.DataFrame(metadata_rows)
        meta_path = os.path.join(PENDLE_DATA_DIR, "markets_metadata.csv")
        meta_df.to_csv(meta_path, index=False)
        print(f"\nMetadata saved to {meta_path}")
        print(f"\nSummary — {len(meta_df)} markets fetched:")
        print(meta_df[["chain","label","data_points","avg_tvl_usd","entry_implied_apy_pct","avg_base_lp_apy_pct"]].to_string(index=False))
    else:
        print("\n[WARN] No market data collected.")

    return metadata_rows


if __name__ == "__main__":
    print("=" * 60)
    print("Pendle Historical Data Fetcher")
    print(f"Period: {START_DATE[:10]} → {END_DATE[:10]}")
    print("=" * 60)
    fetch_all_pendle_markets()
    print("\nDone.")
