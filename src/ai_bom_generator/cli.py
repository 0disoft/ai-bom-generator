from __future__ import annotations

import argparse
from pathlib import Path
import sys

from ai_bom_generator import __version__
from ai_bom_generator.app import GenerateBomOptions, generate_bom
from ai_bom_generator.errors import AIBomError, ExitCode, InvalidInputError
from ai_bom_generator.reporting import build_error_report, write_json_file
from ai_bom_generator.security import Redactor


_TERMINAL_REDACTOR = Redactor("strict")


class AIBomArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise InvalidInputError(message, "input")


def build_parser() -> argparse.ArgumentParser:
    parser = AIBomArgumentParser(prog="ai-bom")
    parser.add_argument(
        "--version",
        action="version",
        version=f"ai-bom-generator {__version__}",
    )
    subparsers = parser.add_subparsers(dest="command", required=True, parser_class=AIBomArgumentParser)
    generate = subparsers.add_parser("generate", help="Generate an AI/ML BOM from a model directory.")
    generate.add_argument("model_directory", type=Path)
    generate.add_argument("--config", type=Path, default=None)
    generate.add_argument("--format", dest="output_format", default=None)
    generate.add_argument("--output", type=Path, required=True)
    generate.add_argument("--warning-report", type=Path, required=True)
    generate.add_argument("--summary", default="-")
    generate.add_argument("--manifest", type=Path, default=None)
    generate.add_argument("--error-report", type=Path, default=None)
    generate.add_argument("--warnings", choices=["allow", "fail"], default=None)
    generate.add_argument("--redaction", choices=["strict", "off"], default="strict")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    effective_argv = list(sys.argv[1:] if argv is None else argv)
    error_report_path: Path | None = None
    try:
        error_report_path = _extract_error_report_path(effective_argv)
        args = parser.parse_args(effective_argv)
        if args.command != "generate":
            parser.error("unsupported command")

        summary_stdout = args.summary == "-"
        summary_path = None if summary_stdout else Path(args.summary)
        manifest_path = args.manifest
        if manifest_path is None:
            manifest_path = _default_manifest_path(args.output, summary_path)
        error_report_candidate = args.error_report
        error_report_path = None
        error_report_path = _validate_error_report_destination(
            error_report_candidate,
            args.model_directory,
            (args.output, args.warning_report, summary_path, manifest_path),
        )
        _remove_stale_error_report(error_report_path)
        options = GenerateBomOptions(
            model_directory=args.model_directory,
            config=args.config,
            output_format=args.output_format,
            output=args.output,
            warning_report=args.warning_report,
            summary=summary_path,
            manifest=manifest_path,
            summary_stdout=summary_stdout,
            warnings=args.warnings,
            redaction=args.redaction,
        )
        return generate_bom(options)
    except SystemExit as exc:
        if exc.code in (0, None):
            return ExitCode.SUCCESS
        raise
    except AIBomError as exc:
        print(f"ai-bom: {exc.stage}: {_TERMINAL_REDACTOR.redact_text(exc.message)}", file=sys.stderr)
        _write_failure_report(error_report_path, exc)
        return exc.exit_code
    except Exception as exc:
        print(f"ai-bom: internal-error: {_TERMINAL_REDACTOR.redact_text(str(exc))}", file=sys.stderr)
        _write_failure_report(error_report_path, exc)
        return ExitCode.INTERNAL_ERROR


def _default_manifest_path(output: Path, summary: Path | None) -> Path:
    base = summary if summary is not None else output
    return base.with_name(f"{base.name}.manifest.json")


def _extract_error_report_path(argv: list[str]) -> Path | None:
    value: str | None = None
    for index, argument in enumerate(argv):
        if argument.startswith("--error-report="):
            value = argument.split("=", 1)[1]
        elif argument == "--error-report" and index + 1 < len(argv):
            candidate = argv[index + 1]
            if candidate and not candidate.startswith("-"):
                value = candidate
    if not value:
        return None
    return _resolve_output_path(Path(value), "Error report")


def _validate_error_report_destination(
    candidate: Path | None,
    model_directory: Path,
    other_outputs: tuple[Path | None, ...],
) -> Path | None:
    if candidate is None:
        return None
    resolved = _resolve_output_path(candidate, "Error report")
    model_root = model_directory.resolve(strict=False)
    if _paths_overlap(resolved, model_root):
        raise InvalidInputError(
            f"Error report output path must be outside target model directory: {candidate}",
            "input",
        )
    for output in other_outputs:
        if output is None:
            continue
        output_path = _resolve_output_path(output, "Generated")
        if _paths_overlap(resolved, output_path):
            raise InvalidInputError(
                f"Error report output path must not overlap another output path: {candidate}",
                "input",
            )
    return resolved


def _resolve_output_path(candidate: Path, label: str) -> Path:
    path = candidate if candidate.is_absolute() else Path.cwd() / candidate
    if path.is_symlink():
        raise InvalidInputError(f"{label} output path must not be a symlink: {candidate}", "input")
    if path.exists() and path.is_dir():
        raise InvalidInputError(f"{label} output path must be a file path, not a directory: {candidate}", "input")
    if path.parent.exists() and not path.parent.is_dir():
        raise InvalidInputError(f"{label} output parent path must be a directory: {path.parent}", "input")
    return path.resolve(strict=False)


def _paths_overlap(left: Path, right: Path) -> bool:
    try:
        left.relative_to(right)
        return True
    except ValueError:
        pass
    try:
        right.relative_to(left)
        return True
    except ValueError:
        return False


def _remove_stale_error_report(path: Path | None) -> None:
    if path is None:
        return
    try:
        path.unlink(missing_ok=True)
    except OSError as exc:
        raise InvalidInputError(f"Could not remove stale error report: {path}: {exc}", "output") from exc


def _write_failure_report(path: Path | None, error: AIBomError | Exception) -> None:
    if path is None:
        return
    try:
        write_json_file(path, build_error_report(error, _TERMINAL_REDACTOR))
    except Exception as exc:
        message = _TERMINAL_REDACTOR.redact_text(str(exc))
        print(f"ai-bom: error-report: could not write {path}: {message}", file=sys.stderr)
