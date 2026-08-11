from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.domain.rules import RuleDefinition


class CompilerProvider(Protocol):
    def generate_candidate(self, text: str) -> dict[str, Any]: ...


class CompilationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    definition: RuleDefinition
    explanation: str
    warnings: list[str] = Field(default_factory=list)


class CompilerOutputError(ValueError):
    """Raised when a provider emits data outside the safe Rule DSL."""


class ValidatedRuleCompiler:
    def __init__(self, provider: CompilerProvider):
        self.provider = provider

    def compile(self, text: str) -> CompilationResult:
        if not text.strip():
            raise ValueError("rule text must not be empty")
        candidate = self.provider.generate_candidate(text)
        try:
            result = CompilationResult.model_validate(candidate)
        except ValidationError as exc:
            raise CompilerOutputError(
                "compiler provider returned an invalid rule candidate"
            ) from exc
        return result

