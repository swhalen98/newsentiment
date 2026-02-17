import streamlit as st
import pandas as pd
import requests
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
from collections import defaultdict
import plotly.express as px
import json

st.set_page_config(page_title="US News Map", page_icon=":map:", layout="wide")

st.sidebar.markdown("# US News Map")
st.markdown("# US News Map")

st.write("This page will display a map of the US with news volume bars by state and top topics.")

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

@st.cache_data(ttl=3600)
@retry(
    wait=wait_exponential(multiplier=1, min=4, max=10),
    stop=stop_after_attempt(5),
    retry=retry_if_exception_type(requests.exceptions.RequestException),
    reraise=True,
)
def get_gdelt_state_news_data(state_abbr, query, timespan):
    """
    Grab GDELT data for a specific US state from the GDELT API,
    including news volume and top topics.
    """
    API_BASE_URL_DOC = "https://api.gdeltproject.org/api/v2/doc/doc"
    API_BASE_URL_GKG = "https://api.gdeltproject.org/api/v1/gkg_geojson"

    gdelt_state_code = f"US{state_abbr}" # e.g., 'USTX' for Texas

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36"
    }

    # --- Fetch News Volume ---
    volume_params = {
        "query": f"{query} locationadm1:{gdelt_state_code}",
        "mode": "timelinevol",
        "timespan": timespan,
        "format": "json",
    }
    news_volume_df = pd.DataFrame()
    try:
        response = requests.get(API_BASE_URL_DOC, params=volume_params, headers=headers, timeout=10)
        response.raise_for_status()
        if response.text.strip():
            data = response.json()
            if 'timeline' in data and data['timeline']:
                series = data['timeline'][0].get('data')
                if series:
                    df = pd.DataFrame(series)
                    df.rename(columns={'date': 'datetime'}, inplace=True)
                    news_volume_df = df
    except requests.exceptions.RequestException as e:
        if hasattr(e, 'response') and e.response is not None and e.response.status_code == 429:
            st.error(f"Rate limited by GDELT API for volume ({state_abbr}): {e}. Retrying...")
            raise  # tenacity will retry on RequestException
        else:
            st.error(f"Error fetching volume for {state_abbr} from GDELT API: {e}")
    except ValueError:
        st.error(f"Error parsing JSON for volume ({state_abbr}) from GDELT API: {response.text[:500]}")

    # --- Fetch Top Topics (Themes) ---
    top_themes = defaultdict(int)
    gkg_params = {
        "query": f"{query} locationadm1:{gdelt_state_code}",
        "timespan": timespan,
        "format": "json", # gkg_geojson returns GeoJSON, but format=json might give a more parsable response for themes
    }

    try:
        response = requests.get(API_BASE_URL_GKG, params=gkg_params, headers=headers, timeout=10)
        response.raise_for_status()
        if response.text.strip():
            gkg_data = response.json()
        else:
            gkg_data = {}

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
            st.error(f"Rate limited by GDELT API for themes ({state_abbr}): {e}. Retrying...")
            raise  # tenacity will retry on RequestException
        else:
            st.error(f"Error fetching themes for {state_abbr} from GDELT API: {e}")
    except ValueError:
        st.error(f"Error parsing JSON for themes ({state_abbr}) from GDELT API: {response.text[:500]}")

    # Sort themes by count and get the top ones
    sorted_themes = sorted(top_themes.items(), key=lambda item: item[1], reverse=True)

    return {
        "state_name": US_STATES[state_abbr],
        "news_volume": news_volume_df,
        "total_volume": news_volume_df['value'].sum() if not news_volume_df.empty else 0,
        "top_themes": sorted_themes
    }

# --- Main App Logic ---

search_term_map = st.text_input(
    'Enter a Search Term for US Map',
    'Artificial Intelligence',
    key='search_term_map'
)

timespan_map = st.selectbox(
    'Select a Timespan for US Map',
    ('24h', '1w', '1m'),
    index=0, # Default to '24h' for more recent data
    key='timespan_map'
)

if search_term_map:
    all_states_data = []

    progress_text = st.empty()
    progress_bar = st.progress(0)

    for i, (state_abbr, state_name) in enumerate(US_STATES.items()):
        progress_text.text(f"Fetching data for {state_name} ({state_abbr})...")
        progress_bar.progress((i + 1) / len(US_STATES))

        try:
            state_data = get_gdelt_state_news_data(state_abbr, search_term_map, timespan_map)
            all_states_data.append(state_data)
        except requests.exceptions.RequestException:
            st.warning(f"Failed to fetch data for {state_name} after multiple retries due to rate limiting. Please try again later.")
            continue # Skip this state and continue with others

    progress_bar.empty()
    progress_text.empty()

    if all_states_data:
        # Prepare data for map
        map_data = []
        for state_data in all_states_data:
            map_data.append({
                'state_abbr': list(US_STATES.keys())[list(US_STATES.values()).index(state_data['state_name'])],
                'state_name': state_data['state_name'],
                'total_volume': state_data['total_volume'],
                'top_theme_1': state_data['top_themes'][0][0] if state_data['top_themes'] else 'N/A',
                'top_theme_1_count': state_data['top_themes'][0][1] if state_data['top_themes'] else 0,
                'top_theme_2': state_data['top_themes'][1][0] if len(state_data['top_themes']) > 1 else 'N/A',
                'top_theme_2_count': state_data['top_themes'][1][1] if len(state_data['top_themes']) > 1 else 0,
            })

        map_df = pd.DataFrame(map_data)

        # Load GeoJSON for US states
        # You would typically load this from a URL or local file
        # For simplicity, let's assume we have a way to get this
        # Example using a common public GeoJSON (replace with a local one if needed)
        geojson_url = "https://raw.githubusercontent.com/PublicaMundi/MappingAPI/master/data/geojson/us-states.json"

        try:
            geojson_response = requests.get(geojson_url, timeout=5)
            geojson_response.raise_for_status()
            us_states_geojson = geojson_response.json()
        except requests.exceptions.RequestException as e:
            st.error(f"Error loading US states GeoJSON: {e}. Cannot display map.")
            us_states_geojson = None

        if us_states_geojson:
            st.header('US News Volume and Top Topics by State', divider='gray')

            # Create choropleth map
            fig = px.choropleth(
                map_df,
                geojson=us_states_geojson,
                locations='state_abbr', # Your DataFrame column with state abbreviations
                featureidkey="properties.state", # Key in GeoJSON that matches 'locations'
                color='total_volume', # Your DataFrame column with the data to color the states
                color_continuous_scale="Viridis",
                scope="usa",
                hover_name='state_name',
                hover_data={
                    'total_volume': True,
                    'top_theme_1': True,
                    'top_theme_1_count': False,
                    'top_theme_2': True,
                    'top_theme_2_count': False,
                },
                title='News Volume by US State'
            )
            fig.update_geos(fitbounds="locations", visible=False)
            fig.update_layout(margin={"r":0,"t":50,"l":0,"b":0})
            st.plotly_chart(fig, use_container_width=True)

            st.write("### Top Topics by State (Hover over map for details)")
            st.dataframe(map_df[['state_name', 'total_volume', 'top_theme_1', 'top_theme_2']])

    else:
        st.info("No data fetched for any state or GeoJSON could not be loaded.")
else:
    st.info("Please enter a search term to view the US News Map.")
