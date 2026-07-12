from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class EngineConfig:
    name: str
    command: str


@dataclass(slots=True)
class AppConfig:
    runs_root: Path
    scripts_root: Path
    orca: EngineConfig
    gaussian: EngineConfig
    xtb: EngineConfig
    crest: EngineConfig
    dry_run: bool
    config_file: Path | None


def _read_json_config(config_file: Path | None) -> dict[str, str]:
    if config_file is None:
        return {}
    payload = json.loads(config_file.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("配置文件顶层必须是 JSON 对象")
    return {str(key): str(value) for key, value in payload.items()}


def load_config(
    base_dir: Path | None = None,
    runs_root: Path | None = None,
    orca_cmd: str | None = None,
    gaussian_cmd: str | None = None,
    xtb_cmd: str | None = None,
    crest_cmd: str | None = None,
    dry_run: bool = False,
    config_file: Path | None = None,
) -> AppConfig:
    root = (base_dir or Path.cwd()).resolve()
    file_config = _read_json_config(config_file.resolve() if config_file else None)
    configured_runs_root = runs_root or (Path(file_config["runs_root"]) if "runs_root" in file_config else None)
    return AppConfig(
        runs_root=(configured_runs_root.resolve() if configured_runs_root else root / "runs"),
        scripts_root=root / "scripts",
        orca=EngineConfig("orca", orca_cmd or file_config.get("orca_cmd") or os.environ.get("ORCA_CMD", "orca")),
        gaussian=EngineConfig("gaussian", gaussian_cmd or file_config.get("gaussian_cmd") or os.environ.get("GAUSSIAN_CMD", "g16")),
        xtb=EngineConfig("xtb", xtb_cmd or file_config.get("xtb_cmd") or os.environ.get("XTB_CMD", "xtb")),
        crest=EngineConfig("crest", crest_cmd or file_config.get("crest_cmd") or os.environ.get("CREST_CMD", "crest")),
        dry_run=dry_run,
        config_file=config_file.resolve() if config_file else None,
    )