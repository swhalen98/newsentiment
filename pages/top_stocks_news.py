import streamlit as st
import plotly.express as px
import fmp_client
import database

st.set_page_config(page_title="Market Movers & News", page_icon=":chart_with_upwards_trend:", layout="wide")

st.sidebar.markdown("# Market Movers & News")
st.markdown("# Market Movers & News")
st.write("Top gaining, losing, and most active stocks — plus the latest news. All data is free-tier FMP.")

# ---------------------------------------------------------------------------
# Refresh
# ---------------------------------------------------------------------------
if st.button("Refresh Market Data"):
    with st.spinner("Fetching gainers, losers, actives, and news..."):
        errors = []

        for mover_type, fn in [("gainer", fmp_client.get_gainers),
                                ("loser", fmp_client.get_losers),
                                ("active", fmp_client.get_actives)]:
            try:
                database.insert_market_movers(mover_type, fn())
            except Exception as e:
                errors.append(f"{mover_type.capitalize()}s: {e}")

        try:
            database.insert_news(fmp_client.get_stock_news())
        except Exception as e:
            errors.append(f"News: {e}")

        if errors:
            for err in errors:
                st.error(err)
        else:
            st.success("Market data refreshed.")
        st.rerun()

# ---------------------------------------------------------------------------
# Market movers — tabs
# ---------------------------------------------------------------------------
st.header("Market Movers", divider="gray")
tab_gainers, tab_losers, tab_actives = st.tabs(["Gainers", "Losers", "Most Active"])


def render_movers(mover_type):
    df = database.get_latest_market_movers(mover_type)
    if df.empty:
        st.info("No data yet — click **Refresh Market Data** above.")
        return

    as_of = df["fetched_at"].iloc[0]
    st.caption(f"Last updated: {as_of}")

    fig = px.bar(
        df.head(20),
        x="symbol",
        y="changesPercentage",
        hover_data=["name", "price", "volume"],
        labels={"changesPercentage": "% Change", "symbol": "Symbol"},
        color="changesPercentage",
        color_continuous_scale=px.colors.diverging.RdYlGn,
        color_continuous_midpoint=0,
        text_auto=".2f",
    )
    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(
        df[["symbol", "name", "price", "changesPercentage", "volume"]]
        .rename(columns={"changesPercentage": "% Change"}),
        hide_index=True,
        use_container_width=True,
    )


with tab_gainers:
    render_movers("gainer")

with tab_losers:
    render_movers("loser")

with tab_actives:
    render_movers("active")

# ---------------------------------------------------------------------------
# News feed
# ---------------------------------------------------------------------------
st.header("Latest News", divider="gray")
news_df = database.get_news(limit=50)

if news_df.empty:
    st.info("No news yet — click **Refresh Market Data** above.")
else:
    for _, row in news_df.iterrows():
        cols = st.columns([0.85, 0.15])
        with cols[0]:
            st.markdown(f"**[{row['title']}]({row['url']})**")
        with cols[1]:
            if row.get("symbol"):
                st.code(row["symbol"], language=None)
        st.caption(f"{row.get('site', '')}  ·  {row.get('publishedDate', '')}")
        st.divider()
