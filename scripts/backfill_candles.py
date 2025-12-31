import time
from datetime import datetime, timezone
import pandas as pd
from pandas_datareader import data as pdr
from sqlalchemy import create_engine, text

engine = create_engine("sqlite:///data/db/news.db")

def unix_utc_midnight(dt_index):
    # dt_index is a pandas Timestamp
    dt = datetime(dt_index.year, dt_index.month, dt_index.day, tzinfo=timezone.utc)
    return int(dt.timestamp())

def get_symbols():
    with engine.begin() as conn:
        return conn.execute(text("SELECT id, symbol FROM symbols")).fetchall()

def fetch_daily_stooq(symbol: str, start="2024-01-01"):
    # Stooq uses e.g. "aapl.us"
    stooq_symbol = f"{symbol.lower()}.us"
    df = pdr.DataReader(stooq_symbol, "stooq", start=start)
    # df index is date, columns: Open High Low Close Volume
    df = df.sort_index()
    return df

def main():
    symbols = get_symbols()
    for symbol_id, sym in symbols:
        # skip non-US equities if you have them
        if sym.upper() == "SPY":
            stooq_sym = "spy.us"
        else:
            stooq_sym = f"{sym.lower()}.us"

        try:
            df = pdr.DataReader(stooq_sym, "stooq", start="2024-01-01").sort_index()
        except Exception as e:
            print("FAILED", sym, e)
            continue

        with engine.begin() as conn:
            for dt, row in df.iterrows():
                ts = unix_utc_midnight(dt)
                close = float(row["Close"])
                vol = float(row.get("Volume", 0.0))
                conn.execute(text("""
                    INSERT OR REPLACE INTO price_candles(symbol_id, ts, close, volume)
                    VALUES(:sid,:ts,:c,:v)
                """), {"sid": int(symbol_id), "ts": int(ts), "c": close, "v": vol})

        print("OK", sym, len(df))

if __name__ == "__main__":
    main()
