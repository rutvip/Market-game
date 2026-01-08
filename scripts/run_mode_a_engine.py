import time
from mode_a_engine import ModeAEngine

eng = ModeAEngine(mid0=200.0)

# Add a negative news shock, similar magnitude to your earlier example
eng.add_news(direction=-1, impact=0.35)

t0 = time.time()
next_trade = t0 + 1.0

for i in range(400):  # 400 ticks * 50ms = 20s
    now = time.time()
    eng.tick(now)

    # dumb strategy: sell once after 1s, buy back after 10s
    if i == 20:
        px = eng.sell(qty=10, now=now)
        print("SELL 10 @", round(px, 4))
    if i == 200:
        px = eng.buy(qty=10, now=now)
        print("BUY 10 @", round(px, 4))

    if i % 20 == 0:
        bid, ask, spr, imp = eng.quotes(now)
        print("mid", round(eng.mid,4), "inv", eng.player.inv, "pnl", round(eng.pnl(),4), "imp", round(imp,3))

    time.sleep(0.05)

print("FINAL PnL:", eng.pnl())
