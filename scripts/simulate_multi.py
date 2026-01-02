import time
from game_engine import Shock, tick_update_prices

prices = {"AAPL": 200.0}
now = int(time.time())

# Your sample: direction negative, impact ~0.357
shocks = [Shock(symbol="AAPL", sector=None, direction=-1, impact=0.357, created_ts=now)]

for i in range(30):  # 30 minutes
    prices = tick_update_prices(prices, shocks, now_ts=now + i*60)
    print(prices)
