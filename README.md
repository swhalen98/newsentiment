# Global News Sentiment & Pulse Dashboard

This interactive dashboard, built with Python and Streamlit, provides a real-time view of global news sentiment and mention volume, powered by the [GDELT Project](https://www.gdeltproject.org/) API.

## 🚀 Features

- **Real-time Data**: Fetches the latest news data from the GDELT v2 Summary API.
- **Dynamic Search**: Enter any search term (e.g., "Artificial Intelligence", "climate change", a specific company name) to see how it's being covered in the global news.
- **Selectable Timespans**: Analyze trends over the last 24 hours, 1 week, or 1 month.
- **Key Metrics**:
  - **Total Mentions**: The total number of news articles mentioning your search term in the selected timespan.
  - **Peak Volume**: The highest volume of mentions in a single time interval.
  - **Average Sentiment**: A score indicating the overall tone of the news coverage (positive, negative, or neutral).
- **Trend Visualization**: An interactive line chart shows the volume of mentions over time.

## 🛠️ How It Works

The application takes a user-provided search term and a timespan and queries the GDELT API. The API returns a timeline of news mentions and the average "tone" (sentiment) for each interval.

The Streamlit front-end then processes this data to calculate the key metrics and visualizes the timeline data in a line chart.

## ⚙️ Running the Application

1.  **Install the dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

2.  **Run the Streamlit app**:
    ```bash
    streamlit run streamlit_app.py
    ```

This will start the local Streamlit server and open the application in your web browser.
