from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.auth_router import require_current_user
from app.core.config import get_db
from app.models.User import User
from app.schemas.rule import (
    RuleCompileRequest,
    RuleCreate,
    RuleResponse,
    RuleStatusUpdate,
    RuleUpdate,
    RuleVersionResponse,
)
from app.compilers.base import CompilationResult, ValidatedRuleCompiler
from app.compilers.heuristic import HeuristicCompilerProvider, UnsupportedRuleText
from app.services.ruleService import (
    create_rule,
    delete_rule,
    get_rule,
    list_rule_versions,
    list_rules,
    set_rule_enabled,
    update_rule,
)


router = APIRouter(prefix="/rules", tags=["rules"])


@router.post("/compile", response_model=CompilationResult)
def compile_rule(request: RuleCompileRequest):
    compiler = ValidatedRuleCompiler(
        HeuristicCompilerProvider(cooldown_seconds=request.cooldown_seconds)
    )
    try:
        return compiler.compile(request.text)
    except (ValueError, UnsupportedRuleText) as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.post("", response_model=RuleResponse, status_code=status.HTTP_201_CREATED)
def post_rule(
    request: RuleCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_current_user),
):
    return create_rule(request, db, user_id=user.id)


@router.get("", response_model=list[RuleResponse])
def get_rules(db: Session = Depends(get_db), user: User = Depends(require_current_user)):
    return list_rules(db, user_id=user.id)


@router.get("/{rule_id}", response_model=RuleResponse)
def get_rule_by_id(rule_id: str, db: Session = Depends(get_db), user: User = Depends(require_current_user)):
    rule = get_rule(rule_id, db, user_id=user.id)
    if rule is None:
        raise HTTPException(status_code=404, detail="Rule not found")
    return rule


@router.put("/{rule_id}", response_model=RuleResponse)
def put_rule(rule_id: str, request: RuleUpdate, db: Session = Depends(get_db), user: User = Depends(require_current_user)):
    rule = update_rule(rule_id, request, db, user_id=user.id)
    if rule is None:
        raise HTTPException(status_code=404, detail="Rule not found")
    return rule


@router.get("/{rule_id}/versions", response_model=list[RuleVersionResponse])
def get_rule_versions(rule_id: str, db: Session = Depends(get_db), user: User = Depends(require_current_user)):
    versions = list_rule_versions(rule_id, db, user_id=user.id)
    if versions is None:
        raise HTTPException(status_code=404, detail="Rule not found")
    return versions


@router.patch("/{rule_id}/status", response_model=RuleResponse)
def patch_rule_status(
    rule_id: str,
    request: RuleStatusUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_current_user),
):
    rule = set_rule_enabled(rule_id, request.enabled, db, user_id=user.id)
    if rule is None:
        raise HTTPException(status_code=404, detail="Rule not found")
    return rule


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rule_by_id(
    rule_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_current_user),
):
    if not delete_rule(rule_id, db, user_id=user.id):
        raise HTTPException(status_code=404, detail="Rule not found")
