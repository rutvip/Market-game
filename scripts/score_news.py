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

# XGB impact model
impact_model = joblib.load("data/models/impact_xgb.joblib")

def finbert_probs(text: str):
    with torch.no_grad():
        enc = tok([text], padding=True, truncation=True, max_length=256, return_tensors="pt")
        probs = torch.softmax(mdl(**enc).logits, dim=-1).cpu().numpy()[0]
    # [neg, neu, pos]
    return float(probs[2]), float(probs[0]), float(probs[1])  # p_pos, p_neg, p_neu

def direction_from_headline(headline: str) -> int:
    """
    Simple v1 rule-based direction (better than trusting FinBERT sign for short headlines).
    You can expand this later.
    """
    h = (headline or "").lower()
    pos = ["beats", "beat", "raises guidance", "upgrades", "record revenue", "surges", "wins", "strong demand"]
    neg = ["misses", "miss", "cuts guidance", "downgrades", "lawsuit", "probe", "recall", "plunges", "falls", "weak demand"]
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

    now = int(time.time())
    wrote = 0

    for news_id, headline, body, source, pub in rows:
        text_in = f"{headline}. {body}".strip()

        p_pos, p_neg, p_neu = finbert_probs(text_in)
        sentiment_score = p_pos - p_neg

        # Your XGB expects: [sentiment_score, p_pos, p_neg, p_neu, hour, dow]
        # For scoring, hour/dow can be taken from UTC published_at
        t = time.gmtime(int(pub))
        hour, dow = t.tm_hour, t.tm_wday

        X = np.array([[sentiment_score, p_pos, p_neg, p_neu, hour, dow]], dtype=float)
        y_hat = float(impact_model.predict(X)[0])
        impact = max(0.0, min(1.0, y_hat / IMPACT_DENOM))

        direction = direction_from_headline(headline)
        # if rules can't decide, fallback to FinBERT sign (soft)
        if direction == 0:
            direction = +1 if sentiment_score > 0.05 else (-1 if sentiment_score < -0.05 else 0)

        with engine.begin() as conn:
            conn.execute(text("""
                INSERT OR REPLACE INTO news_predictions
                (news_id, predicted_y, impact_score, direction, created_at)
                VALUES(:nid,:y,:imp,:dir,:ts)
            """), {"nid": int(news_id), "y": y_hat, "imp": impact, "dir": int(direction), "ts": now})
        wrote += 1

    print("Scored", wrote, "news items.")

if __name__ == "__main__":
    main()
