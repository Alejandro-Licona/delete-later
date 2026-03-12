"""
Master orchestrator — runs all data fetches then builds the model portfolio.
Re-run at any time to refresh data (will overwrite existing CSVs).
"""

from fetch_pendle_data import fetch_all_pendle_markets
from fetch_uniswap_data import fetch_all_uniswap_pools
from build_model_portfolio import build_model_portfolio

if __name__ == "__main__":
    print("\n" + "█" * 60)
    print("  White Star Capital — Strategy Tracker")
    print("  Step 1/3: Fetch Pendle historical data")
    print("█" * 60)
    fetch_all_pendle_markets()

    print("\n" + "█" * 60)
    print("  Step 2/3: Fetch Uniswap V4 pool data")
    print("█" * 60)
    fetch_all_uniswap_pools()

    print("\n" + "█" * 60)
    print("  Step 3/3: Build model portfolio")
    print("█" * 60)
    build_model_portfolio()
