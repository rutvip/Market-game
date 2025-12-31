import joblib
import numpy as np
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

MODEL = "ProsusAI/finbert"
tok = AutoTokenizer.from_pretrained(MODEL)
mdl = AutoModelForSequenceClassification.from_pretrained(MODEL)
mdl.eval()

impact_model = joblib.load("data/models/impact_xgb.joblib")

def finbert_feats(text: str):
    with torch.no_grad():
        enc = tok([text], padding=True, truncation=True, max_length=256, return_tensors="pt")
        probs = torch.softmax(mdl(**enc).logits, dim=-1).cpu().numpy()[0]
    p_neg, p_neu, p_pos = probs[0], probs[1], probs[2]
    sentiment_score = float(p_pos - p_neg)
    return float(p_pos), float(p_neg), float(p_neu), sentiment_score

def predict_y(headline: str, hour=10, dow=1):
    p_pos, p_neg, p_neu, s = finbert_feats(headline)
    X = np.array([[s, p_pos, p_neg, p_neu, hour, dow]], dtype=float)
    y_hat = float(impact_model.predict(X)[0])
    return s, y_hat

if __name__ == "__main__":
    headline = "Apple beats earnings and raises guidance; shares jump"
    s, y_hat = predict_y(headline, hour=10, dow=1)
    print("headline:", headline)
    print("sentiment_score:", s)
    print("predicted y (abs abnormal log-return):", y_hat)

    # Convert y -> impact_score 0..1 (tune denominator)
    impact = max(0.0, min(1.0, y_hat / 0.02))  # 2% abnormal move => impact 1
    print("impact_score(0..1):", impact)
