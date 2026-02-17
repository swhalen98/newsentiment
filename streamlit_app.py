import streamlit as st
import pandas as pd
import requests
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type

# Set the title and favicon that appear in the Browser's tab bar.
st.set_page_config(
    page_title='Global News Sentiment & Pulse',
    page_icon=':newspaper:', # This is an emoji shortcode. Could be a URL too.
)

# -----------------------------------------------------------------------------
# Declare some useful functions.

@st.cache_data(ttl=3600)
@retry(
    wait=wait_exponential(multiplier=1, min=4, max=10),
    stop=stop_after_attempt(5),
    retry=retry_if_exception_type(requests.exceptions.RequestException),
    reraise=True,
)
def get_gdelt_data(query, timespan):
    """Grab GDELT data from the GDELT API.

    This uses caching to avoid having to hit the API every time. The cache is
    set to expire every hour (3600 seconds).
    """
    API_BASE_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
    params = {
        "query": f"{query} sourcecountry:US",
        "mode": "timelinevol",
        "timespan": timespan,
        "format": "json",
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36"
    }
    try:
        response = requests.get(API_BASE_URL, params=params, headers=headers, timeout=10)
        response.raise_for_status()  # Raise an exception for bad status codes
        data = response.json()
        if 'timeline' in data and data['timeline']:
            series = data['timeline'][0].get('data')
            if series:
                df = pd.DataFrame(series)
                df.rename(columns={'date': 'datetime'}, inplace=True)
                return df
    except requests.exceptions.RequestException as e:
        if hasattr(e, 'response') and e.response is not None and e.response.status_code == 429:
            st.error(f"Error fetching data from GDELT API: {e}. Retrying...")
            raise  # tenacity will retry on RequestException
        else:
            st.error(f"Error fetching data from GDELT API: {e}")
    except ValueError:
        st.error(f"Error parsing JSON response from GDELT API. The API returned: {response.text[:500]}")
    return pd.DataFrame()


# -----------------------------------------------------------------------------
# Draw the actual page
st.sidebar.markdown("# Global News Sentiment & Pulse")

# Set the title that appears at the top of the page.
'''
# :newspaper: Global News Sentiment & Pulse

Browse news volume and sentiment from the [GDELT Project](https://www.gdeltproject.org/).
Enter a search term and select a timespan to see how the story is evolving across
the global news landscape.
'''

# Add some spacing
''
''

timespan = st.selectbox(
    'Select a Timespan',
    ('24h', '1w', '1m'),
    index=1  # Default to '1w'
)

search_term = st.text_input(
    'Enter a Search Term',
    'Artificial Intelligence'
)

''
''
''

# Fetch and process the data
if search_term:
    gdelt_df = get_gdelt_data(search_term, timespan)

    if not gdelt_df.empty:
        gdelt_df['datetime'] = pd.to_datetime(gdelt_df['datetime'])
        gdelt_df.rename(columns={'value': 'Mention Volume'}, inplace=True)

        st.header('Mention Volume Over Time', divider='gray')
        ''
        st.line_chart(
            gdelt_df,
            x='datetime',
            y='Mention Volume',
        )
        ''
        ''

        # Calculate metrics
        total_mentions = gdelt_df['Mention Volume'].sum()
        peak_volume = gdelt_df['Mention Volume'].max()
        # The 'tone' data is often coarse, so we'll use a simple average for this example
        average_tone = gdelt_df['tone'].mean() if 'tone' in gdelt_df.columns else 0

        st.header('Key Metrics', divider='gray')
        ''
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(label="Total Mentions", value=f"{int(total_mentions):,}")
        with col2:
            st.metric(label="Peak Volume", value=f"{int(peak_volume):,}")
        with col3:
            st.metric(label="Avg. Sentiment", value=f"{average_tone:.2f}")

    else:
        st.warning(f"No results found for '{search_term}' in the last {timespan}. Try another query.")
else:
    st.info("Please enter a search term to begin.")
