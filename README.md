# News Impact Trader (Toy Project)

This repository is a hands-on toy project that:
1) pulls company news and price candles,
2) featurizes news with FinBERT sentiment,
3) trains a simple impact regressor (XGBoost),
4) scores news to produce direction + impact, and
5) runs a Python trading game (Mode A) that simulates price ticks and injects news shocks.

The goal is that anyone new can clone this repo, run the pipeline end-to-end, and play the Python version locally.

---

## Requirements

This project uses the following Python packages:

- pandas
- numpy
- requests
- sqlalchemy
- tqdm
- scikit-learn
- xgboost
- transformers
- torch
- pygame

Recommended Python version: 3.10 or 3.11.

---


## Repository structure


data/
  db/ # sqlite database lives here (you need to create this folder)
models/ # trained models saved here
scripts/
  init_db.py
  seed_sym.py
  backfill_news.py
  backfill_candles.py
  finbert_features.py
  build_labels.py
  train_regressor.py
  test_one_news.py
  add_predictions_label.py
  score_news.py
  simulate_ticks.py
  simulate_multi.py
  game_engine.py
  mode_a_engine.py
  run_game_symbol.py
  run_mode_a_engine.py
  run_round_mode_a.py
  ui_py_game_mode.py
requirements.txt


---

## Setup

### 1) Clone the repository

git clone https://github.com/rutvip/Market-game.git

### 2) Create required folders

You must create the database directory before initializing the DB.

Mac/Linux:

mkdir -p data/db
mkdir -p data/models


Windows (PowerShell):

mkdir data\db
mkdir data\models

### 3) Create and activate a virtual environment

Windows (PowerShell):

python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt


Mac/Linux:

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

Finnhub API key

This project expects a Finnhub API token in an environment variable called FINNHUB_TOKEN.

1) Create a token

Create an account at Finnhub and generate an API key.

2) Export it as an environment variable

Windows (PowerShell):

$env:FINNHUB_TOKEN="YOUR_TOKEN_HERE"


Mac/Linux:

export FINNHUB_TOKEN="YOUR_TOKEN_HERE"

End-to-end run order (from empty DB to playable UI)

Run these scripts in order.

Step 1: Initialize the database schema
python scripts/init_db.py

Step 2: Seed symbols

This populates the symbols table with your initial universe.

python scripts/seed_sym.py

Step 3: Backfill news

Fetches news articles and stores them in news_items.

python scripts/backfill_news.py

### Step 4: Backfill candles

Fetches price candles and stores them in price_candles.

python scripts/backfill_candles.py


## Notes:

If you see 401 Unauthorized, your token is missing/incorrect.

If you see 403 Forbidden, your Finnhub plan may not allow the candle resolution/time range you are requesting.

Step 5: Build FinBERT features

Runs FinBERT on the stored news and writes features to news_features.

python scripts/finbert_features.py

Step 6: Build supervised labels (y)

Creates training rows in train_rows.

python scripts/build_labels.py

Step 7: Train the impact regressor

Trains XGBoost and saves the model to data/models/impact_xgb.joblib.

python scripts/train_regressor.py

Step 8: Quick sanity check on one headline
python scripts/test_one_news.py

Step 9: Add predictions labels/table (if your flow uses it)
python scripts/add_predictions_label.py

Step 10: Score news (direction + impact)

Writes predicted direction and impact into the DB (for example into news_predictions).

python scripts/score_news.py

Run the game (UI)

After scoring news, run the pygame UI version:

python scripts/ui_py_game_mode.py


Typical controls:

b: buy 1

s: sell 1

Up Arrow: buy 10

Down Arrow: sell 10

f: flatten position

q: quit

The UI displays only the headline. Direction/impact are applied internally by the engine.

Common issues
sqlite3.OperationalError: unable to open database file

You likely did not create data/db before running init_db.py.

Fix:

Mac/Linux:

mkdir -p data/db


Windows (PowerShell):

mkdir data\db

401 Unauthorized from Finnhub

Your token is missing or incorrect. Re-export FINNHUB_TOKEN and retry.

403 Forbidden / "You don't have access to this resource"

Your Finnhub plan may not allow the candle resolution you requested. Adjust resolution/time range in scripts/backfill_candles.py or use a plan that supports it.

No new news_items to featurize

This means finbert_features.py already processed all currently ingested news. It is not an error.

## Notes

This is a toy environment meant to be simple and runnable locally.

Labels and scoring are intentionally simplified to keep the pipeline easy to follow.

The price engine is not intended to be a real market simulator; it is designed to create a responsive trading loop driven by news.




