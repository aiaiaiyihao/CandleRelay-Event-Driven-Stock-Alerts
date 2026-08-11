from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_db
from app.schemas.rule import RuleCreate, RuleResponse
from app.services.ruleService import create_rule, get_rule, list_rules


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

