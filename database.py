"""
Database layer — SQLite, no Streamlit imports.

Design principles:
- All tables keep full history with a fetched_at timestamp.
- Pages always read "latest snapshot" via a MAX(fetched_at) subquery.
- News deduplicates by URL (INSERT OR IGNORE).
- init_db() is idempotent and safe to call on every app start.
"""
import sqlite3
import pandas as pd

DB_FILE = "news_sentiment.db"


def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    c = conn.cursor()

    # Each row is one sector reading at one point in time.
    c.execute('''
        CREATE TABLE IF NOT EXISTS sector_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sector TEXT NOT NULL,
            symbol TEXT NOT NULL,
            price REAL,
            change REAL,
            changesPercentage REAL,
            fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Gainers, losers, most-active — differentiated by the `type` column.
    c.execute('''
        CREATE TABLE IF NOT EXISTS market_movers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,
            symbol TEXT NOT NULL,
            name TEXT,
            price REAL,
            change REAL,
            changesPercentage REAL,
            volume INTEGER,
            fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # News deduplicated by URL; fetched_at records when we first saw each item.
    c.execute('''
        CREATE TABLE IF NOT EXISTS stock_news (
            url TEXT PRIMARY KEY,
            symbol TEXT,
            title TEXT NOT NULL,
            text TEXT,
            site TEXT,
            publishedDate TEXT,
            fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Sector snapshots
# ---------------------------------------------------------------------------

def insert_sector_snapshot(data):
    """Append a new point-in-time sector performance snapshot."""
    if not data:
        return
    conn = get_db_connection()
    c = conn.cursor()
    for row in data:
        c.execute('''
            INSERT INTO sector_snapshots (sector, symbol, price, change, changesPercentage)
            VALUES (?, ?, ?, ?, ?)
        ''', (row["sector"], row["symbol"], row.get("price"),
              row.get("change"), row.get("changesPercentage")))
    conn.commit()
    conn.close()


def get_latest_sector_snapshot():
    """Most recent reading per sector (the last fetch batch)."""
    conn = get_db_connection()
    df = pd.read_sql_query('''
        SELECT sector, symbol, price, change, changesPercentage, fetched_at
        FROM sector_snapshots
        WHERE fetched_at = (SELECT MAX(fetched_at) FROM sector_snapshots)
        ORDER BY changesPercentage DESC
    ''', conn)
    conn.close()
    return df


def get_sector_history(sector):
    """All historical readings for one sector, oldest first."""
    conn = get_db_connection()
    df = pd.read_sql_query('''
        SELECT changesPercentage, price, fetched_at
        FROM sector_snapshots
        WHERE sector = ?
        ORDER BY fetched_at ASC
    ''', conn, params=(sector,))
    conn.close()
    return df


# ---------------------------------------------------------------------------
# Market movers
# ---------------------------------------------------------------------------

def insert_market_movers(mover_type, data):
    """Append a new batch of gainers / losers / actives."""
    if not data:
        return
    conn = get_db_connection()
    c = conn.cursor()
    for row in data:
        c.execute('''
            INSERT INTO market_movers (type, symbol, name, price, change, changesPercentage, volume)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            mover_type,
            row.get("symbol"),
            row.get("name"),
            row.get("price"),
            row.get("change"),
            row.get("changesPercentage"),
            row.get("volume"),
        ))
    conn.commit()
    conn.close()


def get_latest_market_movers(mover_type):
    """Most recent batch of movers for the given type."""
    conn = get_db_connection()
    df = pd.read_sql_query('''
        SELECT symbol, name, price, change, changesPercentage, volume, fetched_at
        FROM market_movers
        WHERE type = ?
          AND fetched_at = (SELECT MAX(fetched_at) FROM market_movers WHERE type = ?)
        ORDER BY changesPercentage DESC
    ''', conn, params=(mover_type, mover_type))
    conn.close()
    return df


# ---------------------------------------------------------------------------
# News
# ---------------------------------------------------------------------------

def insert_news(data):
    """Insert news articles; silently skip duplicates (same URL)."""
    if not data:
        return
    conn = get_db_connection()
    c = conn.cursor()
    for item in data:
        c.execute('''
            INSERT OR IGNORE INTO stock_news (url, symbol, title, text, site, publishedDate)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            item.get("url"),
            item.get("symbol"),
            item.get("title"),
            item.get("text"),
            item.get("site"),
            item.get("publishedDate"),
        ))
    conn.commit()
    conn.close()


def get_news(limit=100):
    """Most recent news articles."""
    conn = get_db_connection()
    df = pd.read_sql_query('''
        SELECT symbol, title, site, publishedDate, url
        FROM stock_news
        ORDER BY publishedDate DESC
        LIMIT ?
    ''', conn, params=(limit,))
    conn.close()
    return df
