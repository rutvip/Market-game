from sqlalchemy import create_engine, text

engine = create_engine("sqlite:///data/db/news.db")

ddl = """
CREATE TABLE IF NOT EXISTS news_predictions (
  news_id INTEGER PRIMARY KEY,
  predicted_y REAL,         -- predicted abs abnormal log-return over your label horizon
  impact_score REAL,        -- 0..1 scaled for game
  direction INTEGER,        -- -1, 0, +1 (game direction)
  created_at INTEGER
);
"""

with engine.begin() as conn:
    for stmt in [s.strip() for s in ddl.split(";") if s.strip()]:
        conn.execute(text(stmt))

print("news_predictions table ready.")
