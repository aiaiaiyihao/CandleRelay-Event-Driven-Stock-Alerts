from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_db
from app.schemas.rule import (
    RuleCreate,
    RuleResponse,
    RuleStatusUpdate,
    RuleUpdate,
    RuleVersionResponse,
)
from app.services.ruleService import (
    create_rule,
    get_rule,
    list_rule_versions,
    list_rules,
    set_rule_enabled,
    update_rule,
)


router = APIRouter(prefix="/rules", tags=["rules"])


@router.post("", response_model=RuleResponse, status_code=status.HTTP_201_CREATED)
def post_rule(request: RuleCreate, db: Session = Depends(get_db)):
    return create_rule(request, db)


@router.get("", response_model=list[RuleResponse])
def get_rules(db: Session = Depends(get_db)):
    return list_rules(db)


@router.get("/{rule_id}", response_model=RuleResponse)
def get_rule_by_id(rule_id: str, db: Session = Depends(get_db)):
    rule = get_rule(rule_id, db)
    if rule is None:
        raise HTTPException(status_code=404, detail="Rule not found")
    return rule


@router.put("/{rule_id}", response_model=RuleResponse)
def put_rule(rule_id: str, request: RuleUpdate, db: Session = Depends(get_db)):
    rule = update_rule(rule_id, request, db)
    if rule is None:
        raise HTTPException(status_code=404, detail="Rule not found")
    return rule


@router.get("/{rule_id}/versions", response_model=list[RuleVersionResponse])
def get_rule_versions(rule_id: str, db: Session = Depends(get_db)):
    versions = list_rule_versions(rule_id, db)
    if versions is None:
        raise HTTPException(status_code=404, detail="Rule not found")
    return versions


@router.patch("/{rule_id}/status", response_model=RuleResponse)
def patch_rule_status(
    rule_id: str,
    request: RuleStatusUpdate,
    db: Session = Depends(get_db),
):
    rule = set_rule_enabled(rule_id, request.enabled, db)
    if rule is None:
        raise HTTPException(status_code=404, detail="Rule not found")
    return rule
