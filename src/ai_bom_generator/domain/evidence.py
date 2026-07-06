from __future__ import annotations

from dataclasses import dataclass

from ai_bom_generator.domain.artifact import ModelArtifact
from ai_bom_generator.domain.reference import DeclaredReference
from ai_bom_generator.domain.warning import Warning


@dataclass(frozen=True)
class NormalizedEvidence:
    target_root: str
    model_metadata: tuple[DeclaredReference, ...]
    artifacts: tuple[ModelArtifact, ...]
    dependencies: tuple[DeclaredReference, ...]
    datasets: tuple[DeclaredReference, ...]
    prompts: tuple[DeclaredReference, ...]
    evals: tuple[DeclaredReference, ...]
    training: tuple[DeclaredReference, ...]
    git: tuple[DeclaredReference, ...]
    warnings: tuple[Warning, ...]

    @property
    def warning_count(self) -> int:
        return len(self.warnings)

    @property
    def completeness_status(self) -> str:
        if not self.model_metadata and not self.artifacts:
            return "empty"
        if self.warnings:
            return "partial"
        return "complete"
