import time
import msvcrt
from sqlalchemy import create_engine, text
from mode_a_engine import ModeAEngine

DB = "sqlite:///data/db/news.db"
db = create_engine(DB)

SYMBOL = "AMZN"

# GAME SETTINGS
ROUND_SECONDS = 30
DT = 0.05

# Forced news cadence
NEWS_INTERVAL_SEC = 15.0
MIN_IMPACT = 0.15
NEWS_POOL_SIZE = 300  # preload this many recent scored items

# risk penalty: encourages being flat like a market maker / floor trader
INV_PENALTY_LAMBDA = 0.02
INV_PENALTY_POWER = 1.3


def read_key():
    if msvcrt.kbhit():
        return msvcrt.getwch()
    return None


def get_symbol_id(symbol: str) -> int:
    with db.begin() as conn:
        row = conn.execute(text("SELECT id FROM symbols WHERE symbol=:s"), {"s": symbol}).fetchone()
    if not row:
        raise RuntimeError(f"Symbol {symbol} not found. Run seed_sym.py first.")
    return int(row[0])


def fetch_scored_pool(symbol_id: int, limit: int):
    """
    Returns list of (news_id, headline, direction, impact_score) sorted oldest->newest,
    filtered to inject-ready items.
    """
    with db.begin() as conn:
        rows = conn.execute(text("""
            SELECT n.id, n.headline, p.direction, p.impact_score
            FROM news_items n
            JOIN news_predictions p ON p.news_id = n.id
            WHERE n.symbol_id = :sid
            ORDER BY n.id DESC
            LIMIT :lim
        """), {"sid": symbol_id, "lim": limit}).fetchall()

    pool = [(int(r[0]), r[1], int(r[2]), float(r[3])) for r in rows][::-1]  # oldest->newest
    pool = [x for x in pool if x[2] != 0 and x[3] >= MIN_IMPACT]
    return pool


def inv_penalty(inv: int) -> float:
    return INV_PENALTY_LAMBDA * (abs(inv) ** INV_PENALTY_POWER)


def flatten(eng: ModeAEngine, now: float):
    if eng.player.inv > 0:
        eng.sell(qty=eng.player.inv, now=now)
    elif eng.player.inv < 0:
        eng.buy(qty=-eng.player.inv, now=now)


def main():
    round_start = time.time()
    round_end = round_start + ROUND_SECONDS

    risk_cost = 0.0
    prev_now = round_start

    sid = get_symbol_id(SYMBOL)

    eng = ModeAEngine(mid0=200.0, dt=DT)

    # Build pool for forced injections
    news_pool = fetch_scored_pool(sid, NEWS_POOL_SIZE)
    pool_i = 0
    next_news_ts = round_start + NEWS_INTERVAL_SEC

    last_print = 0.0

    print(f"\n=== MODE A ROUND: {SYMBOL} | {ROUND_SECONDS}s ===")
    print("Controls: b/B buy 1/10 | s/S sell 1/10 | f flatten | q quit")
    print(f"Forced news every {NEWS_INTERVAL_SEC:.0f}s | gate: impact >= {MIN_IMPACT}\n")

    while True:
        now = time.time()

        # accumulate risk cost over real wall-clock time
        dt_real = now - prev_now
        prev_now = now
        risk_cost += inv_penalty(eng.player.inv) * dt_real

        # round end?
        if now >= round_end:
            break

        # input
        k = read_key()
        if k in ("q", "Q"):
            print("Quit.")
            return

        if k in ("b", "B"):
            qty = 1 if k == "b" else 10
            px = eng.buy(qty=qty, now=now)
            print(f"[TRADE] BUY {qty} @ {px:.4f} inv={eng.player.inv} pnl={eng.pnl():.2f}")

        elif k in ("s", "S"):
            qty = 1 if k == "s" else 10
            px = eng.sell(qty=qty, now=now)
            print(f"[TRADE] SELL {qty} @ {px:.4f} inv={eng.player.inv} pnl={eng.pnl():.2f}")

        elif k in ("f", "F"):
            flatten(eng, now)
            print(f"[TRADE] FLATTEN inv={eng.player.inv} pnl={eng.pnl():.2f}")

        # FORCE NEWS: inject exactly once every 15 seconds
        if now >= next_news_ts:
            # refresh pool if exhausted
            if not news_pool or pool_i >= len(news_pool):
                news_pool = fetch_scored_pool(sid, NEWS_POOL_SIZE)
                pool_i = 0

            if news_pool:
                nid, headline, direction, impact = news_pool[pool_i]
                pool_i += 1

                eng.add_news(direction=direction, impact=impact, now=now)
                print(f"\n[NEWS@{int(NEWS_INTERVAL_SEC)}s] id={nid} dir={direction} impact={impact:.3f} :: {headline}")
            else:
                print(f"\n[NEWS@{int(NEWS_INTERVAL_SEC)}s] No scored news available in DB for {SYMBOL}.")

            next_news_ts += NEWS_INTERVAL_SEC

        # tick market
        eng.tick(now)

        # print status
        if now - last_print >= 0.5:
            bid, ask, spr, imp = eng.quotes(now)
            t_left = max(0.0, round_end - now)
            score = eng.pnl() - risk_cost
            print(
                f"t_left={t_left:5.1f}s mid={eng.mid:.4f} bid={bid:.4f} ask={ask:.4f} "
                f"inv={eng.player.inv:4d} pnl={eng.pnl():7.2f} risk={risk_cost:6.2f} score={score:7.2f} "
                f"impact~{imp:.3f}"
            )
            last_print = now

        time.sleep(DT)

    # round over: flatten and final score
    now = time.time()
    flatten(eng, now)
    final_pnl = eng.pnl()
    final_score = final_pnl - risk_cost

    print("\n=== ROUND OVER ===")
    print(f"Final PnL:   {final_pnl:.2f}")
    print(f"Risk Cost:   {risk_cost:.2f}")
    print(f"FINAL SCORE: {final_score:.2f}")


if __name__ == "__main__":
    main()
