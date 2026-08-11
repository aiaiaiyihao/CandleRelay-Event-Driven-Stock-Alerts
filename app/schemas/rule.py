from pydantic import BaseModel, ConfigDict, Field

from app.domain.rules import RuleDefinition


class RuleCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=120)
    definition: RuleDefinition


class RuleResponse(BaseModel):
    id: str
    name: str
    enabled: bool
    version: int
    definition: RuleDefinition

