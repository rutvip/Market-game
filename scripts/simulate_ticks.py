import math, random

def step_price(P, direction, impact, age_min, alpha=0.003, lam=0.08, sigma=0.0015):
    """
    P: current price
    direction: -1/0/+1
    impact: 0..1
    age_min: minutes since headline started affecting price
    alpha: headline strength
    lam: decay
    sigma: noise
    """
    eps = random.gauss(0, 1)
    drift = alpha * direction * impact * math.exp(-lam * age_min)
    r = drift + sigma * eps
    return P * math.exp(r)

def simulate(P0=200.0, direction=-1, impact=0.357, minutes=30):
    P = P0
    path = [P]
    for t in range(minutes):
        P = step_price(P, direction, impact, age_min=t)
        path.append(P)
    return path

if __name__ == "__main__":
    path = simulate()
    print("start:", path[0], "end:", path[-1], "pct:", (path[-1]/path[0]-1)*100)
