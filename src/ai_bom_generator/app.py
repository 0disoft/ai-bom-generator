from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import time

from ai_bom_generator.collectors import collect_evidence
from ai_bom_generator.config import LoadedConfig, load_config
from ai_bom_generator.domain.evidence import NormalizedEvidence
from ai_bom_generator.errors import ExitCode, ExporterError, InvalidInputError
from ai_bom_generator.exporters.cyclonedx_json import SUPPORTED_FORMAT as CYCLONEDX_JSON_FORMAT
from ai_bom_generator.exporters.cyclonedx_json import export_cyclonedx_json
from ai_bom_generator.exporters.spdx_ai import SUPPORTED_FORMAT as SPDX_AI_FORMAT
from ai_bom_generator.exporters.spdx_ai import export_spdx_ai
from ai_bom_generator.reporting import build_summary, build_warning_report, write_json_output_set
from ai_bom_generator.reporting.json_writer import write_json_stream
from ai_bom_generator.security import PathPolicy, Redactor


@dataclass(frozen=True)
class GenerateBomOptions:
    model_directory: Path
    config: Path | None
    output_format: str | None
    output: Path
    warning_report: Path
    summary: Path | None
    manifest: Path
    summary_stdout: bool
    warnings: str | None
    redaction: str


def generate_bom(options: GenerateBomOptions) -> int:
    start = time.perf_counter()
    policy = PathPolicy(options.model_directory)
    output_destinations = _validate_output_destinations(options, policy)
    _remove_existing_output_files(output_destinations)
    redactor = Redactor(options.redaction)
    config = load_config(options.config, policy)
    output_format = _resolve_output_format(options, config)
    if output_format not in _SUPPORTED_EXPORT_FORMATS:
        raise ExporterError(f"Unsupported output format: {output_format}", "exporter")
    warning_policy = _resolve_warning_policy(options, config)
    evidence = collect_evidence(config, policy, redactor)

    bom = _export_bom(output_format, evidence, redactor)
    warning_report = build_warning_report(evidence, redactor)
    warning_policy_failed = warning_policy == "fail" and evidence.warning_count > 0
    elapsed_ms = int((time.perf_counter() - start) * 1000)
    summary = build_summary(
        evidence=evidence,
        bom_path=options.output,
        warning_report_path=options.warning_report,
        output_format=output_format,
        elapsed_ms=elapsed_ms,
        warning_policy_failed=warning_policy_failed,
        redactor=redactor,
    )

    output_items = [
        ("bom", options.output, bom),
        ("warning_report", options.warning_report, warning_report),
    ]
    if options.summary:
        output_items.append(("summary", options.summary, summary))
    write_json_output_set(output_items, options.manifest)

    if options.summary_stdout:
        import sys

        write_json_stream(sys.stdout, summary)

    return ExitCode.WARNING_POLICY_FAILED if warning_policy_failed else ExitCode.SUCCESS


def _resolve_output_format(options: GenerateBomOptions, config: LoadedConfig) -> str:
    if options.output_format is not None:
        return options.output_format

    output = config.get_table("output")
    configured = output.get("format", CYCLONEDX_JSON_FORMAT)
    if not isinstance(configured, str):
        raise InvalidInputError("[output].format must be a string.", "config")
    return configured


_SUPPORTED_EXPORT_FORMATS = {CYCLONEDX_JSON_FORMAT, SPDX_AI_FORMAT}


def _export_bom(output_format: str, evidence: NormalizedEvidence, redactor: Redactor) -> dict[str, object]:
    if output_format == CYCLONEDX_JSON_FORMAT:
        return export_cyclonedx_json(evidence, redactor)
    if output_format == SPDX_AI_FORMAT:
        return export_spdx_ai(evidence, redactor)
    raise ExporterError(f"Unsupported output format: {output_format}", "exporter")


def _resolve_warning_policy(options: GenerateBomOptions, config: LoadedConfig) -> str:
    if options.warnings is not None:
        return options.warnings

    warning_policy = config.get_table("warning_policy")
    configured = warning_policy.get("missing_metadata", "warn")
    if not isinstance(configured, str):
        raise InvalidInputError("[warning_policy].missing_metadata must be a string.", "config")
    if configured == "warn":
        return "allow"
    if configured == "fail":
        return "fail"
    raise InvalidInputError("[warning_policy].missing_metadata must be warn or fail.", "config")


def _validate_output_destinations(options: GenerateBomOptions, policy: PathPolicy) -> dict[str, Path]:
    destinations = {
        "bom": policy.validate_output_file(options.output, "BOM"),
        "warning_report": policy.validate_output_file(options.warning_report, "Warning report"),
        "manifest": policy.validate_output_file(options.manifest, "Generation manifest"),
    }
    if options.summary is not None:
        destinations["summary"] = policy.validate_output_file(options.summary, "Summary")

    seen: dict[Path, str] = {}
    for label, path in destinations.items():
        previous = seen.get(path)
        if previous:
            raise InvalidInputError(
                f"Output paths must be distinct; {label} and {previous} both resolve to {path}",
                "input",
            )
        for existing_path, existing_label in seen.items():
            if _paths_overlap(path, existing_path):
                raise InvalidInputError(
                    "Output paths must not overlap; "
                    f"{label} resolves to {path} and {existing_label} resolves to {existing_path}",
                    "input",
                )
        seen[path] = label
    return destinations


def _remove_existing_output_files(destinations: dict[str, Path]) -> None:
    for label, path in destinations.items():
        try:
            if path.exists():
                path.unlink()
        except OSError as exc:
            message = f"Could not remove stale {label} output before generation: {path}: {exc}"
            raise InvalidInputError(message, "input") from exc


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
