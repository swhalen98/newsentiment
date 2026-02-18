import streamlit as st
from database import init_db

# Set the title and favicon that appear in the Browser's tab bar.
st.set_page_config(
    page_title='News Sentiment Analysis',
    page_icon=':newspaper:', # This is an emoji shortcode. Could be a URL too.
)

# Initialize the database
init_db()

# -----------------------------------------------------------------------------
# Draw the actual page

st.sidebar.markdown("# News Sentiment Analysis")

# Set the title that appears at the top of the page.
'''
# :newspaper: News Sentiment Analysis

Welcome to the News Sentiment Analysis app.

This application provides tools to analyze news sentiment and volume from various sources.

Use the sidebar to navigate to the different pages:

- **Top Stocks News:** View news and sentiment for the top 25 stocks by market cap.
- **Sector Performance:** Analyze the performance of different market sectors and related news.

'''

st.info("Select a page from the sidebar to get started.")
