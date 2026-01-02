import math
import random
from dataclasses import dataclass
from typing import List, Dict, Optional

@dataclass
class Shock:
    symbol: Optional[str]     # None => sector/global shock
    sector: Optional[str]     # None if symbol-specific
    direction: int            # -1, 0, +1
    impact: float             # 0..1
    created_ts: int           # unix seconds

def exp_decay(age_sec: float, half_life_sec: float) -> float:
    # exp(-lambda * t) with lambda = ln(2)/half_life
    if half_life_sec <= 0:
        return 0.0
    lam = math.log(2.0) / half_life_sec
    return math.exp(-lam * age_sec)

def tick_update_prices(
    prices: Dict[str, float],
    shocks: List[Shock],
    now_ts: int,
    dt_sec: int = 60,
    sigma_per_min: float = 0.0015,
    alpha: float = 0.003,
    half_life_min: float = 9.0,
) -> Dict[str, float]:
    """
    Updates each symbol price in-place style:
    P_{t+1} = P_t * exp( drift + noise )
    drift = sum_i alpha * dir_i * impact_i * decay(age)
    noise ~ N(0, sigma_per_min) per minute
    """
    half_life_sec = half_life_min * 60.0
    # scale noise for dt (sigma is per 60s)
    sigma = sigma_per_min * math.sqrt(dt_sec / 60.0)

    out = {}
    for sym, P in prices.items():
        drift = 0.0
        for sh in shocks:
            if sh.direction == 0 or sh.impact <= 0:
                continue
            age = max(0, now_ts - sh.created_ts)
            decay = exp_decay(age, half_life_sec)
            if sh.symbol is not None:
                if sh.symbol != sym:
                    continue
                drift += alpha * sh.direction * sh.impact * decay
            else:
                # sector/global shocks: apply if sector matches (if you track sectors per symbol)
                # For now: treat as global shock
                drift += 0.6 * alpha * sh.direction * sh.impact * decay

        eps = random.gauss(0.0, 1.0)
        r = drift + sigma * eps
        out[sym] = P * math.exp(r)

    return out
