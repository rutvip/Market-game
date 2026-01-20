# scripts/score_news.py
import time
import joblib
import numpy as np
from sqlalchemy import create_engine, text
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

engine = create_engine("sqlite:///data/db/news.db")

# FinBERT
FINBERT = "ProsusAI/finbert"
tok = AutoTokenizer.from_pretrained(FINBERT)
mdl = AutoModelForSequenceClassification.from_pretrained(FINBERT)
mdl.eval()

device = "cuda" if torch.cuda.is_available() else "cpu"
mdl.to(device)

# XGB impact model
impact_model = joblib.load("data/models/impact_xgb.joblib")

def finbert_probs(text: str):
    with torch.no_grad():
        enc = tok([text], padding=True, truncation=True, max_length=256, return_tensors="pt")
        enc = {k: v.to(device) for k, v in enc.items()}
        probs = torch.softmax(mdl(**enc).logits, dim=-1).detach().cpu().numpy()[0]
    # probs = [neg, neu, pos]
    p_neg, p_neu, p_pos = float(probs[0]), float(probs[1]), float(probs[2])
    return p_pos, p_neg, p_neu

def direction_from_headline(headline: str) -> int:
    h = (headline or "").lower()
    pos = ["beats", "beat", "raises guidance", "upgrades", "record revenue", "surges", "wins", "strong demand", "jumps", "tops estimates"]
    neg = ["misses", "miss", "cuts guidance", "downgrades", "lawsuit", "probe", "recall", "plunges", "falls", "weak demand", "misses estimates"]
    if any(p in h for p in pos): return +1
    if any(n in h for n in neg): return -1
    return 0

def main():
    # scale: 2% abnormal move => impact 1.0 (tune later)
    IMPACT_DENOM = 0.02

    with engine.begin() as conn:
        rows = conn.execute(text("""
            SELECT n.id, n.headline, COALESCE(n.body,''), n.source, n.published_at
            FROM news_items n
            WHERE n.id NOT IN (SELECT news_id FROM news_predictions)
              AND n.id IN (SELECT news_id FROM news_features)
            LIMIT 500
        """)).fetchall()

    if not rows:
        print("No unscored news found.")
        return

    now_ts = int(time.time())
    wrote = 0

    for news_id, headline, body, source, pub in rows:
        text_in = f"{headline}. {body}".strip()

        p_pos, p_neg, p_neu = finbert_probs(text_in)
        sentiment_score = p_pos - p_neg

        t = time.gmtime(int(pub))
        hour, dow = t.tm_hour, t.tm_wday

        # XGB expects: [sentiment_score, p_pos, p_neg, p_neu, hour, dow]
        X = np.array([[sentiment_score, p_pos, p_neg, p_neu, hour, dow]], dtype=float)
        y_hat = float(impact_model.predict(X)[0])

        impact = max(0.0, min(1.0, y_hat / IMPACT_DENOM))

        direction = direction_from_headline(headline)
        if direction == 0:
            direction = +1 if sentiment_score > 0.05 else (-1 if sentiment_score < -0.05 else 0)

        with engine.begin() as conn:
            conn.execute(text("""
                INSERT OR REPLACE INTO news_predictions
                (news_id, predicted_y, impact_score, direction, created_at)
                VALUES(:nid,:y,:imp,:dir,:ts)
            """), {"nid": int(news_id), "y": y_hat, "imp": impact, "dir": int(direction), "ts": now_ts})

        wrote += 1

    print(f"Scored {wrote} news items. device={device}")

if __name__ == "__main__":
    main()
