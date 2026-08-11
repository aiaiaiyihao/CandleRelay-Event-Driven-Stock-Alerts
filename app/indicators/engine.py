from collections import defaultdict, deque
from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

from app.domain.events import MarketEvent


@dataclass(frozen=True)
class IndicatorSnapshot:
    values: dict[str, Decimal | None]

    def get(self, indicator: str, period: int) -> Decimal | None:
        return self.values.get(f"{indicator}_{period}")


class IndicatorEngine:
    """Maintains bounded rolling state independently per symbol and timeframe."""

    def __init__(self, max_period: int = 500):
        if max_period < 1:
            raise ValueError("max_period must be positive")
        self._max_period = max_period
        self._closes: dict[tuple[str, str], deque[Decimal]] = defaultdict(
            lambda: deque(maxlen=max_period)
        )
        self._volumes: dict[tuple[str, str], deque[int]] = defaultdict(
            lambda: deque(maxlen=max_period)
        )

    def update(self, event: MarketEvent, periods: Iterable[int]) -> IndicatorSnapshot:
        requested = sorted(set(periods))
        if any(period < 1 or period > self._max_period for period in requested):
            raise ValueError(f"periods must be between 1 and {self._max_period}")

        key = (event.symbol, event.timeframe)
        previous_closes = self._closes[key]
        previous_volumes = self._volumes[key]
        closes_with_current = [*previous_closes, event.close]
        values: dict[str, Decimal | None] = {}

        for period in requested:
            values[f"sma_{period}"] = self._average_last(closes_with_current, period)
            volume_average = self._average_last(previous_volumes, period)
            values[f"volume_ratio_{period}"] = (
                Decimal(event.volume) / volume_average
                if volume_average not in (None, Decimal(0))
                else None
            )

        previous_closes.append(event.close)
        previous_volumes.append(event.volume)
        return IndicatorSnapshot(values=values)

    @staticmethod
    def _average_last(values, period: int) -> Decimal | None:
        if len(values) < period:
            return None
        window = list(values)[-period:]
        return sum(Decimal(value) for value in window) / Decimal(period)

