from __future__ import annotations

from pathlib import Path
import re
from typing import Any

from ai_bom_generator.config import LoadedConfig
from ai_bom_generator.domain.artifact import ModelArtifact
from ai_bom_generator.domain.evidence import NormalizedEvidence
from ai_bom_generator.domain.reference import DeclaredReference
from ai_bom_generator.domain.source_location import SourceLocation
from ai_bom_generator.domain.warning import Warning
from ai_bom_generator.errors import CollectorError, InvalidInputError
from ai_bom_generator.hashing import sha256_file
from ai_bom_generator.security import PathPolicy, Redactor


_GIT_SHA_RE = re.compile(r"^[0-9a-fA-F]{40}$")
_KNOWN_MODEL_CARD = "MODEL_CARD.md"


def collect_evidence(config: LoadedConfig, policy: PathPolicy, redactor: Redactor) -> NormalizedEvidence:
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
    artifacts = _collect_artifacts(config, policy, warnings)
    dependencies = _collect_path_references("dependencies", config, policy, warnings, redactor)
    datasets = _collect_named_references("datasets", config, warnings, redactor)
    prompts = _collect_path_references("prompts", config, policy, warnings, redactor, optional_paths=True)
    evals = _collect_path_references("evals", config, policy, warnings, redactor, optional_paths=True)
    training = _collect_path_references("training", config, policy, warnings, redactor, optional_paths=True)
    git = _collect_git(policy, warnings)

    return NormalizedEvidence(
        target_root=policy.root.as_posix(),
        model_metadata=tuple(sorted(model_metadata)),
        artifacts=tuple(sorted(artifacts)),
        dependencies=tuple(sorted(dependencies)),
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


def _collect_artifacts(config: LoadedConfig, policy: PathPolicy, warnings: list[Warning]) -> list[ModelArtifact]:
    artifacts_config = config.get_table("artifacts")
    includes = artifacts_config.get("include", [])
    if not includes:
        warnings.append(
            Warning(
                code="MISSING_ARTIFACT_SELECTION",
                severity="warning",
                object_kind="artifact",
                object_id="artifacts",
                message="No model artifact include patterns were declared.",
                source=_source(config, "artifacts.include"),
                remediation="Add [artifacts].include patterns for model files to hash.",
            )
        )
        return []
    if not isinstance(includes, list) or any(not isinstance(item, str) for item in includes):
        raise InvalidInputError("[artifacts].include must be an array of strings.", "config")

    excludes = artifacts_config.get("exclude", [])
    if excludes and (not isinstance(excludes, list) or any(not isinstance(item, str) for item in excludes)):
        raise InvalidInputError("[artifacts].exclude must be an array of strings.", "config")

    include_patterns = [policy.validate_relative_glob(pattern, "[artifacts].include") for pattern in includes]
    exclude_patterns = [policy.validate_relative_glob(pattern, "[artifacts].exclude") for pattern in excludes]

    selected: list[ModelArtifact] = []
    for pattern in sorted(include_patterns):
        matches = sorted(policy.root.glob(pattern))
        if not matches:
            warnings.append(
                Warning(
                    code="MISSING_ARTIFACT",
                    severity="warning",
                    object_kind="artifact",
                    object_id=pattern,
                    message=f"No artifact matched include pattern: {pattern}",
                    source=_source(config, "artifacts.include"),
                    remediation="Check the artifact path or remove the include pattern.",
                )
            )
            continue
        for match in matches:
            if _is_excluded(match, policy.root, exclude_patterns):
                continue
            try:
                if match.is_symlink():
                    warnings.append(
                        Warning(
                            code="SKIPPED_SYMLINK",
                            severity="warning",
                            object_kind="artifact",
                            object_id=match.as_posix(),
                            message="Symlink artifact was skipped by default.",
                            source=_source(config, "artifacts.include"),
                            remediation="Use a real file inside the target root.",
                        )
                    )
                    continue
                resolved = match.resolve(strict=True)
                policy.ensure_inside_root(resolved)
                if not resolved.is_file():
                    continue
                selected.append(
                    ModelArtifact(
                        path=policy.relative_to_root(resolved),
                        size=resolved.stat().st_size,
                        digest=sha256_file(resolved),
                        digest_algorithm="sha256",
                        selected_by=pattern,
                        source=_source(config, "artifacts.include"),
                    )
                )
            except OSError as exc:
                raise CollectorError(f"Failed to collect artifact {match}: {exc}", "artifact") from exc
    return selected


def _collect_path_references(
    section: str,
    config: LoadedConfig,
    policy: PathPolicy,
    warnings: list[Warning],
    redactor: Redactor,
    optional_paths: bool = False,
) -> list[DeclaredReference]:
    items = config.get_array(section)
    references: list[DeclaredReference] = []
    for index, item in enumerate(items):
        source = _source(config, f"{section}[{index}]")
        raw_path = item.get("path") or item.get("artifact")
        object_id = _scalar_object_id(
            item.get("name") or item.get("type") or raw_path,
            f"{section}-{index}",
        )
        values = _string_pairs(
            item,
            redactor,
            warnings,
            config,
            f"{section}[{index}]",
            _singular_kind(section),
            object_id,
        )
        if raw_path:
            if not isinstance(raw_path, str):
                raise InvalidInputError(f"{section}[{index}] path must be a string.", "config")
            try:
                resolved = policy.resolve_existing_file(raw_path, required=not optional_paths)
                merged = dict(values)
                merged["path"] = policy.relative_to_root(resolved)
                values = tuple(sorted(merged.items()))
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
                else:
                    raise
        references.append(DeclaredReference(kind=_singular_kind(section), object_id=object_id, values=values, source=source))
    return references


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
        if section == "datasets" and "license_declared" not in item:
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
            for line in _read_git_text_file(packed_refs).splitlines():
                if not line or line.startswith("#") or line.startswith("^"):
                    continue
                commit, _, packed_ref = line.partition(" ")
                if packed_ref == ref_name and _GIT_SHA_RE.fullmatch(commit):
                    return commit.lower()
        except OSError:
            return None
    return None


def _read_git_text_file(path: Path) -> str:
    if path.is_symlink():
        raise OSError("symlink Git metadata is not allowed")
    return path.read_text(encoding="utf-8")


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
            pairs.append((str(key), redactor.redact_text(str(value))))
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


def _is_excluded(path: Path, root: Path, excludes: list[str]) -> bool:
    relative = path.relative_to(root).as_posix()
    return any(path.match(pattern) or relative == pattern or Path(relative).match(pattern) for pattern in excludes)


def _singular_kind(section: str) -> str:
    return {
        "dependencies": "dependency",
        "datasets": "dataset",
        "prompts": "prompt",
        "evals": "eval",
        "training": "training",
    }.get(section, section)
