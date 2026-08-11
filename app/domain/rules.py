from enum import Enum
from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, PositiveInt, model_validator


class Timeframe(str, Enum):
    MINUTE_1 = "1m"
    MINUTE_5 = "5m"
    MINUTE_15 = "15m"
    HOUR_1 = "1h"
    DAY_1 = "1d"


class Operator(str, Enum):
    LT = "<"
    LTE = "<="
    EQ = "=="
    GTE = ">="
    GT = ">"
    CROSSES_ABOVE = "crosses_above"
    CROSSES_BELOW = "crosses_below"


class TriggerMode(str, Enum):
    WHILE_TRUE = "while_true"
    ON_FALSE_TO_TRUE = "on_false_to_true"


class PriceMetric(str, Enum):
    OPEN = "open"
    HIGH = "high"
    LOW = "low"
    PRICE = "price"
    VOLUME = "volume"


class IndicatorName(str, Enum):
    SMA = "sma"
    EMA = "ema"
    RSI = "rsi"
    VOLUME_RATIO = "volume_ratio"


class MetricOperand(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["metric"] = "metric"
    metric: PriceMetric


class IndicatorOperand(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["indicator"] = "indicator"
    indicator: IndicatorName
    period: PositiveInt


class ValueOperand(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["value"] = "value"
    value: float


Operand = Annotated[
    Union[MetricOperand, IndicatorOperand, ValueOperand],
    Field(discriminator="type"),
]


class Condition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    left: Operand
    operator: Operator
    right: Operand

    @model_validator(mode="after")
    def validate_operands(self):
        if isinstance(self.left, ValueOperand):
            raise ValueError("left operand must be a metric or indicator")
        if self.operator in {Operator.CROSSES_ABOVE, Operator.CROSSES_BELOW}:
            if isinstance(self.right, ValueOperand):
                raise ValueError("cross operators require a metric or indicator on the right")
        return self


class ConditionGroup(BaseModel):
    model_config = ConfigDict(extra="forbid")

    all: list[Condition] | None = None
    any: list[Condition] | None = None

    @model_validator(mode="after")
    def require_exactly_one_group(self):
        populated = [group for group in (self.all, self.any) if group]
        if len(populated) != 1:
            raise ValueError("conditions must contain exactly one non-empty 'all' or 'any' group")
        return self


class RuleDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=True)

    dsl_version: Literal["1.0"] = "1.0"
    symbol: str = Field(min_length=1, max_length=32, pattern=r"^[A-Za-z0-9.\-]+$")
    timeframe: Timeframe
    conditions: ConditionGroup
    trigger: TriggerMode = TriggerMode.ON_FALSE_TO_TRUE
    cooldown_seconds: int = Field(default=0, ge=0, le=31_536_000)

    @model_validator(mode="after")
    def normalize_symbol(self):
        self.symbol = self.symbol.upper()
        return self

