import time
from sqlalchemy import create_engine, text
from mode_a_engine import ModeAEngine
import msvcrt

DB = "sqlite:///data/db/news.db"
engine_db = create_engine(DB)

SYMBOL = "AAPL"

def get_symbol_id(symbol: str) -> int:
    with engine_db.begin() as conn:
        row = conn.execute(text("SELECT id FROM symbols WHERE symbol=:s"), {"s": symbol}).fetchone()
    if not row:
        raise RuntimeError(f"Symbol {symbol} not found in symbols table.")
    return int(row[0])

def read_key():
    if msvcrt.kbhit():
        return msvcrt.getwch()
    return None

def fetch_new_news_predictions(symbol_id: int, last_news_id: int):
    """
    Returns list of (news_id, headline, direction, impact_score)
    """
    with engine_db.begin() as conn:
        rows = conn.execute(text("""
            SELECT n.id, n.headline, p.direction, p.impact_score
            FROM news_items n
            JOIN news_predictions p ON p.news_id = n.id
            WHERE n.symbol_id = :sid
              AND n.id > :last
            ORDER BY n.id ASC
            LIMIT 50
        """), {"sid": symbol_id, "last": last_news_id}).fetchall()
    return [(int(r[0]), r[1], int(r[2]), float(r[3])) for r in rows]

def main():
    symbol_id = get_symbol_id(SYMBOL)

    eng = ModeAEngine(mid0=200.0, dt=0.05)  # 50ms tick

    last_news_id = 0
    last_print = 0.0

    print(f"=== MODE A single-symbol game: {SYMBOL} ===")
    print("Controls: b=buy(1), s=sell(1), B=buy(10), S=sell(10), q=quit\n")

    # non-blocking input (simple cross-platform fallback: poll stdin only if line available)
    # For v1, we just auto-trade nothing; you can wire UI later.

    while True:
        now = time.time()  # IMPORTANT: define now first

        # --- player input ---
        k = read_key()
        if k in ("q", "Q"):
            print("Bye.")
            break

        if k in ("b", "B"):   # buy
            qty = 1 if k == "b" else 10
            px = eng.buy(qty=qty, now=now)
            print(f"[TRADE] BUY {qty} @ {px:.4f} inv={eng.player.inv} pnl={eng.pnl():.2f}")

        elif k in ("s", "S"):  # sell
            qty = 1 if k == "s" else 10
            px = eng.sell(qty=qty, now=now)
            print(f"[TRADE] SELL {qty} @ {px:.4f} inv={eng.player.inv} pnl={eng.pnl():.2f}")

        elif k in ("f", "F"):  # flatten
            if eng.player.inv > 0:
                px = eng.sell(qty=eng.player.inv, now=now)
                print(f"[TRADE] FLATTEN SELL @ {px:.4f} inv={eng.player.inv} pnl={eng.pnl():.2f}")
            elif eng.player.inv < 0:
                px = eng.buy(qty=-eng.player.inv, now=now)
                print(f"[TRADE] FLATTEN BUY @ {px:.4f} inv={eng.player.inv} pnl={eng.pnl():.2f}")

        # --- market tick ---
        eng.tick(now)

        # --- pull new news + inject shocks (gated) ---
        events = fetch_new_news_predictions(symbol_id, last_news_id)
        for news_id, headline, direction, impact in events:
            last_news_id = max(last_news_id, news_id)

            # Gate low-signal headlines (prevents runaway drift)
            if direction == 0 or impact < 0.15:
                continue

            eng.add_news(direction=direction, impact=impact, now=now)
            print(f"\n[NEWS] id={news_id} dir={direction} impact={impact:.3f} :: {headline}")

        # --- print status ~ every 0.5s ---
        if now - last_print > 0.5:
            bid, ask, spr, imp = eng.quotes(now)
            print(
                f"mid={eng.mid:.4f} bid={bid:.4f} ask={ask:.4f} "
                f"inv={eng.player.inv} cash={eng.player.cash:.2f} pnl={eng.pnl():.2f} "
                f"activeImpact~{imp:.3f}"
            )
            last_print = now

        time.sleep(eng.dt)


        # 2) pull new news from DB and add shocks
        events = fetch_new_news_predictions(symbol_id, last_news_id)
        for news_id, headline, direction, impact in events:
            last_news_id = max(last_news_id, news_id)
            eng.add_news(direction=direction, impact=impact, now=now)
            print(f"\n[NEWS] id={news_id} dir={direction} impact={impact:.3f} :: {headline}")

        # 3) print status ~ every 0.5s
        if now - last_print > 0.5:
            bid, ask, spr, imp = eng.quotes(now)
            print(
                f"mid={eng.mid:.4f} bid={bid:.4f} ask={ask:.4f} "
                f"inv={eng.player.inv} cash={eng.player.cash:.2f} pnl={eng.pnl():.2f} "
                f"activeImpact~{imp:.3f}"
            )
            last_print = now

        time.sleep(eng.dt)

if __name__ == "__main__":
    main()
