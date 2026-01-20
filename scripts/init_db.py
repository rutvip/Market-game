# scripts/init_db.py
from pathlib import Path
from sqlalchemy import create_engine, text

DB_PATH = Path("data/db/news.db")

DDL = """
CREATE TABLE IF NOT EXISTS sectors (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT UNIQUE,
  description TEXT
);

CREATE TABLE IF NOT EXISTS symbols (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  symbol TEXT UNIQUE,
  name TEXT,
  sector_id INTEGER,
  FOREIGN KEY(sector_id) REFERENCES sectors(id)
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
  ingested_at INTEGER,
  FOREIGN KEY(symbol_id) REFERENCES symbols(id),
  FOREIGN KEY(sector_id) REFERENCES sectors(id)
);

CREATE TABLE IF NOT EXISTS price_candles (
  symbol_id INTEGER,
  ts INTEGER,          -- unix seconds (UTC), candle start
  close REAL,
  volume REAL,
  PRIMARY KEY(symbol_id, ts),
  FOREIGN KEY(symbol_id) REFERENCES symbols(id)
);

CREATE TABLE IF NOT EXISTS news_features (
  news_id INTEGER PRIMARY KEY,
  p_pos REAL,
  p_neg REAL,
  p_neu REAL,
  sentiment_score REAL,     -- p_pos - p_neg
  source TEXT,
  hour INTEGER,             -- UTC hour
  dow INTEGER,              -- UTC day-of-week (Mon=0)
  is_market_hours INTEGER,
  FOREIGN KEY(news_id) REFERENCES news_items(id)
);

CREATE TABLE IF NOT EXISTS train_rows (
  news_id INTEGER PRIMARY KEY,
  symbol_id INTEGER,
  t0 INTEGER,
  horizon_min INTEGER,
  y REAL,
  FOREIGN KEY(news_id) REFERENCES news_items(id),
  FOREIGN KEY(symbol_id) REFERENCES symbols(id)
);

CREATE TABLE IF NOT EXISTS news_predictions (
  news_id INTEGER PRIMARY KEY,
  predicted_y REAL,
  impact_score REAL,      -- 0..1
  direction INTEGER,      -- -1,0,+1
  created_at INTEGER,
  FOREIGN KEY(news_id) REFERENCES news_items(id)
);

-- Indexes for speed
CREATE INDEX IF NOT EXISTS idx_news_items_symbol_id ON news_items(symbol_id);
CREATE INDEX IF NOT EXISTS idx_news_items_published_at ON news_items(published_at);
CREATE INDEX IF NOT EXISTS idx_news_features_news_id ON news_features(news_id);
CREATE INDEX IF NOT EXISTS idx_train_rows_symbol_id ON train_rows(symbol_id);
CREATE INDEX IF NOT EXISTS idx_news_pred_created_at ON news_predictions(created_at);
"""

def main():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    engine = create_engine(f"sqlite:///{DB_PATH.as_posix()}")

    # SQLite/SQLAlchemy: execute one statement at a time.
    stmts = [s.strip() for s in DDL.split(";") if s.strip()]

    with engine.begin() as conn:
        for s in stmts:
            conn.execute(text(s))

    print(f"DB initialized: {DB_PATH}")

if __name__ == "__main__":
    main()
