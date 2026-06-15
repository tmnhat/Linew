#!/usr/bin/env python3
"""
Script to fetch price data and run predictions for all symbols.
Run manually or via cron.
"""
import asyncio
import sys
import os

sys.path.insert(0, '/app')
os.chdir('/app')

async def main():
    from app.core.database import get_db_context
    from app.prediction.data_fetcher import fetch_history, fetch_current_price
    from app.prediction.tasks import task_run_full_prediction
    from app.prediction.config import DEFAULT_SYMBOLS, HISTORY_PERIOD

    print("=== LINEW PREDICTION SYSTEM - DATA FETCH ===")
    print()

    # Fetch prices for all symbols
    print("1. Fetching historical prices...")
    async with get_db_context() as session:
        for symbol_info in DEFAULT_SYMBOLS:
            symbol = symbol_info["symbol"]
            print(f"   Fetching {symbol}...")
            try:
                records = await fetch_history(session, symbol, period=HISTORY_PERIOD)
                print(f"   -> Got {len(records)} records for {symbol}")
            except Exception as e:
                print(f"   -> Error fetching {symbol}: {e}")

    print()
    print("2. Fetching current prices...")
    for symbol_info in DEFAULT_SYMBOLS:
        symbol = symbol_info["symbol"]
        try:
            data = await fetch_current_price(symbol)
            if data:
                print(f"   {symbol}: ${data['price']:,.2f} ({data['change_pct']:+.2f}%)")
            else:
                print(f"   {symbol}: Failed to fetch")
        except Exception as e:
            print(f"   {symbol}: Error - {e}")

    print()
    print("3. Running predictions...")
    result = await task_run_full_prediction()

    print(f"   Predicted: {result.get('predicted', 0)} symbols")
    print(f"   Errors: {len(result.get('errors', []))}")

    for error in result.get('errors', []):
        print(f"      - {error}")

    print()
    print("=== DONE ===")

if __name__ == "__main__":
    asyncio.run(main())
