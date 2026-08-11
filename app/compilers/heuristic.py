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
        timeframe, warning = self._timeframe(text)
        technical_condition, default_period = self._technical_condition(text)
        conditions = [technical_condition]

        volume_ratio = self._volume_ratio(text)
        if volume_ratio is not None:
            volume_period = self._volume_period(text) or default_period
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

    def _technical_condition(self, text: str) -> tuple[dict[str, Any], int]:
        ema_match = re.search(r"EMA\s*[_-]?(\d+)", text, re.IGNORECASE)
        sma_match = re.search(r"SMA\s*[_-]?(\d+)", text, re.IGNORECASE)
        if ema_match and sma_match:
            ema_period = int(ema_match.group(1))
            sma_period = int(sma_match.group(1))
            return (
                {
                    "left": {
                        "type": "indicator",
                        "indicator": "ema",
                        "period": ema_period,
                    },
                    "operator": self._cross_operator(text),
                    "right": {
                        "type": "indicator",
                        "indicator": "sma",
                        "period": sma_period,
                    },
                },
                max(ema_period, sma_period),
            )

        rsi_match = re.search(r"RSI\s*[_-]?(\d+)", text, re.IGNORECASE)
        if rsi_match:
            period = int(rsi_match.group(1))
            operator, value = self._threshold_comparison(text, rsi_match.end())
            return (
                {
                    "left": {
                        "type": "indicator",
                        "indicator": "rsi",
                        "period": period,
                    },
                    "operator": operator,
                    "right": {"type": "value", "value": value},
                },
                period,
            )

        sma_period = self._sma_period(text)
        return (
            {
                "left": {"type": "metric", "metric": "price"},
                "operator": self._price_operator(text),
                "right": {
                    "type": "indicator",
                    "indicator": "sma",
                    "period": sma_period,
                },
            },
            sma_period,
        )

    @staticmethod
    def _symbol(text: str) -> str:
        ignored = {"SMA", "EMA", "RSI", "AND", "OR", "WHEN", "ALERT"}
        matches = re.findall(r"\b[A-Z]{1,5}(?:\.[A-Z])?\b", text)
        for match in matches:
            if match not in ignored:
                return match
        raise UnsupportedRuleText("could not identify a stock symbol")

    @staticmethod
    def _sma_period(text: str) -> int:
        match = re.search(r"SMA\s*[_-]?(\d+)", text, re.IGNORECASE)
        if not match:
            raise UnsupportedRuleText("could not identify an SMA period")
        return int(match.group(1))

    @staticmethod
    def _price_operator(text: str) -> str:
        if re.search(r"cross(?:es)?\s+below", text, re.IGNORECASE):
            return "crosses_below"
        if re.search(r"below|less\s+than", text, re.IGNORECASE):
            return "<"
        raise UnsupportedRuleText("could not identify the price comparison")

    @staticmethod
    def _cross_operator(text: str) -> str:
        if re.search(r"cross(?:es)?\s+above", text, re.IGNORECASE):
            return "crosses_above"
        if re.search(r"cross(?:es)?\s+below", text, re.IGNORECASE):
            return "crosses_below"
        raise UnsupportedRuleText("could not identify the indicator cross direction")

    @staticmethod
    def _threshold_comparison(text: str, start: int) -> tuple[str, float]:
        remainder = text[start:]
        match = re.search(
            r"(below|less\s+than|<)\s*(\d+(?:\.\d+)?)",
            remainder,
            re.IGNORECASE,
        )
        if match:
            return "<", float(match.group(2))
        match = re.search(
            r"(above|greater\s+than|>)\s*(\d+(?:\.\d+)?)",
            remainder,
            re.IGNORECASE,
        )
        if match:
            return ">", float(match.group(2))
        raise UnsupportedRuleText("could not identify the indicator threshold")

    @staticmethod
    def _volume_ratio(text: str) -> float | None:
        if not re.search(r"volume", text, re.IGNORECASE):
            return None
        match = re.search(r"(\d+(?:\.\d+)?)\s*(?:x|times)", text, re.IGNORECASE)
        if match:
            return float(match.group(1))
        raise UnsupportedRuleText("could not identify the volume multiplier")

    @staticmethod
    def _volume_period(text: str) -> int | None:
        patterns = [
            r"past\s+(\d+)\s+(?:trading\s+)?days?",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return int(match.group(1))
        return None

    @staticmethod
    def _timeframe(text: str) -> tuple[str, str | None]:
        minute = re.search(r"(1|5|15)\s*min(?:ute)?s?", text, re.IGNORECASE)
        if minute:
            return f"{minute.group(1)}m", None
        if re.search(r"(?:1\s*)?hour", text, re.IGNORECASE):
            return "1h", None
        if re.search(r"daily|day\s+bars?", text, re.IGNORECASE):
            return "1d", None
        return "1d", "No timeframe was specified; defaulted to daily bars (1d)."
