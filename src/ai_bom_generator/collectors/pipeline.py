from __future__ import annotations

import os
from pathlib import Path
import re
from typing import Any, Iterator

from ai_bom_generator.collectors.artifacts import collect_artifacts
from ai_bom_generator.collectors.dependency_files import (
    DependencyFileLimitError,
    DependencyParseError,
    detect_dependency_format,
    parse_dependency_file,
)
from ai_bom_generator.collectors.generation_marker import (
    collect_initial_generation_marker,
    verify_final_generation_marker,
)
from ai_bom_generator.config import LoadedConfig
from ai_bom_generator.domain.dependency import DependencyPackage
from ai_bom_generator.domain.evidence import NormalizedEvidence
from ai_bom_generator.domain.reference import DeclaredReference
from ai_bom_generator.domain.source_location import SourceLocation
from ai_bom_generator.domain.warning import Warning
from ai_bom_generator.errors import CollectorError, InvalidInputError
from ai_bom_generator.security import PathPolicy, Redactor, open_binary_nofollow


_GIT_SHA_RE = re.compile(r"^[0-9a-fA-F]{40}$")
_MAX_GIT_METADATA_BYTES = 1024 * 1024
_KNOWN_MODEL_CARD = "MODEL_CARD.md"


def collect_evidence(config: LoadedConfig, policy: PathPolicy, redactor: Redactor) -> NormalizedEvidence:
    initial_generation_marker = collect_initial_generation_marker(config, policy)
    warnings: list[Warning] = []
    if redactor.mode == "off":
        warnings.append(
            Warning(
                code="REDACTION_DISABLED",
                severity="warning",
                object_kind="run",
                object_id="redaction",
                message="Secret-shaped values will not be redacted because redaction mode is off.",
                remediation="Use --redaction strict unless unredacted output is required for local debugging.",
            )
        )
    model_metadata = _collect_model(config, policy, warnings, redactor)
    artifacts = collect_artifacts(config, policy, warnings)
    dependencies, dependency_packages = _collect_dependencies(config, policy, warnings, redactor)
    datasets = _collect_named_references("datasets", config, warnings, redactor)
    prompts = _collect_path_references("prompts", config, policy, warnings, redactor, optional_paths=True)
    evals = _collect_path_references("evals", config, policy, warnings, redactor, optional_paths=True)
    training = _collect_path_references("training", config, policy, warnings, redactor, optional_paths=True)
    _ensure_unique_reference_ids([*dependencies, *datasets, *prompts, *evals, *training])
    git = _collect_git(policy, warnings)
    generation_marker = verify_final_generation_marker(config, policy, initial_generation_marker)

    unique_dependency_packages = {package.identity_key(): package for package in dependency_packages}
    return NormalizedEvidence(
        target_root=policy.root.as_posix(),
        generation_marker=generation_marker,
        model_metadata=tuple(sorted(model_metadata)),
        artifacts=tuple(sorted(artifacts)),
        dependencies=tuple(sorted(dependencies)),
        dependency_packages=tuple(
            sorted(
                unique_dependency_packages.values(),
                key=lambda item: (item.source.path, item.name, item.version or "", item.requirement),
            )
        ),
        datasets=tuple(sorted(datasets)),
        prompts=tuple(sorted(prompts)),
        evals=tuple(sorted(evals)),
        training=tuple(sorted(training)),
        git=tuple(sorted(git)),
        warnings=tuple(sorted(warnings)),
    )


def _collect_model(
    config: LoadedConfig,
    policy: PathPolicy,
    warnings: list[Warning],
    redactor: Redactor,
) -> list[DeclaredReference]:
    model = config.get_table("model")
    discovered_model_card = _discover_model_card(policy, warnings)
    if not model:
        if discovered_model_card:
            return [
                DeclaredReference(
                    kind="model",
                    object_id="model",
                    values=(("model_card", discovered_model_card),),
                    source=SourceLocation(path=discovered_model_card, collector="model"),
                )
            ]
        if not any(warning.code == "MISSING_MODEL_METADATA" and warning.object_kind == "model" for warning in warnings):
            warnings.append(
                Warning(
                    code="MISSING_MODEL_METADATA",
                    severity="warning",
                    object_kind="model",
                    object_id="model",
                    message="No [model] metadata was declared.",
                    remediation="Add [model] metadata to the AI-BOM config.",
                )
            )
        return []

    object_id = _scalar_object_id(model.get("name"), "model")
    values = dict(
        _string_pairs(
            model,
            redactor,
            warnings,
            config,
            "model",
            "model",
            object_id,
            skip_keys={"model_card"},
        )
    )
    model_card = model.get("model_card")
    if model_card is not None:
        if not isinstance(model_card, str):
            raise InvalidInputError("[model].model_card must be a string path.", "config")
        resolved = policy.resolve_existing_file(model_card, required=True)
        values["model_card"] = policy.relative_to_root(resolved)
    elif discovered_model_card:
        values["model_card"] = discovered_model_card

    if not values:
        warnings.append(
            Warning(
                code="EMPTY_MODEL_METADATA",
                severity="warning",
                object_kind="model",
                object_id="model",
                message="[model] exists but contains no scalar metadata fields.",
                source=_source(config, "model"),
                remediation="Declare at least a model name, version, or license_declared value.",
            )
        )
    return [
        DeclaredReference(
            kind="model",
            object_id=object_id,
            values=tuple(sorted(values.items())),
            source=_source(config, "model"),
        )
    ]


def _discover_model_card(policy: PathPolicy, warnings: list[Warning]) -> str | None:
    candidate = policy.root / _KNOWN_MODEL_CARD
    source = SourceLocation(path=_KNOWN_MODEL_CARD, collector="model")
    if candidate.is_symlink():
        warnings.append(
            Warning(
                code="SKIPPED_SYMLINK",
                severity="warning",
                object_kind="model",
                object_id=_KNOWN_MODEL_CARD,
                message="Symlink model metadata file was skipped by default.",
                source=source,
                remediation="Use a real model metadata file inside the target root.",
            )
        )
        return None
    if not candidate.exists():
        return None
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        warnings.append(
            Warning(
                code="MISSING_MODEL_METADATA",
                severity="warning",
                object_kind="model",
                object_id=_KNOWN_MODEL_CARD,
                message=f"Known model metadata file could not be read: {_KNOWN_MODEL_CARD}: {exc}",
                source=source,
                remediation="Check the model metadata file or declare [model] metadata in config.",
            )
        )
        return None
    policy.ensure_inside_root(resolved)
    if not resolved.is_file():
        return None
    return policy.relative_to_root(resolved)


def _collect_path_references(
    section: str,
    config: LoadedConfig,
    policy: PathPolicy,
    warnings: list[Warning],
    redactor: Redactor,
    optional_paths: bool = False,
    metadata_skip_keys: set[str] | None = None,
) -> list[DeclaredReference]:
    items = config.get_array(section)
    references: list[DeclaredReference] = []
    for index, item in enumerate(items):
        source = _source(config, f"{section}[{index}]")
        raw_path_field = None
        if item.get("path"):
            raw_path_field = "path"
        elif item.get("artifact"):
            raw_path_field = "artifact"
        raw_path = item.get(raw_path_field) if raw_path_field else None
        object_id_source = item.get("name") or item.get("type")
        object_id = _scalar_object_id(object_id_source, f"{section}-{index}")
        values = _string_pairs(
            item,
            redactor,
            warnings,
            config,
            f"{section}[{index}]",
            _singular_kind(section),
            object_id,
            skip_keys={"path", "artifact", *(metadata_skip_keys or set())},
        )
        if raw_path:
            if not isinstance(raw_path, str):
                raise InvalidInputError(f"{section}[{index}] path must be a string.", "config")
            try:
                resolved = policy.resolve_existing_file(raw_path, required=not optional_paths)
                normalized_path = policy.relative_to_root(resolved)
                merged = dict(values)
                merged["path"] = normalized_path
                if raw_path_field == "artifact":
                    merged["artifact"] = normalized_path
                values = tuple(sorted(merged.items()))
                if object_id_source is None:
                    object_id = normalized_path
            except InvalidInputError:
                if optional_paths:
                    warnings.append(
                        Warning(
                            code=f"MISSING_{section.upper()}_REFERENCE_FILE",
                            severity="warning",
                            object_kind=section,
                            object_id=str(item.get("name", raw_path)),
                            message=f"Declared {section} file could not be read: {raw_path}",
                            source=source,
                            remediation="Check the path or remove the stale reference.",
                        )
                    )
                    continue
                else:
                    raise
        references.append(DeclaredReference(kind=_singular_kind(section), object_id=object_id, values=values, source=source))
    return references


def _collect_dependencies(
    config: LoadedConfig,
    policy: PathPolicy,
    warnings: list[Warning],
    redactor: Redactor,
) -> tuple[list[DeclaredReference], list[DependencyPackage]]:
    items = config.get_array("dependencies")
    references = _collect_path_references(
        "dependencies",
        config,
        policy,
        warnings,
        redactor,
        metadata_skip_keys={"parse"},
    )
    packages: list[DependencyPackage] = []
    for index, (item, reference) in enumerate(zip(items, references, strict=True)):
        parse_enabled = item.get("parse", True)
        if not isinstance(parse_enabled, bool):
            raise InvalidInputError(f"dependencies[{index}].parse must be a boolean.", "config")
        values = dict(reference.values)
        relative_path = values.get("path")
        if not parse_enabled or relative_path is None:
            continue

        dependency_format = detect_dependency_format(relative_path, item.get("type"))
        warning_source = _source(config, f"dependencies[{index}].path")
        if dependency_format is None:
            warnings.append(
                Warning(
                    code="UNSUPPORTED_DEPENDENCY_FORMAT",
                    severity="warning",
                    object_kind="dependency",
                    object_id=relative_path,
                    message=f"Dependency file format is not supported for parsing: {relative_path}",
                    source=warning_source,
                    remediation=(
                        "Use type = \"uv\" for uv.lock, type = \"pip\" or \"requirements\" "
                        "for requirements files, type = \"conda-lock\" for unified conda-lock "
                        "YAML files, or set parse = false."
                    ),
                )
            )
            continue

        path = policy.root / relative_path
        try:
            result = parse_dependency_file(path, relative_path, dependency_format, redactor)
        except DependencyFileLimitError as exc:
            warnings.append(
                Warning(
                    code="DEPENDENCY_FILE_LIMIT_EXCEEDED",
                    severity="warning",
                    object_kind="dependency",
                    object_id=relative_path,
                    message=f"Dependency file was not parsed because a fixed safety limit was exceeded: {exc}",
                    source=warning_source,
                    remediation="Use a smaller lockfile or set parse = false while keeping the file reference.",
                )
            )
            continue
        except DependencyParseError as exc:
            warnings.append(
                Warning(
                    code="DEPENDENCY_PARSE_FAILED",
                    severity="warning",
                    object_kind="dependency",
                    object_id=relative_path,
                    message=f"Dependency file could not be parsed: {relative_path}: {redactor.redact_text(str(exc))}",
                    source=warning_source,
                    remediation="Fix the dependency file, choose the correct type, or set parse = false.",
                )
            )
            continue

        packages.extend(result.packages)
        if result.skipped_entries and result.first_issue:
            warnings.append(
                Warning(
                    code="DEPENDENCY_PARSE_PARTIAL",
                    severity="warning",
                    object_kind="dependency",
                    object_id=relative_path,
                    message=(
                        f"Skipped {result.skipped_entries} unsupported or malformed dependency entries or "
                        "evidence fields in "
                        f"{relative_path}; first issue at {result.first_issue.location}: "
                        f"{result.first_issue.reason}."
                    ),
                    source=warning_source,
                    remediation=(
                        "Replace unsupported directives with explicit PEP 508 entries or set parse = false "
                        "if only file-level evidence is required."
                    ),
                )
            )
    return references, packages


def _collect_named_references(
    section: str,
    config: LoadedConfig,
    warnings: list[Warning],
    redactor: Redactor,
) -> list[DeclaredReference]:
    items = config.get_array(section)
    references: list[DeclaredReference] = []
    for index, item in enumerate(items):
        object_id = _scalar_object_id(item.get("name"), f"{section}-{index}")
        values = _string_pairs(
            item,
            redactor,
            warnings,
            config,
            f"{section}[{index}]",
            _singular_kind(section),
            object_id,
        )
        if section == "datasets" and not str(item.get("license_declared", "")).strip():
            warnings.append(
                Warning(
                    code="MISSING_DATASET_LICENSE",
                    severity="warning",
                    object_kind="dataset",
                    object_id=object_id,
                    message="Dataset license was not declared.",
                    source=_source(config, f"{section}[{index}].license_declared"),
                    remediation="Add license_declared or NOASSERTION to the dataset reference.",
                )
            )
        references.append(DeclaredReference(kind=_singular_kind(section), object_id=object_id, values=values, source=_source(config, f"{section}[{index}]")))
    return references


def _collect_git(policy: PathPolicy, warnings: list[Warning]) -> list[DeclaredReference]:
    git_path = policy.root / ".git"
    if git_path.is_symlink():
        warnings.append(
            Warning(
                code="SKIPPED_GIT_SYMLINK",
                severity="warning",
                object_kind="git",
                object_id=".git",
                message="Git metadata symlink was skipped.",
                source=SourceLocation(path=".git", collector="git"),
                remediation="Use a target project with an in-root .git directory.",
            )
        )
        return []
    if not git_path.exists():
        return []
    if git_path.is_file():
        warnings.append(
            Warning(
                code="UNSUPPORTED_GIT_METADATA_FILE",
                severity="warning",
                object_kind="git",
                object_id=".git",
                message="Git metadata file was skipped because MVP only reads in-root .git directories.",
                source=SourceLocation(path=".git", collector="git"),
                remediation="Run against a checkout with an in-root .git directory or omit Git evidence.",
            )
        )
        return []
    if not git_path.is_dir():
        return []

    git_head = git_path / "HEAD"
    try:
        text = _read_git_text_file(git_head).strip()
    except OSError as exc:
        warnings.append(
            Warning(
                code="GIT_HEAD_UNREADABLE",
                severity="warning",
                object_kind="git",
                object_id="HEAD",
                message=f"Git HEAD could not be read: {exc}",
                source=SourceLocation(path=".git/HEAD", collector="git"),
                remediation="Check the local Git metadata or omit Git evidence.",
            )
        )
        return []

    values = {"head": text}
    if _GIT_SHA_RE.fullmatch(text):
        values["commit"] = text.lower()
    elif text.startswith("ref: "):
        ref_name = text.removeprefix("ref: ").strip()
        values["ref"] = ref_name
        commit = _resolve_git_ref(git_path, ref_name)
        if commit:
            values["commit"] = commit
        else:
            warnings.append(
                Warning(
                    code="GIT_REF_UNRESOLVED",
                    severity="warning",
                    object_kind="git",
                    object_id=ref_name,
                    message=f"Git ref could not be resolved to a commit: {ref_name}",
                    source=SourceLocation(path=".git/HEAD", collector="git"),
                    remediation="Ensure the referenced Git ref exists as a loose or packed ref.",
                )
            )
    else:
        warnings.append(
            Warning(
                code="GIT_HEAD_UNSUPPORTED",
                severity="warning",
                object_kind="git",
                object_id="HEAD",
                message="Git HEAD did not contain a detached commit or symbolic ref.",
                source=SourceLocation(path=".git/HEAD", collector="git"),
                remediation="Use a standard Git HEAD format.",
            )
        )

    return [
        DeclaredReference(
            kind="git",
            object_id="HEAD",
            values=tuple(sorted(values.items())),
            source=SourceLocation(path=".git/HEAD", collector="git"),
        )
    ]


def _resolve_git_ref(git_dir: Path, ref_name: str) -> str | None:
    if ref_name.startswith("/") or "\\" in ref_name:
        return None

    loose_ref = git_dir / ref_name
    try:
        loose_ref.resolve(strict=False).relative_to(git_dir.resolve(strict=True))
    except (OSError, ValueError):
        return None
    if loose_ref.exists() and not loose_ref.is_symlink() and loose_ref.is_file():
        try:
            text = _read_git_text_file(loose_ref).strip()
        except OSError:
            return None
        if _GIT_SHA_RE.fullmatch(text):
            return text.lower()

    packed_refs = git_dir / "packed-refs"
    if packed_refs.exists() and not packed_refs.is_symlink() and packed_refs.is_file():
        try:
            for line in _iter_git_text_lines(packed_refs):
                if not line or line.startswith("#") or line.startswith("^"):
                    continue
                commit, _, packed_ref = line.partition(" ")
                if packed_ref == ref_name and _GIT_SHA_RE.fullmatch(commit):
                    return commit.lower()
        except OSError:
            return None
    return None


def _read_git_text_file(path: Path) -> str:
    with open_binary_nofollow(path) as handle:
        if os.fstat(handle.fileno()).st_size > _MAX_GIT_METADATA_BYTES:
            raise OSError("Git metadata file exceeds the 1 MiB read limit")
        return handle.read(_MAX_GIT_METADATA_BYTES + 1).decode("utf-8")


def _iter_git_text_lines(path: Path) -> Iterator[str]:
    text = _read_git_text_file(path)
    for line in text.splitlines():
        yield line


def _string_pairs(
    data: dict[str, Any],
    redactor: Redactor,
    warnings: list[Warning],
    config: LoadedConfig,
    source_prefix: str,
    object_kind: str,
    object_id: str,
    skip_keys: set[str] | None = None,
) -> tuple[tuple[str, str], ...]:
    skip = skip_keys or set()
    pairs: list[tuple[str, str]] = []
    for key, value in data.items():
        if key in skip:
            continue
        if _is_scalar(value):
            pairs.append((str(key), str(redactor.redact_key_value(str(key), str(value)))))
        else:
            warnings.append(
                Warning(
                    code="UNSUPPORTED_CONFIG_FIELD",
                    severity="warning",
                    object_kind=object_kind,
                    object_id=object_id,
                    message=f"Unsupported non-scalar config field was ignored: {source_prefix}.{key}",
                    source=_source(config, f"{source_prefix}.{key}"),
                    remediation="Use a scalar string, number, or boolean value until structured fields are supported.",
                )
            )
    return tuple(sorted(pairs))


def _is_scalar(value: object) -> bool:
    return isinstance(value, (str, int, float, bool))


def _scalar_object_id(value: object, fallback: str) -> str:
    if _is_scalar(value):
        return str(value)
    return fallback


def _source(config: LoadedConfig, field: str) -> SourceLocation:
    path = config.path.as_posix() if config.path else "<inline-defaults>"
    return SourceLocation(path=path, field=field)


def _singular_kind(section: str) -> str:
    return {
        "dependencies": "dependency",
        "datasets": "dataset",
        "prompts": "prompt",
        "evals": "eval",
        "training": "training",
    }.get(section, section)


def _ensure_unique_reference_ids(references: list[DeclaredReference]) -> None:
    seen: dict[tuple[str, str], DeclaredReference] = {}
    for reference in references:
        key = (reference.kind, reference.object_id)
        previous = seen.get(key)
        if previous is not None:
            raise InvalidInputError(
                "Duplicate reference identity would create duplicate CycloneDX bom-ref "
                f"{reference.kind}:{reference.object_id}. "
                f"First declared at {previous.source.field}; duplicate declared at {reference.source.field}.",
                "config",
            )
        seen[key] = reference
