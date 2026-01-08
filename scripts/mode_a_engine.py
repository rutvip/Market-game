import math, random, time
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class NewsShock:
    direction: int      # -1,0,+1
    impact: float       # 0..1
    start_ts: float     # seconds (time.time())

@dataclass  # no need of init, repr, eq overrides
class Player:
    cash: float = 0.0
    inv: int = 0

class ModeAEngine:
    def __init__(
        self,
        mid0: float = 200.0,
        dt: float = 0.05,
        base_sigma: float = 0.02,      # per sqrt(second)
        alpha: float = 0.15,           # drift scale per second
        half_life: float = 5.0,        # seconds (faster decay = more HFT feel)
        base_spread: float = 0.02,
        fee_per_share: float = 0.001,
        slip0: float = 0.03            # more slippage during high-impact news
    ):
        self.mid = float(mid0)
        self.dt = float(dt)
        self.base_sigma = float(base_sigma)
        self.alpha = float(alpha)
        self.half_life = float(half_life)
        self.base_spread = float(base_spread)
        self.fee = float(fee_per_share)
        self.slip0 = float(slip0)

        self.shocks: List[NewsShock] = []
        self.player = Player()

    def _decay(self, age: float) -> float:
        # exponential decay with half-life
        lam = math.log(2.0) / self.half_life
        return math.exp(-lam * age)

    def _impact_level(self, now: float) -> float:
        """
        Soft-sum of active shocks (clamped to 1.0).
        This feels more realistic than max() when multiple news items cluster.
        """
        level = 0.0
        for s in self.shocks:
            age = max(0.0, now - s.start_ts)
            level += s.impact * self._decay(age)
        return min(1.0, level)

    def add_news(self, direction: int, impact: float, now: Optional[float] = None) -> None:
        if now is None:
            now = time.time()
        self.shocks.append(
            NewsShock(direction=int(direction), impact=float(impact), start_ts=float(now))
        )

    def quotes(self, now: Optional[float] = None):
        if now is None:
            now = time.time()

        imp = self._impact_level(now)
        spread = self.base_spread * (1.0 + 3.0 * imp)
        bid = self.mid - spread / 2.0
        ask = self.mid + spread / 2.0
        return bid, ask, spread, imp

    def _cleanup_shocks(self, now: float) -> None:
        # after ~6 half-lives, decay is ~1/64 (negligible)
        cutoff = now - (6.0 * self.half_life)
        if len(self.shocks) > 200:
            self.shocks = [s for s in self.shocks if s.start_ts >= cutoff]

    def tick(self, now: Optional[float] = None) -> float:
        if now is None:
            now = time.time()

        self._cleanup_shocks(now)

        # news drift sum (directional), then clamp to prevent runaway trends
        drift = 0.0
        for s in self.shocks:
            if s.direction == 0 or s.impact <= 0:
                continue
            age = max(0.0, now - s.start_ts)
            drift += self.alpha * s.direction * s.impact * self._decay(age)

        drift = max(-0.25, min(0.25, drift))  # clamp drift per second

        # volatility scales with active impact (including direction=0 news)
        _, _, _, imp = self.quotes(now)
        sigma = self.base_sigma * (1.0 + 2.5 * imp)

        eps = random.gauss(0.0, 1.0)
        d_mid = drift * self.dt + sigma * math.sqrt(self.dt) * eps
        self.mid = max(0.01, self.mid + d_mid)

        return self.mid

    def buy(self, qty: int = 1, now: Optional[float] = None) -> float:
        if now is None:
            now = time.time()

        bid, ask, _, imp = self.quotes(now)
        slippage = self.slip0 * imp
        px = ask + slippage

        self.player.cash -= px * qty + self.fee * qty
        self.player.inv += qty
        return px

    def sell(self, qty: int = 1, now: Optional[float] = None) -> float:
        if now is None:
            now = time.time()

        bid, ask, _, imp = self.quotes(now)
        slippage = self.slip0 * imp
        px = bid - slippage

        self.player.cash += px * qty - self.fee * qty
        self.player.inv -= qty
        return px

    def pnl(self) -> float:
        return self.player.cash + self.player.inv * self.mid
