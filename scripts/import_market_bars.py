import argparse

from app.core.config import SessionLocal
from app.services.market_bar_service import import_market_bars_csv


def main() -> None:
    parser = argparse.ArgumentParser(description="Import normalized OHLCV CSV bars")
    parser.add_argument("path")
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--timeframe", default="1d")
    parser.add_argument("--source", default="csv")
    args = parser.parse_args()

    with SessionLocal() as session:
        result = import_market_bars_csv(
            args.path,
            symbol=args.symbol,
            timeframe=args.timeframe,
            source=args.source,
            session=session,
        )
    print(f"Imported {result.imported} bars; skipped {result.skipped} duplicates.")


if __name__ == "__main__":
    main()

