from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.Rule import Rule, RuleVersion
from app.schemas.rule import RuleCreate, RuleResponse


def create_rule(request: RuleCreate, session: Session) -> RuleResponse:
    definition = request.definition
    rule = Rule(
        name=request.name,
        symbol=definition.symbol,
        timeframe=definition.timeframe,
        current_version=1,
    )
    rule.versions.append(
        RuleVersion(version=1, dsl=definition.model_dump(mode="json"))
    )
    session.add(rule)
    session.commit()
    session.refresh(rule)
    return _to_response(rule, rule.versions[0])


def list_rules(session: Session) -> list[RuleResponse]:
    rules = session.execute(
        select(Rule).options(selectinload(Rule.versions)).order_by(Rule.created_at)
    ).scalars()
    return [_to_response(rule, _current_version(rule)) for rule in rules]


def get_rule(rule_id: str, session: Session) -> RuleResponse | None:
    rule = session.execute(
        select(Rule)
        .where(Rule.id == rule_id)
        .options(selectinload(Rule.versions))
    ).scalar_one_or_none()
    if rule is None:
        return None
    return _to_response(rule, _current_version(rule))


def _current_version(rule: Rule) -> RuleVersion:
    return next(
        version for version in rule.versions if version.version == rule.current_version
    )


def _to_response(rule: Rule, version: RuleVersion) -> RuleResponse:
    return RuleResponse(
        id=rule.id,
        name=rule.name,
        enabled=rule.enabled,
        version=version.version,
        definition=version.dsl,
    )

