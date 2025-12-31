import os, time, requests
from sqlalchemy import create_engine, text
from tqdm import tqdm

TOKEN = os.getenv("FINNHUB_TOKEN")
engine = create_engine("sqlite:///data/db/news.db")

def get_symbols():
    with engine.begin() as conn:
        rows = conn.execute(text("SELECT id, symbol FROM symbols WHERE symbol != 'SPY'")).fetchall()
    return rows

def fetch_company_news(symbol, _from, to):
    url = "https://finnhub.io/api/v1/company-news"
    r = requests.get(url, params={"symbol": symbol, "from": _from, "to": to, "token": TOKEN}, timeout=30)
    r.raise_for_status()
    return r.json()

def main():
    # backfill window (YYYY-MM-DD)
    _from = "2025-10-01"
    to = "2025-12-30"

    syms = get_symbols()
    now = int(time.time())

    for symbol_id, sym in tqdm(syms):
        items = fetch_company_news(sym, _from, to)
        with engine.begin() as conn:
            for it in items:
                conn.execute(text("""
                    INSERT INTO news_items(provider_id, symbol_id, sector_id, headline, body, source, url, published_at, ingested_at)
                    VALUES(:pid,:sid,NULL,:h,:b,:src,:url,:pub,:ing)
                """), {
                    "pid": str(it.get("id") or it.get("url")),
                    "sid": symbol_id,
                    "h": it.get("headline"),
                    "b": it.get("summary") or it.get("text") or "",
                    "src": it.get("source"),
                    "url": it.get("url"),
                    "pub": int(it.get("datetime", 0)),
                    "ing": now
                })
        time.sleep(0.3)  # be nice to rate limits
    print("Done backfill news.")

if __name__ == "__main__":
    main()
