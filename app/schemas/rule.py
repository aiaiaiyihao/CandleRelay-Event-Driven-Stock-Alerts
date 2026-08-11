from pydantic import BaseModel, ConfigDict, Field

from app.domain.rules import RuleDefinition


class RuleCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=120)
    definition: RuleDefinition


class RuleUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=120)
    definition: RuleDefinition


class RuleStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool


class RuleResponse(BaseModel):
    id: str
    name: str
    enabled: bool
    version: int
    definition: RuleDefinition


class RuleVersionResponse(BaseModel):
    version: int
    definition: RuleDefinition


class RuleCompileRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1, max_length=2_000)
    cooldown_seconds: int = Field(default=3600, ge=0, le=31_536_000)
