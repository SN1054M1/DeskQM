from __future__ import annotations

from datetime import datetime
from pathlib import Path

from qm_automation.models import TaskContext


def create_task_context(runs_root: Path, task_name: str, input_name: str) -> TaskContext:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = runs_root / f"{task_name}_{stamp}_{input_name}"
    input_dir = run_dir / "inputs"
    scratch_dir = run_dir / "scratch"
    logs_dir = run_dir / "logs"
    results_dir = run_dir / "results"
    attempts_dir = run_dir / "attempts"
    command_dir = run_dir / "commands"

    for path in [run_dir, input_dir, scratch_dir, logs_dir, results_dir, attempts_dir, command_dir]:
        path.mkdir(parents=True, exist_ok=False)

    return TaskContext(
        run_dir=run_dir,
        input_dir=input_dir,
        scratch_dir=scratch_dir,
        logs_dir=logs_dir,
        results_dir=results_dir,
        attempts_dir=attempts_dir,
        command_dir=command_dir,
    )