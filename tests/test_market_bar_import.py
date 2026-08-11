from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.core.config import Base
from app.models.MarketBar import MarketBar
from app.services.market_bar_service import import_market_bars_csv


def test_imports_validated_csv_and_skips_duplicates(tmp_path):
    csv_path = tmp_path / "nvda.csv"
    csv_path.write_text(
        "timestamp,open,high,low,close,volume\n"
        "2026-08-01T20:00:00Z,100,105,99,104,1000\n"
        "2026-08-02T20:00:00Z,104,106,101,102,1200\n",
        encoding="utf-8",
    )
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()

    first = import_market_bars_csv(csv_path, "nvda", "1d", "fixture", session)
    second = import_market_bars_csv(csv_path, "nvda", "1d", "fixture", session)

    assert first.imported == 2
    assert first.skipped == 0
    assert second.imported == 0
    assert second.skipped == 2
    bars = session.execute(select(MarketBar).order_by(MarketBar.timestamp)).scalars().all()
    assert [bar.symbol for bar in bars] == ["NVDA", "NVDA"]
    assert [bar.close for bar in bars] == [104, 102]
    session.close()
