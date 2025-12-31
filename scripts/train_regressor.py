import pandas as pd
from sqlalchemy import create_engine, text
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error
from xgboost import XGBRegressor
import joblib
import os

engine = create_engine("sqlite:///data/db/news.db")

def main():
    q = """
    SELECT tr.y,
           nf.sentiment_score, nf.p_pos, nf.p_neg, nf.p_neu,
           nf.hour, nf.dow
    FROM train_rows tr
    JOIN news_features nf ON nf.news_id = tr.news_id
    """
    df = pd.read_sql(text(q), engine)

    # basic cleanup
    df = df.dropna()
    y = df["y"].values
    X = df.drop(columns=["y"]).values

    X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, shuffle=False)

    model = XGBRegressor(
        n_estimators=600,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.9,
        colsample_bytree=0.9,
        random_state=42
    )
    model.fit(X_train, y_train)

    pred = model.predict(X_val)
    mae = mean_absolute_error(y_val, pred)
    print("VAL MAE:", mae)

    os.makedirs("data/models", exist_ok=True)
    joblib.dump(model, "data/models/impact_xgb.joblib")
    print("Saved: data/models/impact_xgb.joblib")

if __name__ == "__main__":
    main()
