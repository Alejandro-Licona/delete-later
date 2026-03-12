"""
White Star Portfolio — Exclusion Lists
======================================
Markets listed here are excluded from White Star Portfolio allocation
but still appear in the Global data tables for reference.

To add or remove a market, edit the relevant list below and restart the dashboard.

Format: use the market label exactly as it appears in the data
(e.g. the "market" column in pendle_pt_summary.csv or the label in Pendle LP CSVs).
"""

# ─── Pendle PT markets to exclude from White Star Portfolio ──────────────────
# Excludes BOTH the PT position AND the LP position for the listed market.
# Adding a market here drops it from all White Star allocation tabs while
# keeping it visible in the Global Pendle PT/LP data tables.
WS_EXCLUDE_PENDLE_PT: list[str] = [
    "PT-ynRWAx-15OCT2026",    # excluded: RWA exposure, illiquidity concerns
    "PT-msY-9APR2026",   
    "PT-apyUSD-18JUN2026",     # excluded: low secondary market depth
]

# ─── Pendle LP-only exclusions ────────────────────────────────────────────────
# Use this list to exclude a market's LP position only, leaving its PT position
# in the White Star Portfolio. Leave empty if no LP-only exclusions are needed.
WS_EXCLUDE_PENDLE_LP: list[str] = [
    "PT-apyUSD-18JUN2026",
]
