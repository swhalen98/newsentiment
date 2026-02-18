import streamlit as st
import pandas as pd
import requests
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
from database import get_sector_performance_from_db, insert_sector_performance, get_db_connection
import plotly.express as px

st.set_page_config(page_title="Sector Performance", page_icon=":chart_with_upwards_trend:", layout="wide")

st.sidebar.markdown("# Sector Performance")
st.markdown("# Sector Performance")

st.write("This page displays the performance of various market sectors and related news.")

# --- FMP API Configuration ---
FMP_API_KEY = st.secrets.get("FMP_API_KEY", "YOUR_FMP_API_KEY")

@st.cache_data(ttl=3600)
@retry(
    wait=wait_exponential(multiplier=1, min=4, max=10),
    stop=stop_after_attempt(5),
    retry=retry_if_exception_type(requests.exceptions.RequestException),
    reraise=True,
)
def get_sector_performance_from_fmp():
    """
    Fetches the latest sector performance data from the FMP API.
    """
    if FMP_API_KEY == "YOUR_FMP_API_KEY":
        st.error("Please set your FMP_API_KEY in Streamlit secrets or replace the placeholder.")
        return []

    FMP_API_BASE_URL = "https://financialmodelingprep.com/api/v3/sectors-performance"
    params = {"apikey": FMP_API_KEY}
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        response = requests.get(FMP_API_BASE_URL, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        sector_data = response.json()
        if sector_data:
            # The API returns a list of dictionaries.
            # Convert 'changesPercentage' to a float.
            for sector in sector_data:
                try:
                    sector['performance'] = float(sector.get('changesPercentage', '0').replace('%', ''))
                except (ValueError, TypeError):
                    sector['performance'] = 0.0
            return sector_data
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching sector performance from FMP API: {e}")
    except ValueError:
        st.error(f"Error parsing JSON response from FMP API: {response.text[:500]}")
    return []

@st.cache_data(ttl=3600)
def get_news_for_sector(sector):
    """
    Fetches news for a given sector.
    For simplicity, we'll search for the sector name as a keyword in the general news.
    """
    # This is a simplified implementation. A more advanced version could
    # get top companies in a sector and then get news for those companies.
    FMP_API_BASE_URL = "https://financialmodelingprep.com/api/v3/stock_news"
    params = {"section": "general", "limit": 20, "apikey": FMP_API_KEY}
    headers = {"User-Agent": "Mozilla/5.0"}
    all_news = []
    try:
        response = requests.get(FMP_API_BASE_URL, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        news_data = response.json()
        # Filter news that contains the sector name in the title or text
        for news in news_data:
            if sector.lower() in news.get('text', '').lower() or sector.lower() in news.get('title', '').lower():
                all_news.append(news)
    except requests.exceptions.RequestException as e:
        st.warning(f"Error fetching news for {sector}: {e}")
    except ValueError:
        st.error(f"Error parsing JSON for {sector}: {response.text[:500]}")
    return all_news


# --- Main App Logic ---
st.header('Market Sector Performance', divider='gray')

if st.button("Fetch Latest Sector Performance"):
    sector_performance_data = get_sector_performance_from_fmp()

    if sector_performance_data:
        insert_sector_performance(sector_performance_data)
        st.success("Successfully fetched and stored the latest sector performance data.")

# Display sector performance from the database
sector_df = get_sector_performance_from_db()

if not sector_df.empty:
    # Sort by performance
    sector_df = sector_df.sort_values('performance', ascending=False)

    # Bar chart of sector performance
    fig = px.bar(
        sector_df,
        x='sector',
        y='performance',
        title='Sector Performance (1D % Change)',
        labels={'performance': '% Change'},
        color='performance',
        color_continuous_scale=px.colors.diverging.RdYlGn,
        color_continuous_midpoint=0
    )
    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(sector_df[['sector', 'performance', 'last_updated']].rename(columns={'performance': '% Change'}), hide_index=True)

    # Allow user to select a sector to view news
    st.header("Sector News", divider='gray')
    selected_sector = st.selectbox("Select a sector to view news", sector_df['sector'].unique())

    if selected_sector:
        st.subheader(f"Recent News for the {selected_sector} Sector")
        sector_news = get_news_for_sector(selected_sector)
        if sector_news:
            for news in sector_news:
                st.markdown(f"**[{news['title']}]({news['url']})**")
                st.write(f"_{news['publishedDate']}_")
                st.write(news.get('text', 'No summary available.'))
                st.divider()
        else:
            st.info(f"No recent news found for the {selected_sactor} sector.")

else:
    st.info("No sector performance data found in the database. Click the button above to fetch data.")
