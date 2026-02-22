import streamlit as st
import plotly.express as px
import fmp_client
import database

st.set_page_config(page_title="Sector Performance", page_icon=":chart_with_upwards_trend:", layout="wide")

st.sidebar.markdown("# Sector Performance")
st.markdown("# Sector Performance")
st.write(
    "Sector performance is tracked via major sector ETFs "
    "(XLK, XLF, XLE, XLV, XLI, XLY, XLP, XLU, XLRE, XLB, XLC). "
    "Each refresh appends a new snapshot — history accumulates over time."
)

# ---------------------------------------------------------------------------
# Refresh
# ---------------------------------------------------------------------------
if st.button("Refresh Sector Data"):
    with st.spinner("Fetching latest sector data from FMP..."):
        try:
            data = fmp_client.get_sector_performance()
            database.insert_sector_snapshot(data)
            st.cache_data.clear()
            st.success(f"Snapshot saved for {len(data)} sectors.")
            st.rerun()
        except Exception as e:
            st.error(f"Error fetching sector data: {e}")

# ---------------------------------------------------------------------------
# Latest snapshot
# ---------------------------------------------------------------------------
st.header("Latest Snapshot", divider="gray")
df = database.get_latest_sector_snapshot()

if df.empty:
    st.info("No data yet — click **Refresh Sector Data** above to fetch the first snapshot.")
    st.stop()

fig = px.bar(
    df,
    x="sector",
    y="changesPercentage",
    title="Sector Performance — Daily % Change (ETF Proxy)",
    labels={"changesPercentage": "% Change", "sector": "Sector"},
    color="changesPercentage",
    color_continuous_scale=px.colors.diverging.RdYlGn,
    color_continuous_midpoint=0,
    text_auto=".2f",
)
fig.update_layout(xaxis_tickangle=-30)
st.plotly_chart(fig, use_container_width=True)

st.dataframe(
    df[["sector", "symbol", "price", "changesPercentage", "fetched_at"]]
    .rename(columns={"changesPercentage": "% Change", "fetched_at": "As of"}),
    hide_index=True,
    use_container_width=True,
)

# ---------------------------------------------------------------------------
# Historical trend for a selected sector
# ---------------------------------------------------------------------------
st.header("Sector History", divider="gray")
selected = st.selectbox("Select a sector to view its trend", df["sector"].tolist())

history_df = database.get_sector_history(selected)

if len(history_df) < 2:
    st.info("Refresh more than once to start building a historical trend.")
else:
    fig2 = px.line(
        history_df,
        x="fetched_at",
        y="changesPercentage",
        title=f"{selected} — Daily % Change Over Time",
        labels={"changesPercentage": "% Change", "fetched_at": "Fetched at"},
        markers=True,
    )
    st.plotly_chart(fig2, use_container_width=True)
