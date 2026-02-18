import sqlite3
import pandas as pd
import streamlit as st

DB_FILE = "news_sentiment.db"

def get_db_connection():
    """Create and return a database connection."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize the database and create tables if they don't exist."""
    conn = get_db_connection()
    c = conn.cursor()

    # Create table for top stocks news
    c.execute('''
        CREATE TABLE IF NOT EXISTS top_stocks_news (
            symbol TEXT,
            companyName TEXT,
            marketCap REAL,
            news_sentiment REAL,
            news_url TEXT,
            news_title TEXT,
            publishedDate TEXT,
            PRIMARY KEY (symbol, news_title)
        )
    ''')

    # Create table for sector performance
    c.execute('''
        CREATE TABLE IF NOT EXISTS sector_performance (
            sector TEXT PRIMARY KEY,
            performance REAL,
            last_updated TEXT
        )
    ''')
    conn.commit()
    conn.close()

def insert_stock_news(news_data):
    """Insert a list of stock news into the database."""
    if not news_data:
        return

    conn = get_db_connection()
    c = conn.cursor()
    for news in news_data:
        c.execute('''
            INSERT OR REPLACE INTO top_stocks_news (symbol, companyName, marketCap, news_sentiment, news_url, news_title, publishedDate)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            news.get('symbol'),
            news.get('companyName'),
            news.get('marketCap'),
            news.get('sentiment'),
            news.get('url'),
            news.get('title'),
            news.get('publishedDate')
        ))
    conn.commit()
    conn.close()

def get_top_stocks_news_from_db():
    """Retrieve top stocks news from the database."""
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT * FROM top_stocks_news", conn)
    conn.close()
    return df

def insert_sector_performance(sector_data):
    """Insert sector performance data into the database."""
    if not sector_data:
        return

    conn = get_db_connection()
    c = conn.cursor()
    for sector in sector_data:
        c.execute('''
            INSERT OR REPLACE INTO sector_performance (sector, performance, last_updated)
            VALUES (?, ?, datetime('now'))
        ''', (
            sector.get('sector'),
            sector.get('performance')
        ))
    conn.commit()
    conn.close()

def get_sector_performance_from_db():
    """Retrieve sector performance data from the database."""
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT * FROM sector_performance", conn)
    conn.close()
    return df

# Initialize the database when the app starts
if 'db_initialized' not in st.session_state:
    init_db()
    st.session_state['db_initialized'] = True
