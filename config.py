"""
Strategy Tracker Configuration
White Star Capital - DeFi Yield Desk
Tracks: Uniswap V4 Market Making + Pendle PT/LP Hold-to-Maturity
Period: Jan 1, 2026 – Mar 13, 2026
"""

# ─── Date Range ───────────────────────────────────────────────────────────────
START_DATE = "2026-01-01T00:00:00Z"
END_DATE = "2026-03-13T00:00:00Z"

# ─── API Keys & Base URLs ─────────────────────────────────────────────────────
COINGECKO_API_KEY = "CG-mCzA4y4DKC4cGd7T3dCV2UAt"
COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3/onchain"

PENDLE_BASE_URL = "https://api-v2.pendle.finance/core"
PENDLE_CHAIN_IDS = [1, 42161]  # Ethereum mainnet, Arbitrum

# ─── Uniswap V4 Pools ────────────────────────────────────────────────────────
# Network IDs as used by GeckoTerminal
UNISWAP_POOLS = {
    "mainnet": {
        "network_id": "eth",
        "pools": [
            {"name": "ETH_USDC", "label": "ETH/USDC", "address": "0xdce6394339af00981949f5f3baf27e3610c76326a700af57e4b3e3ae4977f78d"},
            {"name": "ETH_USDT", "label": "ETH/USDT", "address": "0x72331fcb696b0151904c03584b66dc8365bc63f8a144d89a773384e3a579ca73"},
            {"name": "WBTC_USDC", "label": "WBTC/USDC", "address": "0xb98437c7ba28c6590dd4e1cc46aa89eed181f97108e5b6221730d41347bc817f"},
            {"name": "USDC_cbBTC", "label": "USDC/cbBTC", "address": "0x7067a500ad68cf5129b957fa62c97042cddccaa15d16cb91e3720d97971109bb"},
            {"name": "WBTC_USDT", "label": "WBTC/USDT", "address": "0x20c3a15e34e5d88aeba004b0753af69e4f6bea80eae2263f7a92e919cd33cc56"},
        ],
    },
    "arbitrum": {
        "network_id": "arbitrum",
        "pools": [
            {"name": "ETH_USDC", "label": "ETH/USDC", "address": "0x864abca0a6202dba5b8868772308da953ff125b0f95015adbf89aaf579e903a8"},
            {"name": "ETH_USDT", "label": "ETH/USDT", "address": "0xe88bba0ec2fc9091d68344b32b504abcc59f0aa9e1ae2ef048b69bc7ec3f4df8"},
            {"name": "WBTC_USDC", "label": "WBTC/USDC", "address": "0x80c735c5a0222241f211b3edb8df2ccefad94553ec18f1c29143f0399c78f500"},
            {"name": "WBTC_USDT", "label": "WBTC/USDT", "address": "0x41b1e6b28a39199365f5348a2bf71d0f785167e920d05254b3f2efd1b9487db5"},
        ],
    },
    "unichain": {
        "network_id": "unichain",
        "pools": [
            {"name": "ETH_USDC", "label": "ETH/USDC", "address": "0x3258f413c7a88cda2fa8709a589d221a80f6574f63df5a5b6774485d8acc39d9"},
            {"name": "ETH_USDT", "label": "ETH/USDT", "address": "0x04b7dd024db64cfbe325191c818266e4776918cd9eaf021c26949a859e654b16"},
            {"name": "WBTC_USDC", "label": "WBTC/USDC", "address": "0xbd0f3a7cf4cf5f48ebe850474c8c0012fa5fe893ab811a8b8743a52b83aa8939"},
            {"name": "WBTC_USDT", "label": "WBTC/USDT", "address": "0x05dbb214bd7b9461f9c2f6690b612629b65b9f81d7312fdd3e552d2dda85f771"},
        ],
    },
}

# ─── Pendle Markets ───────────────────────────────────────────────────────────
# Selected markets: diversified across stables, ETH, BTC derivatives and RWA.
# Includes markets that expired within the tracking period (for hold-to-maturity PT analysis)
# and markets currently active.
PENDLE_MARKETS = {
    # ── Ethereum Mainnet (chainId=1) ─────────────────────────────────────────
    "ethereum": {
        "chain_id": 1,
        "markets": [
            # ── Expired in tracking period (ideal PT hold-to-maturity) ──
            {
                "address": "0xed81f8ba2941c3979de2265c295748a6b6956567",
                "label": "PT-sUSDE-5FEB2026",
                "underlying": "sUSDe",
                "category": "stablecoin",
                "expiry": "2026-02-05",
                "expired": True,
            },
            {
                "address": "0xaadbc004dacf10e1fdbd87ca1a40ecaf77cc5b02",
                "label": "PT-USDe-5FEB2026",
                "underlying": "USDe",
                "category": "stablecoin",
                "expiry": "2026-02-05",
                "expired": True,
            },
            {
                "address": "0x3d39e4d42b3f6b493ee52ad5a0d8cb222f03f152",
                "label": "PT-iUSD-19FEB2026",
                "underlying": "iUSD",
                "category": "stablecoin",
                "expiry": "2026-02-19",
                "expired": True,
            },
            {
                "address": "0xcdeb0bab0d9188aab00f06410254a4943403c44b",
                "label": "PT-uniBTC-19FEB2026",
                "underlying": "uniBTC",
                "category": "btc",
                "expiry": "2026-02-19",
                "expired": True,
            },
            {
                "address": "0x6d8c4de7071d5aee27fc3a810764e62a4a00ceb9",
                "label": "PT-sNUSD-5MAR2026",
                "underlying": "sNUSD",
                "category": "stablecoin",
                "expiry": "2026-03-05",
                "expired": True,
            },
            # ── Active markets ──
            {
                "address": "0xafb7d6d1e9bca5b675adc9b4f52f0cdfddec9654",
                "label": "PT-srUSDe-2APR2026",
                "underlying": "srUSDe",
                "category": "stablecoin",
                "expiry": "2026-04-02",
                "expired": False,
            },
            {
                "address": "0x3c53fae231ad3c0408a8b6d33138bbff1caec330",
                "label": "PT-apyUSD-18JUN2026",
                "underlying": "apyUSD",
                "category": "stablecoin",
                "expiry": "2026-06-18",
                "expired": False,
            },
            {
                "address": "0x6cb9a013604a567a5834fadd411165b1ca616783",
                "label": "PT-reUSDe-25JUN2026",
                "underlying": "reUSDe",
                "category": "stablecoin",
                "expiry": "2026-06-25",
                "expired": False,
            },
            {
                "address": "0xe2aef2a77a2db2757455d799fb1ceb2a3ea7a04c",
                "label": "PT-msY-9APR2026",
                "underlying": "msY",
                "category": "stablecoin",
                "expiry": "2026-04-09",
                "expired": False,
            },
            {
                "address": "0xfce3f966a131c46a51b896ceea3917bc4c302577",
                "label": "PT-ynRWAx-15OCT2026",
                "underlying": "ynRWAx",
                "category": "rwa",
                "expiry": "2026-10-15",
                "expired": False,
            },
            {
                "address": "0x9f56fbe66110f4a0bc9a6ced9c35c4cfdfefb92f",
                "label": "PT-jrNUSD-28MAY2026",
                "underlying": "jrNUSD",
                "category": "stablecoin",
                "expiry": "2026-05-28",
                "expired": False,
            },
        ],
    },
    # ── Arbitrum (chainId=42161) ─────────────────────────────────────────────
    "arbitrum": {
        "chain_id": 42161,
        "markets": [
            {
                "address": "0x22d95cec2b962c142fff9be88cfc7ef15043419f",
                "label": "PT-thBILL-18JUN2026",
                "underlying": "thBILL",
                "category": "rwa",
                "expiry": "2026-06-18",
                "expired": False,
            },
            {
                "address": "0x8a8a557b90ec79496a18a1f9c9da8bbd7db86fd3",
                "label": "PT-USDai-18JUN2026",
                "underlying": "USDai",
                "category": "stablecoin",
                "expiry": "2026-06-18",
                "expired": False,
            },
            {
                "address": "0xcbf629c8d396b1261f81f55175afa010e94787d8",
                "label": "PT-sUSDai-15OCT2026",
                "underlying": "sUSDai",
                "category": "stablecoin",
                "expiry": "2026-10-15",
                "expired": False,
            },
            {
                "address": "0x46d62a8dede1bf2d0de04f2ed863245cbba5e538",
                "label": "PT-weETH-25JUN2026",
                "underlying": "weETH",
                "category": "eth",
                "expiry": "2026-06-25",
                "expired": False,
            },
            {
                "address": "0xf78452e0f5c0b95fc5dc8353b8cd1e06e53fa25b",
                "label": "PT-wstETH-25JUN2026",
                "underlying": "wstETH",
                "category": "eth",
                "expiry": "2026-06-25",
                "expired": False,
            },
        ],
    },
}

# ─── Data directories ─────────────────────────────────────────────────────────
DATA_DIR = "data"
PENDLE_DATA_DIR = f"{DATA_DIR}/pendle"
UNISWAP_DATA_DIR = f"{DATA_DIR}/uniswap"

# ─── Pendle historical data fields ───────────────────────────────────────────
PENDLE_FIELDS = (
    "timestamp,baseApy,impliedApy,maxApy,underlyingApy,"
    "swapFeeApy,pendleApy,lpRewardApy,ptPrice,lpPrice,tvl,tradingVolume"
)
