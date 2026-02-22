"""
FMP API client — free-tier endpoints only.

All functions return plain Python dicts/lists. No Streamlit calls here.
Free plan limits: ~250 calls/day, no premium endpoints.
"""
import requests
import streamlit as st

FMP_BASE = "https://financialmodelingprep.com/api/v3"

# Sector ETF proxies — used to approximate sector performance on the free tier
SECTOR_ETFS = {
    "Technology": "XLK",
    "Financials": "XLF",
    "Energy": "XLE",
    "Health Care": "XLV",
    "Industrials": "XLI",
    "Consumer Discretionary": "XLY",
    "Consumer Staples": "XLP",
    "Utilities": "XLU",
    "Real Estate": "XLRE",
    "Materials": "XLB",
    "Communication Services": "XLC",
}


def _get(endpoint, params=None):
    api_key = st.secrets.get("FMP_API_KEY", "")
    if not api_key:
        raise ValueError("FMP_API_KEY not set in .streamlit/secrets.toml")

    if params is None:
        params = {}
    params["apikey"] = api_key

    response = requests.get(
        f"{FMP_BASE}/{endpoint}",
        params=params,
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def get_sector_performance():
    """
    Approximate sector performance using major sector ETF daily % change.
    Endpoint: /api/v3/quote/{symbols}  (free tier)
    """
    symbols = ",".join(SECTOR_ETFS.values())
    data = _get(f"quote/{symbols}")

    etf_to_sector = {v: k for k, v in SECTOR_ETFS.items()}
    results = []
    for item in data:
        symbol = item.get("symbol")
        if symbol in etf_to_sector:
            results.append({
                "sector": etf_to_sector[symbol],
                "symbol": symbol,
                "price": item.get("price"),
                "change": item.get("change"),
                "changesPercentage": item.get("changesPercentage"),
            })
    return results


def get_gainers():
    """Top gaining stocks. Endpoint: /api/v3/gainers (free tier)"""
    return _get("gainers")


def get_losers():
    """Top losing stocks. Endpoint: /api/v3/losers (free tier)"""
    return _get("losers")


def get_actives():
    """Most active stocks by volume. Endpoint: /api/v3/actives (free tier)"""
    return _get("actives")


def get_stock_news(limit=50):
    """
    Latest stock news. Endpoint: /api/v3/stock_news (free tier, max ~50 items).
    """
    return _get("stock_news", {"limit": limit})
