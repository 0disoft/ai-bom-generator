from __future__ import annotations

import argparse
from pathlib import Path
import sys

from ai_bom_generator.app import GenerateBomOptions, generate_bom
from ai_bom_generator.errors import AIBomError, ExitCode


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ai-bom")
    subparsers = parser.add_subparsers(dest="command", required=True)
    generate = subparsers.add_parser("generate", help="Generate an AI/ML BOM from a model directory.")
    generate.add_argument("model_directory", type=Path)
    generate.add_argument("--config", type=Path, default=None)
    generate.add_argument("--format", dest="output_format", default="cyclonedx-json-1.7")
    generate.add_argument("--output", type=Path, required=True)
    generate.add_argument("--warning-report", type=Path, required=True)
    generate.add_argument("--summary", default="-")
    generate.add_argument("--warnings", choices=["allow", "fail"], default="allow")
    generate.add_argument("--redaction", choices=["strict", "off"], default="strict")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
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
    try:
        return generate_bom(options)
    except AIBomError as exc:
        print(f"ai-bom: {exc.stage}: {exc.message}", file=sys.stderr)
        return exc.exit_code
    except Exception as exc:
        print(f"ai-bom: internal-error: {exc}", file=sys.stderr)
        return ExitCode.INTERNAL_ERROR
