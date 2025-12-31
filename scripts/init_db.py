from sqlalchemy import create_engine, text



engine = create_engine("sqlite:///data/db/news.db")

ddl = """
CREATE TABLE IF NOT EXISTS sectors (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT UNIQUE,
  description TEXT
);

CREATE TABLE IF NOT EXISTS symbols (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  symbol TEXT UNIQUE,
  name TEXT,
  sector_id INTEGER
);

CREATE TABLE IF NOT EXISTS news_items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  provider_id TEXT,
  symbol_id INTEGER,
  sector_id INTEGER,
  headline TEXT,
  body TEXT,
  source TEXT,
  url TEXT,
  published_at INTEGER,  -- unix seconds (UTC)
  ingested_at INTEGER
);

CREATE TABLE IF NOT EXISTS price_candles (
  symbol_id INTEGER,
  ts INTEGER,          -- unix seconds (UTC), candle start
  close REAL,
  volume REAL,
  PRIMARY KEY(symbol_id, ts)
);

CREATE TABLE IF NOT EXISTS news_features (
  news_id INTEGER PRIMARY KEY,
  p_pos REAL,
  p_neg REAL,
  p_neu REAL,
  sentiment_score REAL,     -- p_pos - p_neg
  source TEXT,
  hour INTEGER,
  dow INTEGER,
  is_market_hours INTEGER
);

CREATE TABLE IF NOT EXISTS train_rows (
  news_id INTEGER PRIMARY KEY,
  symbol_id INTEGER,
  t0 INTEGER,
  horizon_min INTEGER,
  y REAL
);
"""
stmts = [s.strip() for s in ddl.split(";") if s.strip()]

with engine.begin() as conn:
    for s in stmts:
        conn.execute(text(s))
print("DB initialized: data/db/news.db")
