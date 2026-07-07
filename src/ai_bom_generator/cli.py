from __future__ import annotations

import argparse
from pathlib import Path
import sys

from ai_bom_generator.app import GenerateBomOptions, generate_bom
from ai_bom_generator.errors import AIBomError, ExitCode, InvalidInputError
from ai_bom_generator.security import Redactor


_TERMINAL_REDACTOR = Redactor("strict")


class AIBomArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise InvalidInputError(message, "input")


def build_parser() -> argparse.ArgumentParser:
    parser = AIBomArgumentParser(prog="ai-bom")
    subparsers = parser.add_subparsers(dest="command", required=True, parser_class=AIBomArgumentParser)
    generate = subparsers.add_parser("generate", help="Generate an AI/ML BOM from a model directory.")
    generate.add_argument("model_directory", type=Path)
    generate.add_argument("--config", type=Path, default=None)
    generate.add_argument("--format", dest="output_format", default=None)
    generate.add_argument("--output", type=Path, required=True)
    generate.add_argument("--warning-report", type=Path, required=True)
    generate.add_argument("--summary", default="-")
    generate.add_argument("--warnings", choices=["allow", "fail"], default="allow")
    generate.add_argument("--redaction", choices=["strict", "off"], default="strict")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
        if args.command != "generate":
            parser.error("unsupported command")

        summary_stdout = args.summary == "-"
        summary_path = None if summary_stdout else Path(args.summary)
        options = GenerateBomOptions(
            model_directory=args.model_directory,
            config=args.config,
            output_format=args.output_format,
            output=args.output,
            warning_report=args.warning_report,
            summary=summary_path,
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
        return exc.exit_code
    except Exception as exc:
        print(f"ai-bom: internal-error: {_TERMINAL_REDACTOR.redact_text(str(exc))}", file=sys.stderr)
        return ExitCode.INTERNAL_ERROR
