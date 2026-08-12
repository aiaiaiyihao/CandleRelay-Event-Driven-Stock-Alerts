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
        technical_conditions, default_period = self._technical_conditions(text)
        conditions = [*technical_conditions, *self._price_value_conditions(text)]
        volume_condition = self._volume_condition(text, default_period or 20)
        if volume_condition:
            conditions.append(volume_condition)
        if not conditions:
            raise UnsupportedRuleText("could not identify a supported rule condition")

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

    def _technical_conditions(self, text: str) -> tuple[list[dict[str, Any]], int | None]:
        ema_match = re.search(r"EMA\s*[_-]?(\d+)", text, re.IGNORECASE)
        sma_match = re.search(r"SMA\s*[_-]?(\d+)", text, re.IGNORECASE)
        if ema_match and sma_match:
            ema_period = int(ema_match.group(1))
            sma_period = int(sma_match.group(1))
            return ([{
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
                }], max(ema_period, sma_period))

        rsi_match = re.search(r"RSI\s*[_-]?(\d+)", text, re.IGNORECASE)
        if rsi_match:
            period = int(rsi_match.group(1))
            operator, value = self._threshold_comparison(text, rsi_match.end())
            return ([{
                    "left": {
                        "type": "indicator",
                        "indicator": "rsi",
                        "period": period,
                    },
                    "operator": operator,
                    "right": {"type": "value", "value": value},
                }], period)

        sma_match = re.search(r"SMA\s*[_-]?(\d+)", text, re.IGNORECASE)
        if sma_match:
            sma_period = int(sma_match.group(1))
            return ([{
                "left": {"type": "metric", "metric": "price"},
                "operator": self._price_operator(text),
                "right": {
                    "type": "indicator",
                    "indicator": "sma",
                    "period": sma_period,
                },
            }], sma_period)
        return [], None

    @staticmethod
    def _price_value_conditions(text: str) -> list[dict[str, Any]]:
        range_match = re.search(
            r"(?:price|trades?|trading)\s+(?:is\s+)?(?:between|from)\s*\$?(\d+(?:\.\d+)?)\s+(?:and|to)\s*\$?(\d+(?:\.\d+)?)",
            text,
            re.IGNORECASE,
        )
        if range_match:
            lower, upper = sorted((float(range_match.group(1)), float(range_match.group(2))))
            return [
                {"left": {"type": "metric", "metric": "price"}, "operator": ">=", "right": {"type": "value", "value": lower}},
                {"left": {"type": "metric", "metric": "price"}, "operator": "<=", "right": {"type": "value", "value": upper}},
            ]

        comparison = re.search(
            r"(?:price|trades?|trading)\s+(?:is\s+)?(above|over|greater\s+than|below|under|less\s+than|>=?|<=?)\s*\$?(\d+(?:\.\d+)?)",
            text,
            re.IGNORECASE,
        )
        if not comparison:
            return []
        phrase = comparison.group(1).lower()
        operator = ">" if phrase in {"above", "over", "greater than", ">"} else "<"
        if phrase == ">=": operator = ">="
        if phrase == "<=": operator = "<="
        return [{
            "left": {"type": "metric", "metric": "price"},
            "operator": operator,
            "right": {"type": "value", "value": float(comparison.group(2))},
        }]

    def _volume_condition(self, text: str, default_period: int) -> dict[str, Any] | None:
        volume_ratio = self._volume_ratio(text)
        if volume_ratio is None:
            return None
        volume_phrase = text[text.lower().find("volume"):]
        operator = "<" if re.search(r"less\s+than|below|under", volume_phrase, re.IGNORECASE) else ">"
        return {
            "left": {
                "type": "indicator",
                "indicator": "volume_ratio",
                "period": self._volume_period(text) or default_period,
            },
            "operator": operator,
            "right": {"type": "value", "value": volume_ratio},
        }

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
        if re.search(r"cross(?:es)?\s+above", text, re.IGNORECASE):
            return "crosses_above"
        if re.search(r"cross(?:es)?\s+below", text, re.IGNORECASE):
            return "crosses_below"
        if re.search(r"above|greater\s+than", text, re.IGNORECASE):
            return ">"
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
        minute = re.search(
            r"\b(1|5|15)\s*(?:m\b|[- ]?min(?:ute)?s?\b)",
            text,
            re.IGNORECASE,
        )
        if minute:
            return f"{minute.group(1)}m", None
        if re.search(r"\b(?:1\s*h|(?:1\s*)?hour(?:ly|s)?)\b", text, re.IGNORECASE):
            return "1h", None
        if re.search(r"\b(?:1\s*d|daily|(?:1\s*)?day(?:\s+bars?)?)\b", text, re.IGNORECASE):
            return "1d", None
        return "1d", "No timeframe was specified; defaulted to daily bars (1d)."
