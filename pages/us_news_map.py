import streamlit as st
import pandas as pd
import requests
import time
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
from collections import defaultdict
import plotly.express as px

st.set_page_config(page_title="US News Map", page_icon=":map:", layout="wide")

st.sidebar.markdown("# US News Map")
st.markdown("# US News Map")

st.write("Select states and a search term to see news volume across the US.")

# US state abbreviations and their full names
US_STATES = {
    'AL': 'Alabama', 'AK': 'Alaska', 'AZ': 'Arizona', 'AR': 'Arkansas', 'CA': 'California',
    'CO': 'Colorado', 'CT': 'Connecticut', 'DE': 'Delaware', 'FL': 'Florida', 'GA': 'Georgia',
    'HI': 'Hawaii', 'ID': 'Idaho', 'IL': 'Illinois', 'IN': 'Indiana', 'IA': 'Iowa',
    'KS': 'Kansas', 'KY': 'Kentucky', 'LA': 'Louisiana', 'ME': 'Maine', 'MD': 'Maryland',
    'MA': 'Massachusetts', 'MI': 'Michigan', 'MN': 'Minnesota', 'MS': 'Mississippi', 'MO': 'Missouri',
    'MT': 'Montana', 'NE': 'Nebraska', 'NV': 'Nevada', 'NH': 'New Hampshire', 'NJ': 'New Jersey',
    'NM': 'New Mexico', 'NY': 'New York', 'NC': 'North Carolina', 'ND': 'North Dakota', 'OH': 'Ohio',
    'OK': 'Oklahoma', 'OR': 'Oregon', 'PA': 'Pennsylvania', 'RI': 'Rhode Island', 'SC': 'South Carolina',
    'SD': 'South Dakota', 'TN': 'Tennessee', 'TX': 'Texas', 'UT': 'Utah', 'VT': 'Vermont',
    'VA': 'Virginia', 'WA': 'Washington', 'WV': 'West Virginia', 'WI': 'Wisconsin', 'WY': 'Wyoming'
}

DEFAULT_STATES = ['CA', 'TX', 'NY', 'FL', 'IL', 'PA', 'OH', 'GA', 'WA', 'MA']

# Delay between API requests to avoid rate limiting (seconds)
API_REQUEST_DELAY = 1.0

@st.cache_data(ttl=3600)
@retry(
    wait=wait_exponential(multiplier=2, min=5, max=30),
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type(requests.exceptions.RequestException),
    reraise=True,
)
def get_gdelt_state_volume(state_abbr, query, timespan):
    """
    Fetch news volume for a specific US state from the GDELT DOC API.
    """
    API_BASE_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
    gdelt_state_code = f"US{state_abbr}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    params = {
        "query": f"{query} locationadm1:{gdelt_state_code}",
        "mode": "timelinevol",
        "timespan": timespan,
        "format": "json",
    }

    response = requests.get(API_BASE_URL, params=params, headers=headers, timeout=15)
    response.raise_for_status()

    if not response.text.strip():
        return 0

    data = response.json()
    total_volume = 0
    if 'timeline' in data and data['timeline']:
        series = data['timeline'][0].get('data')
        if series:
            total_volume = sum(item.get('value', 0) for item in series)

    return total_volume


# --- Main App Logic ---

search_term_map = st.text_input(
    'Enter a Search Term for US Map',
    'Artificial Intelligence',
    key='search_term_map'
)

timespan_map = st.selectbox(
    'Select a Timespan for US Map',
    ('24h', '1w', '1m'),
    index=0,
    key='timespan_map'
)

selected_states = st.multiselect(
    'Select States to Query',
    options=list(US_STATES.keys()),
    default=DEFAULT_STATES,
    format_func=lambda x: f"{x} - {US_STATES[x]}",
    key='selected_states'
)

if not selected_states:
    st.info("Please select at least one state.")
elif search_term_map:
    all_states_data = []

    progress_text = st.empty()
    progress_bar = st.progress(0)

    for i, state_abbr in enumerate(selected_states):
        state_name = US_STATES[state_abbr]
        progress_text.text(f"Fetching data for {state_name} ({state_abbr})... ({i + 1}/{len(selected_states)})")
        progress_bar.progress((i + 1) / len(selected_states))

        try:
            total_volume = get_gdelt_state_volume(state_abbr, search_term_map, timespan_map)
            all_states_data.append({
                'state_abbr': state_abbr,
                'state_name': state_name,
                'total_volume': total_volume,
            })
        except requests.exceptions.RequestException:
            st.warning(f"Failed to fetch data for {state_name} after retries. Skipping.")
            continue

        # Rate limit: wait between requests (skip delay on last iteration)
        if i < len(selected_states) - 1:
            time.sleep(API_REQUEST_DELAY)

    progress_bar.empty()
    progress_text.empty()

    if all_states_data:
        map_df = pd.DataFrame(all_states_data)

        # Load GeoJSON for US states
        geojson_url = "https://raw.githubusercontent.com/PublicaMundi/MappingAPI/master/data/geojson/us-states.json"

        try:
            geojson_response = requests.get(geojson_url, timeout=5)
            geojson_response.raise_for_status()
            us_states_geojson = geojson_response.json()
        except requests.exceptions.RequestException as e:
            st.error(f"Error loading US states GeoJSON: {e}. Cannot display map.")
            us_states_geojson = None

        if us_states_geojson:
            st.header('US News Volume by State', divider='gray')

            fig = px.choropleth(
                map_df,
                geojson=us_states_geojson,
                locations='state_abbr',
                featureidkey="properties.state",
                color='total_volume',
                color_continuous_scale="Viridis",
                scope="usa",
                hover_name='state_name',
                hover_data={'total_volume': True},
                title='News Volume by US State'
            )
            fig.update_geos(fitbounds="locations", visible=False)
            fig.update_layout(margin={"r": 0, "t": 50, "l": 0, "b": 0})
            st.plotly_chart(fig, use_container_width=True)

            st.header('Volume by State', divider='gray')
            st.dataframe(
                map_df[['state_name', 'total_volume']].sort_values('total_volume', ascending=False),
                hide_index=True,
            )

    else:
        st.info("No data fetched for any state.")
else:
    st.info("Please enter a search term to view the US News Map.")
