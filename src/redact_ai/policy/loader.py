"""Policy YAML → :class:`Policy` loader (BUILD_SPEC §6).

The shipped default policy lives at ``examples/default_policy.yaml`` and
is bundled into the package via :mod:`importlib.resources` so it works
both for ``pip install -e .`` and ``pipx`` end-user installs.
"""

from __future__ import annotations

from functools import lru_cache
from importlib.resources import files
from pathlib import Path

import yaml
from pydantic import ValidationError

from redact_ai.errors import policy_error
from redact_ai.policy.schema import Policy


@lru_cache(maxsize=1)
def _default_yaml_text() -> str:
    """Return the shipped default policy YAML.

    We prefer the package-resource copy under :mod:`redact_ai.resources`; if
    that copy is absent (the project tree is the source layout used for
    tests), fall back to ``examples/default_policy.yaml`` relative to the
    repository root.
    """
    try:
        return files("redact_ai.resources").joinpath("default_policy.yaml").read_text(
            encoding="utf-8"
        )
    except (FileNotFoundError, ModuleNotFoundError):
        repo_root = Path(__file__).resolve().parents[3]
        return (repo_root / "examples" / "default_policy.yaml").read_text(encoding="utf-8")


def load_default_policy() -> Policy:
    return _parse(_default_yaml_text(), policy_id_for_error="default")


def load_policy(source: str | Path) -> Policy:
    """Load a policy from a YAML file path or a YAML string."""
    if isinstance(source, Path) or (isinstance(source, str) and "\n" not in source and Path(source).exists()):
        text = Path(source).read_text(encoding="utf-8")
        label = str(source)
    else:
        text = source
        label = "<inline>"
    return _parse(text, policy_id_for_error=label)


def _parse(text: str, *, policy_id_for_error: str) -> Policy:
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise policy_error(policy_id_for_error, f"YAML parse error: {exc}") from exc
    if not isinstance(data, dict):
        raise policy_error(policy_id_for_error, "top-level YAML must be a mapping")
    try:
        return Policy.model_validate(data)
    except ValidationError as exc:
        raise policy_error(data.get("id", policy_id_for_error), str(exc)) from exc


def builtin_policies() -> list[Policy]:
    return [load_default_policy()]
