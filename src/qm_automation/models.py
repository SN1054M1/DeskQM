from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class Molecule:
    name: str
    natoms: int
    comment: str
    atoms_block: str
    source: Path


@dataclass(slots=True)
class RetryProfile:
    labels: list[str]
    extra_keywords: list[str] = field(default_factory=list)
    maxcore_step_mb: int = 0


@dataclass(slots=True)
class TaskContext:
    run_dir: Path
    input_dir: Path
    scratch_dir: Path
    logs_dir: Path
    results_dir: Path
    attempts_dir: Path
    command_dir: Path


@dataclass(slots=True)
class RunResult:
    success: bool
    engine: str
    work_dir: Path
    final_xyz: Path | None
    energy_hartree: float | None
    primary_input: Path | None
    command_file: Path | None
    shell_command_file: Path | None
    powershell_command_file: Path | None
    command_line: str
    stdout_file: Path
    stderr_file: Path
    metadata_file: Path
    attempt_count: int
    message: str
    dry_run: bool = False


@dataclass(frozen=True, slots=True)
class TemplateProfile:
    task_name: str
    engine: str
    preset_name: str
    description: str
    method: str
    basis: str
    driver: str
    extra_keywords: tuple[str, ...] = ()
    extra_flags: tuple[str, ...] = ()