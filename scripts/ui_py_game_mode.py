import time
import pygame
from sqlalchemy import create_engine, text
from mode_a_engine import ModeAEngine
from dataclasses import dataclass

DB = "sqlite:///data/db/news.db"
db = create_engine(DB)

SYMBOL = "AAPL"

# GAME SETTINGS
ROUND_SECONDS = 90
DT = 0.05

NEWS_INTERVAL_SEC = 5.0
MIN_IMPACT = 0.3
NEWS_POOL_SIZE = 300

INV_PENALTY_LAMBDA = 0.02
INV_PENALTY_POWER = 1.3

# CANDLE SETTINGS (derived from eng.mid ticks)
CANDLE_INTERVAL = 0.5  # seconds per candle (try 0.5 or 0.2 for faster candles)
CANDLE_WINDOW = 500    # how many candles to display
CANDLE_MAX_KEEP = 300   # internal buffer


def inv_penalty(inv: int) -> float:
    return INV_PENALTY_LAMBDA * (abs(inv) ** INV_PENALTY_POWER)


def get_symbol_id(symbol: str) -> int:
    with db.begin() as conn:
        row = conn.execute(text("SELECT id FROM symbols WHERE symbol=:s"), {"s": symbol}).fetchone()
    if not row:
        raise RuntimeError(f"Symbol {symbol} not found in symbols table.")
    return int(row[0])


def fetch_scored_pool(symbol_id: int, limit: int):
    with db.begin() as conn:
        rows = conn.execute(text("""
            SELECT n.id, n.headline, p.direction, p.impact_score
            FROM news_items n
            JOIN news_predictions p ON p.news_id = n.id
            WHERE n.symbol_id = :sid
            ORDER BY n.id DESC
            LIMIT :lim
        """), {"sid": symbol_id, "lim": limit}).fetchall()

    pool = [(int(r[0]), r[1], int(r[2]), float(r[3])) for r in rows][::-1]
    pool = [x for x in pool if x[2] != 0 and x[3] >= MIN_IMPACT]
    return pool


def flatten(eng: ModeAEngine, now: float):
    if eng.player.inv > 0:
        eng.sell(qty=eng.player.inv, now=now)
    elif eng.player.inv < 0:
        eng.buy(qty=-eng.player.inv, now=now)


def wrap_text(text_s: str, font, max_width: int):
    """Simple word-wrap for pygame text surfaces."""
    words = text_s.split(" ")
    lines = []
    cur = ""
    for w in words:
        test = (cur + " " + w).strip()
        if font.size(test)[0] <= max_width:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


# =========================
# Candlesticks (from ticks)
# =========================
@dataclass
class Candle:
    t0: float
    o: float
    h: float
    l: float
    c: float


def update_candles(candles, now, price, interval_sec=1.0, max_candles=300):
    if not candles:
        t0 = now - (now % interval_sec)
        candles.append(Candle(t0=t0, o=price, h=price, l=price, c=price))
        return

    cur = candles[-1]
    if now < cur.t0 + interval_sec:
        cur.h = max(cur.h, price)
        cur.l = min(cur.l, price)
        cur.c = price
    else:
        t0 = now - (now % interval_sec)
        candles.append(Candle(t0=t0, o=price, h=price, l=price, c=price))
        if len(candles) > max_candles:
            del candles[: len(candles) - max_candles]


def draw_candles(screen, candles, rect, window=60):
    if len(candles) < 2:
        return

    view = candles[-window:] if len(candles) > window else candles
    hi = max(c.h for c in view)
    lo = min(c.l for c in view)
    if hi == lo:
        hi += 1e-6

    def y_of(p):
        return rect.y + (hi - p) * rect.height / (hi - lo)

    n = len(view)
    w = max(3, rect.width // max(1, n))
    gap = 1
    body_w = max(2, w - gap)

    pygame.draw.rect(screen, (60, 60, 70), rect, 1)

    for i, c in enumerate(view):
        x = rect.x + i * w + (w - body_w) // 2

        y_h = y_of(c.h)
        y_l = y_of(c.l)
        y_o = y_of(c.o)
        y_c = y_of(c.c)

        # wick
        pygame.draw.line(
            screen, (180, 180, 190),
            (x + body_w // 2, y_h),
            (x + body_w // 2, y_l),
            1
        )

        # body
        top = min(y_o, y_c)
        bot = max(y_o, y_c)
        body_h = max(1, int(bot - top))

        up = c.c >= c.o
        color = (90, 220, 140) if up else (240, 90, 90)
        pygame.draw.rect(screen, color, pygame.Rect(x, int(top), body_w, body_h))

    # price labels
    font = pygame.font.SysFont("consolas", 16)
    screen.blit(font.render(f"{hi:.2f}", True, (200, 200, 210)), (rect.x + 6, rect.y + 4))
    screen.blit(font.render(f"{lo:.2f}", True, (200, 200, 210)), (rect.x + 6, rect.y + rect.height - 22))


def main():
    pygame.init()
    W, H = 1100, 600
    screen = pygame.display.set_mode((W, H))
    pygame.display.set_caption("Mode A - News Trader (Headline Only)")
    clock = pygame.time.Clock()

    font_big = pygame.font.SysFont("consolas", 28)
    font = pygame.font.SysFont("consolas", 22)
    font_small = pygame.font.SysFont("consolas", 18)

    sid = get_symbol_id(SYMBOL)
    eng = ModeAEngine(mid0=200.0, dt=DT)

    # candles
    candles = []

    # round state
    round_start = time.time()
    round_end = round_start + ROUND_SECONDS
    risk_cost = 0.0
    prev_now = round_start

    # news forcing
    news_pool = fetch_scored_pool(sid, NEWS_POOL_SIZE)
    pool_i = 0
    next_news_ts = round_start + NEWS_INTERVAL_SEC
    last_headline = "Waiting for first headline..."

    running = True
    while running:
        now = time.time()

        # end round?
        if now >= round_end:
            running = False

        # accumulate risk cost over time
        dt_real = now - prev_now
        prev_now = now
        risk_cost += inv_penalty(eng.player.inv) * dt_real

        # handle inputs/events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q:
                    return
                if event.key == pygame.K_b:      # buy 1
                    eng.buy(qty=1, now=now)
                if event.key == pygame.K_s:      # sell 1
                    eng.sell(qty=1, now=now)
                if event.key == pygame.K_f:      # flatten
                    flatten(eng, now)
                if event.key == pygame.K_UP:     # buy 10
                    eng.buy(qty=10, now=now)
                if event.key == pygame.K_DOWN:   # sell 10
                    eng.sell(qty=10, now=now)

        # force headline every 15s (apply shock, but DO NOT show direction/impact in UI)
        if now >= next_news_ts:
            if not news_pool or pool_i >= len(news_pool):
                news_pool = fetch_scored_pool(sid, NEWS_POOL_SIZE)
                pool_i = 0

            if news_pool:
                nid, headline, direction, impact = news_pool[pool_i]
                pool_i += 1
                eng.add_news(direction=direction, impact=impact, now=now)
                last_headline = headline
            else:
                last_headline = f"No scored news available for {SYMBOL}."

            next_news_ts += NEWS_INTERVAL_SEC

        # tick market
        eng.tick(now)

        # update candles from mid
        update_candles(
            candles=candles,
            now=now,
            price=eng.mid,
            interval_sec=CANDLE_INTERVAL,
            max_candles=CANDLE_MAX_KEEP,
        )

        # compute display stats
        bid, ask, spr, imp = eng.quotes(now)
        pnl = eng.pnl()
        score = pnl - risk_cost
        t_left = max(0.0, round_end - now)

        # draw
        screen.fill((18, 18, 22))

        # header
        title = font_big.render(f"MODE A  |  {SYMBOL}  |  time left: {t_left:0.1f}s", True, (235, 235, 245))
        screen.blit(title, (20, 18))

        # candlestick chart area
        chart_rect = pygame.Rect(20, 70, 1060, 250)
        draw_candles(screen, candles, chart_rect, window=CANDLE_WINDOW)

        # price panel
        y0 = 335
        screen.blit(font.render(f"mid: {eng.mid:0.4f}", True, (220, 220, 220)), (20, y0))
        screen.blit(font.render(f"bid: {bid:0.4f}", True, (220, 220, 220)), (20, y0 + 32))
        screen.blit(font.render(f"ask: {ask:0.4f}", True, (220, 220, 220)), (20, y0 + 64))

        # position panel
        x1 = 360
        screen.blit(font.render(f"inv: {eng.player.inv}", True, (220, 220, 220)), (x1, y0))
        screen.blit(font.render(f"cash: {eng.player.cash:0.2f}", True, (220, 220, 220)), (x1, y0 + 32))
        screen.blit(font.render(f"pnl:  {pnl:0.2f}", True, (220, 220, 220)), (x1, y0 + 64))
        screen.blit(font.render(f"score:{score:0.2f}", True, (220, 220, 220)), (x1, y0 + 96))

        # headline panel (ONLY headline)
        hx, hy = 20, 430
        screen.blit(font_big.render("HEADLINE", True, (235, 235, 245)), (hx, hy))
        max_w = W - 40
        lines = wrap_text(last_headline, font, max_w)
        for i, line in enumerate(lines[:3]):  # limit lines to fit screen
            surf = font.render(line, True, (245, 245, 245))
            screen.blit(surf, (hx, hy + 40 + i * 26))

        # controls
        cy = H - 34
        screen.blit(
            font_small.render("Controls: b=buy1  s=sell1  f=flatten  ↑=buy10  ↓=sell10  q=quit", True, (190, 190, 200)),
            (20, cy)
        )

        pygame.display.flip()
        clock.tick(60)

    # round over
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
