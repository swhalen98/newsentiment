import streamlit as st
import pandas as pd
import requests
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
from collections import defaultdict

st.set_page_config(page_title="Top Stocks News", page_icon=":chart_with_upwards_trend:", layout="wide")

st.sidebar.markdown("# Top Stocks News")
st.markdown("# Top Stocks News")

st.write("This page will display top 25 stocks by market cap and their top news words.")

# --- FMP API Configuration ---
# IMPORTANT: Replace with your actual FMP API key.
# You can get a free key from https://financialmodelingprep.com/developer/docs
FMP_API_KEY = st.secrets["FMP_API_KEY"] if "FMP_API_KEY" in st.secrets else "YOUR_FMP_API_KEY"

@st.cache_data(ttl=3600)
@retry(
    wait=wait_exponential(multiplier=1, min=4, max=10),
    stop=stop_after_attempt(5),
    retry=retry_if_exception_type(requests.exceptions.RequestException),
    reraise=True,
)
def get_top_stocks_by_market_cap(limit=25):
    """
    Fetches a list of top stocks by market capitalization using the FMP Stock Screener API.
    """
    if FMP_API_KEY == "YOUR_FMP_API_KEY":
        st.error("Please set your FMP_API_KEY in Streamlit secrets or replace the placeholder.")
        return []

    FMP_API_BASE_URL = "https://financialmodelingprep.com/api/v3/stock-screener"

    # Filter for large market cap and sort by market cap in descending order
    # Using a very large marketCapMoreThan to ensure we get large-cap stocks
    params = {
        "marketCapMoreThan": 10000000000, # e.g., > $10 Billion
        "limit": limit * 2, # Fetch more than needed to ensure we get 25 after sorting/filtering
        "sort": "marketCap",
        "exchange": "NASDAQ,NYSE", # Focus on major US exchanges
        "apikey": FMP_API_KEY
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36"
    }

    try:
        response = requests.get(FMP_API_BASE_URL, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        stocks_data = response.json()

        if stocks_data:
            # Sort by marketCap (descending) and take the top 'limit'
            sorted_stocks = sorted(stocks_data, key=lambda x: x.get('marketCap', 0), reverse=True)
            return sorted_stocks[:limit]
        return []
    except requests.exceptions.RequestException as e:
        if hasattr(e, 'response') and e.response is not None and e.response.status_code == 429:
            st.error(f"Rate limited by FMP API: {e}. Retrying...")
            raise  # tenacity will retry on RequestException
        else:
            st.error(f"Error fetching top stocks from FMP API: {e}")
    except ValueError:
        st.error(f"Error parsing JSON response from FMP API: {response.text[:500]}")
    return []

# --- GDELT API Configuration (reusing logic from streamlit_app.py and us_news_map.py) ---
@st.cache_data(ttl=3600)
@retry(
    wait=wait_exponential(multiplier=1, min=4, max=10),
    stop=stop_after_attempt(5),
    retry=retry_if_exception_type(requests.exceptions.RequestException),
    reraise=True,
)
def get_gdelt_news_for_company(company_name, timespan):
    """
    Fetches top news themes for a given company from the GDELT GKG API.
    """
    API_BASE_URL_GKG = "https://api.gdeltproject.org/api/v1/gkg_geojson"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36"
    }

    top_themes = defaultdict(int)
    gkg_params = {
        "query": company_name,
        "timespan": timespan,
        "format": "json", # gkg_geojson returns GeoJSON, but format=json might give a more parsable response for themes
    }

    try:
        response = requests.get(API_BASE_URL_GKG, params=gkg_params, headers=headers, timeout=10)
        response.raise_for_status()
        gkg_data = response.json()

        if 'features' in gkg_data:
            for feature in gkg_data['features']:
                themes_str = feature['properties'].get('mentionedthemes')
                if themes_str:
                    themes = themes_str.split(';')
                    for theme in themes:
                        clean_theme = theme.strip()
                        if clean_theme: # Ensure theme is not empty
                            top_themes[clean_theme] += 1
    except requests.exceptions.RequestException as e:
        if hasattr(e, 'response') and e.response is not None and e.response.status_code == 429:
            st.error(f"Rate limited by GDELT API for themes ({company_name}): {e}. Retrying...")
            raise  # tenacity will retry on RequestException
        else:
            st.error(f"Error fetching themes for {company_name} from GDELT API: {e}")
    except ValueError:
        st.error(f"Error parsing JSON for themes ({company_name}) from GDELT API: {response.text[:500]}")

    # Sort themes by count and get the top ones
    sorted_themes = sorted(top_themes.items(), key=lambda item: item[1], reverse=True)

    # Extract top 3 news words (themes) - each theme is a "word" or phrase
    top_3_themes_text = [theme[0] for theme in sorted_themes[:3]]
    return top_3_themes_text

# --- Main App Logic for Top Stocks News Page ---
st.header('Top 25 Companies by Market Cap with Related News Themes', divider='gray')

timespan_stocks = st.selectbox(
    'Select a Timespan for News Themes',
    ('24h', '1w', '1m'),
    index=0, # Default to '24h'
    key='timespan_stocks'
)

if st.button("Fetch Top Stocks and News"):
    top_stocks = get_top_stocks_by_market_cap(limit=25)

    if top_stocks:
        stocks_with_news = []
        progress_text_stocks = st.empty()
        progress_bar_stocks = st.progress(0)

        for i, stock in enumerate(top_stocks):
            company_name = stock.get('companyName')
            symbol = stock.get('symbol')
            market_cap = stock.get('marketCap')

            progress_text_stocks.text(f"Fetching news for {company_name} ({symbol})...")
            progress_bar_stocks.progress((i + 1) / len(top_stocks))

            if company_name:
                try:
                    top_themes = get_gdelt_news_for_company(company_name, timespan_stocks)
                    stocks_with_news.append({
                        "Symbol": symbol,
                        "Company Name": company_name,
                        "Market Cap": f"${market_cap:,.0f}",
                        "Top 3 News Themes": ", ".join(top_themes) if top_themes else "N/A"
                    })
                except requests.exceptions.RequestException:
                    st.warning(f"Failed to fetch news for {company_name} after multiple retries due to rate limiting. Skipping.")
                    stocks_with_news.append({
                        "Symbol": symbol,
                        "Company Name": company_name,
                        "Market Cap": f"${market_cap:,.0f}",
                        "Top 3 News Themes": "Rate Limited / N/A"
                    })
            else:
                 stocks_with_news.append({
                    "Symbol": symbol,
                    "Company Name": "N/A",
                    "Market Cap": f"${market_cap:,.0f}",
                    "Top 3 News Themes": "N/A"
                })

        progress_bar_stocks.empty()
        progress_text_stocks.empty()

        st.dataframe(pd.DataFrame(stocks_with_news))
    else:
        st.warning("Could not fetch top stocks. Please check your FMP API key and try again.")
