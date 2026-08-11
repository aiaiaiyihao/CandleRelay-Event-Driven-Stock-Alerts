from app.domain.rules import IndicatorOperand, RuleDefinition


def required_indicator_periods(rule: RuleDefinition) -> set[int]:
    conditions = rule.conditions.all or rule.conditions.any or []
    return {
        operand.period
        for condition in conditions
        for operand in (condition.left, condition.right)
        if isinstance(operand, IndicatorOperand)
    }

