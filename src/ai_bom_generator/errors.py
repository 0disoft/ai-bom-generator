from __future__ import annotations

from dataclasses import dataclass


class ExitCode:
    SUCCESS = 0
    WARNING_POLICY_FAILED = 10
    INVALID_INPUT = 20
    COLLECTOR_FAILURE = 30
    EXPORTER_FAILURE = 40
    INTERNAL_ERROR = 70


@dataclass(frozen=True)
class AIBomError(Exception):
    message: str
    exit_code: int
    stage: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "args", (self.message,))

    def __str__(self) -> str:
        return self.message


class InvalidInputError(AIBomError):
    def __init__(self, message: str, stage: str = "input") -> None:
        super().__init__(message=message, exit_code=ExitCode.INVALID_INPUT, stage=stage)


class CollectorError(AIBomError):
    def __init__(self, message: str, stage: str = "collector") -> None:
        super().__init__(message=message, exit_code=ExitCode.COLLECTOR_FAILURE, stage=stage)


class ExporterError(AIBomError):
    def __init__(self, message: str, stage: str = "exporter") -> None:
        super().__init__(message=message, exit_code=ExitCode.EXPORTER_FAILURE, stage=stage)
