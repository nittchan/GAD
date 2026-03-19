from __future__ import annotations

from pathlib import Path

import yaml

from gad._models_legacy import DataManifest, TriggerDef


def load_trigger_def(path: str | Path) -> TriggerDef:
    path = Path(path)
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"Trigger YAML root must be a mapping, got {type(raw).__name__}")
    return TriggerDef.model_validate(raw)


def load_data_manifest(path: str | Path) -> DataManifest:
    path = Path(path)
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"Manifest YAML root must be a mapping, got {type(raw).__name__}")
    return DataManifest.model_validate(raw)


def discover_triggers(triggers_dir: str | Path) -> list[Path]:
    triggers_dir = Path(triggers_dir)
    if not triggers_dir.is_dir():
        return []
    return sorted(triggers_dir.glob("*.yaml"))
