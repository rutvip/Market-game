import time
import pandas as pd
from sqlalchemy import create_engine, text
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

engine = create_engine("sqlite:///data/db/news.db")
MODEL = "ProsusAI/finbert"

tok = AutoTokenizer.from_pretrained(MODEL)
mdl = AutoModelForSequenceClassification.from_pretrained(MODEL)
mdl.eval()

def finbert_probs(texts):
    with torch.no_grad():
        enc = tok(texts, padding=True, truncation=True, max_length=256, return_tensors="pt")
        logits = mdl(**enc).logits
        probs = torch.softmax(logits, dim=-1).cpu().numpy()
    # ProsusAI/finbert label order is typically [negative, neutral, positive]
    return probs

def main(batch=16):
    with engine.begin() as conn:
        rows = conn.execute(text("""
            SELECT id, headline, body, source, published_at
            FROM news_items
            WHERE id NOT IN (SELECT news_id FROM news_features)
            AND published_at > 0
        """)).fetchall()

    if not rows:
        print("No new news_items to featurize.")
        return

    df = pd.DataFrame(rows, columns=["news_id","headline","body","source","published_at"])
    df["text"] = (df["headline"].fillna("") + ". " + df["body"].fillna("")).str.slice(0, 2000)

    out = []
    for i in range(0, len(df), batch):
        chunk = df.iloc[i:i+batch]
        probs = finbert_probs(chunk["text"].tolist())
        for (news_id, src, pub), p in zip(chunk[["news_id","source","published_at"]].itertuples(index=False), probs):
            p_neg, p_neu, p_pos = float(p[0]), float(p[1]), float(p[2])
            s = p_pos - p_neg
            t = time.gmtime(int(pub))
            out.append((int(news_id), p_pos, p_neg, p_neu, s, src, t.tm_hour, t.tm_wday, 0))

    with engine.begin() as conn:
        for row in out:
            conn.execute(text("""
                INSERT OR REPLACE INTO news_features
                (news_id, p_pos, p_neg, p_neu, sentiment_score, source, hour, dow, is_market_hours)
                VALUES (:nid,:pp,:pn,:pneu,:s,:src,:hr,:dw,:mh)
            """), {
                "nid": row[0], "pp": row[1], "pn": row[2], "pneu": row[3],
                "s": row[4], "src": row[5], "hr": row[6], "dw": row[7], "mh": row[8]
            })

    print(f"Wrote features for {len(out)} items.")

if __name__ == "__main__":
    main()
