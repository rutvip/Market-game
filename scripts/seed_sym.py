from sqlalchemy import create_engine, text

engine = create_engine("sqlite:///data/db/news.db")

SYMBOLS = [
  ("AAPL","Apple Inc."), ("MSFT","Microsoft"), ("NVDA","NVIDIA"),
  ("AMZN","Amazon"), ("GOOGL","Alphabet"), ("META","Meta"),
  ("TSLA","Tesla"), ("JPM","JPMorgan"), ("XOM","Exxon"),
  ("SPY","SPDR S&P 500 ETF")  # benchmark
]

with engine.begin() as conn:
    for sym,name in SYMBOLS:
        conn.execute(text(
            "INSERT OR IGNORE INTO symbols(symbol,name,sector_id) VALUES(:s,:n,NULL)"
        ), {"s": sym, "n": name})
print("Seeded symbols.")
