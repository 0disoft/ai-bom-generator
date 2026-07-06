from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import time

from ai_bom_generator.collectors import collect_evidence
from ai_bom_generator.config import load_config
from ai_bom_generator.errors import ExitCode, ExporterError
from ai_bom_generator.exporters.cyclonedx_json import SUPPORTED_FORMAT, export_cyclonedx_json
from ai_bom_generator.reporting import build_summary, build_warning_report, write_json_file
from ai_bom_generator.reporting.json_writer import write_json_stream
from ai_bom_generator.security import PathPolicy, Redactor


@dataclass(frozen=True)
class GenerateBomOptions:
    model_directory: Path
    config: Path | None
    output_format: str
    output: Path
    warning_report: Path
    summary: Path | None
    summary_stdout: bool
    warnings: str
    redaction: str


def generate_bom(options: GenerateBomOptions) -> int:
    start = time.perf_counter()
    if options.output_format != SUPPORTED_FORMAT:
        raise ExporterError(f"Unsupported output format: {options.output_format}", "exporter")
    if options.warnings not in {"allow", "fail"}:
        raise ExporterError(f"Unsupported warning policy: {options.warnings}", "input")

    policy = PathPolicy(options.model_directory)
    redactor = Redactor(options.redaction)
    config = load_config(options.config, policy)
    evidence = collect_evidence(config, policy, redactor)

    bom = export_cyclonedx_json(evidence, redactor)
    warning_report = build_warning_report(evidence, redactor)
    warning_policy_failed = options.warnings == "fail" and evidence.warning_count > 0
    elapsed_ms = int((time.perf_counter() - start) * 1000)
    summary = build_summary(
        evidence=evidence,
        bom_path=options.output,
        warning_report_path=options.warning_report,
        output_format=options.output_format,
        elapsed_ms=elapsed_ms,
        warning_policy_failed=warning_policy_failed,
        redactor=redactor,
    )

    write_json_file(options.output, bom)
    write_json_file(options.warning_report, warning_report)
    if options.summary_stdout:
        import sys

        write_json_stream(sys.stdout, summary)
    elif options.summary:
        write_json_file(options.summary, summary)

    return ExitCode.WARNING_POLICY_FAILED if warning_policy_failed else ExitCode.SUCCESS
