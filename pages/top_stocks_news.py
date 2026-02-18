import streamlit as st
import pandas as pd
import requests
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
from database import get_top_stocks_news_from_db, insert_stock_news

st.set_page_config(page_title="Top Stocks News", page_icon=":chart_with_upwards_trend:", layout="wide")

st.sidebar.markdown("# Top Stocks News")
st.markdown("# Top Stocks News")

st.write("This page will display top 25 stocks by market cap and their top news words.")

# --- FMP API Configuration ---
FMP_API_KEY = st.secrets.get("FMP_API_KEY", "YOUR_FMP_API_KEY")

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
    params = {
        "marketCapMoreThan": 10000000000,  # > $10 Billion
        "limit": limit * 2,
        "sort": "marketCap",
        "exchange": "NASDAQ,NYSE",
        "apikey": FMP_API_KEY
    }
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        response = requests.get(FMP_API_BASE_URL, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        stocks_data = response.json()
        return sorted(stocks_data, key=lambda x: x.get('marketCap', 0), reverse=True)[:limit] if stocks_data else []
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching top stocks from FMP API: {e}")
    except ValueError:
        st.error(f"Error parsing JSON response from FMP API: {response.text[:500]}")
    return []

@st.cache_data(ttl=3600)
@retry(
    wait=wait_exponential(multiplier=1, min=4, max=10),
    stop=stop_after_attempt(5),
    retry=retry_if_exception_type(requests.exceptions.RequestException),
    reraise=True,
)
def get_stock_news_from_fmp(symbols):
    """
    Fetches news with sentiment for a list of stock symbols from the FMP API.
    """
    if FMP_API_KEY == "YOUR_FMP_API_KEY":
        st.error("Please set your FMP_API_KEY in Streamlit secrets or replace the placeholder.")
        return []

    FMP_API_BASE_URL = "https://financialmodelingprep.com/api/v4/stock-news-sentiments-rss-feed"
    all_news = []
    for symbol in symbols:
        params = {"symbol": symbol, "apikey": FMP_API_KEY}
        headers = {"User-Agent": "Mozilla/5.0"}
        try:
            response = requests.get(FMP_API_BASE_URL, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            news_data = response.json().get('items', [])
            for item in news_data:
                item['symbol'] = symbol
            all_news.extend(news_data)
        except requests.exceptions.RequestException as e:
            st.warning(f"Error fetching news for {symbol}: {e}")
        except ValueError:
            st.error(f"Error parsing JSON for {symbol}: {response.text[:500]}")
    return all_news

# --- Main App Logic ---
st.header('Top 25 Companies by Market Cap with Related News Sentiment', divider='gray')

if st.button("Fetch Top Stocks and News"):
    top_stocks = get_top_stocks_by_market_cap(limit=25)

    if top_stocks:
        symbols = [stock['symbol'] for stock in top_stocks]
        news_data = get_stock_news_from_fmp(symbols)

        if news_data:
            # Add company info to news data
            for news_item in news_data:
                stock_info = next((s for s in top_stocks if s['symbol'] == news_item['symbol']), None)
                if stock_info:
                    news_item['companyName'] = stock_info.get('companyName')
                    news_item['marketCap'] = stock_info.get('marketCap')

            insert_stock_news(news_data)
            st.success("Successfully fetched and stored the latest stock news.")

# Display news from the database
st.header("Latest News from Top Stocks", divider='gray')
news_df = get_top_stocks_news_from_db()

if not news_df.empty:
    st.dataframe(news_df[['companyName', 'news_title', 'news_sentiment', 'publishedDate', 'news_url']])
else:
    st.info("No news data found in the database. Click the button above to fetch data.")
