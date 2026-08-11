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
        self._ema_values: dict[tuple[str, str, int], Decimal] = {}
        self._rsi_averages: dict[
            tuple[str, str, int], tuple[Decimal, Decimal]
        ] = {}

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
            values[f"ema_{period}"] = self._next_ema(
                key,
                closes_with_current,
                event.close,
                period,
            )
            values[f"rsi_{period}"] = self._next_rsi(
                key,
                closes_with_current,
                period,
            )
            volume_average = self._average_last(previous_volumes, period)
            values[f"volume_ratio_{period}"] = (
                Decimal(event.volume) / volume_average
                if volume_average not in (None, Decimal(0))
                else None
            )

        previous_closes.append(event.close)
        previous_volumes.append(event.volume)
        return IndicatorSnapshot(values=values)

    def _next_ema(
        self,
        key: tuple[str, str],
        closes_with_current: list[Decimal],
        current_close: Decimal,
        period: int,
    ) -> Decimal | None:
        ema_key = (*key, period)
        previous_ema = self._ema_values.get(ema_key)
        if previous_ema is None:
            current_ema = self._average_last(closes_with_current, period)
        else:
            multiplier = Decimal(2) / Decimal(period + 1)
            current_ema = (
                current_close * multiplier
                + previous_ema * (Decimal(1) - multiplier)
            )
        if current_ema is not None:
            self._ema_values[ema_key] = current_ema
        return current_ema

    def _next_rsi(
        self,
        key: tuple[str, str],
        closes_with_current: list[Decimal],
        period: int,
    ) -> Decimal | None:
        rsi_key = (*key, period)
        averages = self._rsi_averages.get(rsi_key)
        if averages is None:
            if len(closes_with_current) < period + 1:
                return None
            window = closes_with_current[-(period + 1):]
            changes = [current - previous for previous, current in zip(window, window[1:])]
            average_gain = sum(max(change, Decimal(0)) for change in changes) / Decimal(period)
            average_loss = sum(max(-change, Decimal(0)) for change in changes) / Decimal(period)
        else:
            change = closes_with_current[-1] - closes_with_current[-2]
            gain = max(change, Decimal(0))
            loss = max(-change, Decimal(0))
            average_gain = (averages[0] * Decimal(period - 1) + gain) / Decimal(period)
            average_loss = (averages[1] * Decimal(period - 1) + loss) / Decimal(period)

        self._rsi_averages[rsi_key] = (average_gain, average_loss)
        if average_gain == 0 and average_loss == 0:
            return Decimal(50)
        if average_loss == 0:
            return Decimal(100)
        relative_strength = average_gain / average_loss
        return Decimal(100) - Decimal(100) / (Decimal(1) + relative_strength)

    @staticmethod
    def _average_last(values, period: int) -> Decimal | None:
        if len(values) < period:
            return None
        window = list(values)[-period:]
        return sum(Decimal(value) for value in window) / Decimal(period)
