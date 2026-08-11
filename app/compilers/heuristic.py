import re
from typing import Any


class UnsupportedRuleText(ValueError):
    pass


class HeuristicCompilerProvider:
    """Deterministic compiler for the first supported SignalForge rule pattern."""

    def __init__(self, cooldown_seconds: int = 3600):
        self.cooldown_seconds = cooldown_seconds

    def generate_candidate(self, text: str) -> dict[str, Any]:
        symbol = self._symbol(text)
        sma_period = self._sma_period(text)
        timeframe, warning = self._timeframe(text)
        conditions = [
            {
                "left": {"type": "metric", "metric": "price"},
                "operator": self._price_operator(text),
                "right": {
                    "type": "indicator",
                    "indicator": "sma",
                    "period": sma_period,
                },
            }
        ]

        volume_ratio = self._volume_ratio(text)
        if volume_ratio is not None:
            volume_period = self._volume_period(text) or sma_period
            conditions.append(
                {
                    "left": {
                        "type": "indicator",
                        "indicator": "volume_ratio",
                        "period": volume_period,
                    },
                    "operator": ">",
                    "right": {"type": "value", "value": volume_ratio},
                }
            )

        warnings = [warning] if warning else []
        return {
            "definition": {
                "dsl_version": "1.0",
                "symbol": symbol,
                "timeframe": timeframe,
                "conditions": {"all": conditions},
                "trigger": "on_false_to_true",
                "cooldown_seconds": self.cooldown_seconds,
            },
            "explanation": (
                f"Evaluate {symbol} on {timeframe} bars using {len(conditions)} "
                "AND-combined condition(s)."
            ),
            "warnings": warnings,
        }

    @staticmethod
    def _symbol(text: str) -> str:
        ignored = {"SMA", "EMA", "RSI", "AND", "OR", "WHEN", "ALERT"}
        matches = re.findall(r"\b[A-Za-z]{1,5}(?:\.[A-Za-z])?\b", text)
        for match in matches:
            candidate = match.upper()
            if candidate not in ignored:
                return candidate
        raise UnsupportedRuleText("could not identify a stock symbol")

    @staticmethod
    def _sma_period(text: str) -> int:
        match = re.search(r"SMA\s*[_-]?(\d+)", text, re.IGNORECASE)
        if not match:
            match = re.search(r"(\d+)\s*(?:日|天)?(?:简单)?均线", text)
        if not match:
            raise UnsupportedRuleText("could not identify an SMA period")
        return int(match.group(1))

    @staticmethod
    def _price_operator(text: str) -> str:
        if re.search(r"跌破|下穿|cross(?:es)?\s+below", text, re.IGNORECASE):
            return "crosses_below"
        if re.search(r"低于|小于|below|less\s+than", text, re.IGNORECASE):
            return "<"
        raise UnsupportedRuleText("could not identify the price comparison")

    @staticmethod
    def _volume_ratio(text: str) -> float | None:
        if not re.search(r"成交量|volume", text, re.IGNORECASE):
            return None
        match = re.search(r"(\d+(?:\.\d+)?)\s*(?:倍|x|times)", text, re.IGNORECASE)
        if match:
            return float(match.group(1))
        if re.search(r"两倍|二倍", text):
            return 2.0
        raise UnsupportedRuleText("could not identify the volume multiplier")

    @staticmethod
    def _volume_period(text: str) -> int | None:
        patterns = [
            r"过去\s*(\d+)\s*(?:个)?(?:交易)?[天日]",
            r"past\s+(\d+)\s+(?:trading\s+)?days?",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return int(match.group(1))
        return None

    @staticmethod
    def _timeframe(text: str) -> tuple[str, str | None]:
        minute = re.search(r"(1|5|15)\s*(?:分钟|min(?:ute)?s?)", text, re.IGNORECASE)
        if minute:
            return f"{minute.group(1)}m", None
        if re.search(r"(?:1\s*)?(?:小时|hour)", text, re.IGNORECASE):
            return "1h", None
        if re.search(r"日线|daily|day\s+bars?", text, re.IGNORECASE):
            return "1d", None
        return "1d", "No timeframe was specified; defaulted to daily bars (1d)."

