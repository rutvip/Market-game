import math
from sqlalchemy import create_engine, text

engine = create_engine("sqlite:///data/db/news.db")
BETA = 1.0  # start simple

def next_close(symbol_id, ts):
    # pick next candle on/after ts
    with engine.begin() as conn:
        row = conn.execute(text("""
            SELECT close, ts FROM price_candles
            WHERE symbol_id=:sid AND ts>=:ts
            ORDER BY ts ASC LIMIT 1
        """), {"sid": symbol_id, "ts": ts}).fetchone()
    if not row:
        return None
    return float(row[0]), int(row[1])

def main():
    with engine.begin() as conn:
        spy_id = conn.execute(text("SELECT id FROM symbols WHERE symbol='SPY'")).fetchone()[0]
        news = conn.execute(text("""
            SELECT id, symbol_id, published_at
            FROM news_items
            WHERE symbol_id IS NOT NULL AND published_at > 0
              AND id IN (SELECT news_id FROM news_features)
              AND id NOT IN (SELECT news_id FROM train_rows)
        """)).fetchall()

    added = 0
    for news_id, symbol_id, pub in news:
        # map published_at to that day's UTC midnight ts
        t0_day = int(pub) - (int(pub) % 86400)

        P0 = next_close(symbol_id, t0_day)
        P1 = next_close(symbol_id, t0_day + 86400)
        M0 = next_close(spy_id, t0_day)
        M1 = next_close(spy_id, t0_day + 86400)

        if None in (P0, P1, M0, M1):
            continue

        p0, _ = P0
        p1, _ = P1
        m0, _ = M0
        m1, _ = M1

        r_stock = math.log(p1 / p0)
        r_mkt = math.log(m1 / m0)
        abn = r_stock - BETA * r_mkt
        y = abs(abn)

        with engine.begin() as conn:
            conn.execute(text("""
                INSERT OR REPLACE INTO train_rows(news_id, symbol_id, t0, horizon_min, y)
                VALUES(:nid,:sid,:t0,:h,:y)
            """), {"nid": int(news_id), "sid": int(symbol_id), "t0": int(t0_day), "h": 1440, "y": float(y)})
        added += 1

    print("Added", added, "train rows")

if __name__ == "__main__":
    main()
