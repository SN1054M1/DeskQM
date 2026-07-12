from __future__ import annotations

import csv
from datetime import datetime
import json
from pathlib import Path
from typing import Any

from qm_automation.models import RunResult


def _infer_task_name(work_dir: str | None) -> str:
    if not work_dir:
        return "unknown"
    stem = Path(work_dir).name
    parts = stem.split("_")
    if len(parts) >= 3 and parts[-2].isdigit():
        return "_".join(parts[:-3]) or stem
    if len(parts) >= 4 and parts[-3].isdigit() and parts[-2].isdigit():
        return "_".join(parts[:-4]) or stem
    if len(parts) >= 2:
        return parts[0]
    return stem


def _normalize_record(record: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(record)
    normalized.setdefault("success", False)
    normalized.setdefault("dry_run", False)
    normalized.setdefault("engine", "unknown")
    normalized.setdefault("energy_hartree", None)
    normalized.setdefault("work_dir", "")
    normalized.setdefault("final_xyz", None)
    normalized.setdefault("primary_input", None)
    normalized.setdefault("command_file", None)
    normalized.setdefault("shell_command_file", None)
    normalized.setdefault("powershell_command_file", None)
    normalized.setdefault("message", "")
    normalized.setdefault("metadata_path", None)
    normalized["task_name"] = _infer_task_name(str(normalized.get("work_dir", "")))
    return normalized


def _infer_run_timestamp(work_dir: str | None) -> datetime | None:
    if not work_dir:
        return None
    parts = Path(work_dir).name.split("_")
    for index in range(len(parts) - 1):
        stamp = f"{parts[index]}_{parts[index + 1]}"
        try:
            return datetime.strptime(stamp, "%Y%m%d_%H%M%S")
        except ValueError:
            continue
    return None


def write_results_csv(output_file: Path, results: list[RunResult]) -> None:
    with output_file.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "engine",
                "success",
                "dry_run",
                "energy_hartree",
                "work_dir",
                "final_xyz",
                "primary_input",
                "stdout",
                "stderr",
                "message",
            ],
        )
        writer.writeheader()
        for result in results:
            writer.writerow(
                {
                    "engine": result.engine,
                    "success": result.success,
                    "dry_run": result.dry_run,
                    "energy_hartree": result.energy_hartree,
                    "work_dir": str(result.work_dir),
                    "final_xyz": str(result.final_xyz) if result.final_xyz else "",
                    "primary_input": str(result.primary_input) if result.primary_input else "",
                    "stdout": str(result.stdout_file),
                    "stderr": str(result.stderr_file),
                    "message": result.message,
                }
            )


def write_results_json(output_file: Path, results: list[RunResult]) -> None:
    payload = []
    for result in results:
        payload.append(
            {
                "engine": result.engine,
                "success": result.success,
                "dry_run": result.dry_run,
                "energy_hartree": result.energy_hartree,
                "task_name": _infer_task_name(str(result.work_dir)),
                "work_dir": str(result.work_dir),
                "final_xyz": str(result.final_xyz) if result.final_xyz else None,
                "primary_input": str(result.primary_input) if result.primary_input else None,
                "command_file": str(result.command_file) if result.command_file else None,
                "shell_command_file": str(result.shell_command_file) if result.shell_command_file else None,
                "powershell_command_file": str(result.powershell_command_file) if result.powershell_command_file else None,
                "stdout": str(result.stdout_file),
                "stderr": str(result.stderr_file),
                "metadata": str(result.metadata_file),
                "message": result.message,
            }
        )
    output_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def collect_run_metadata(runs_root: Path) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    if not runs_root.exists():
        return records
    for metadata_file in runs_root.glob("*/results/run_metadata.json"):
        payload = _normalize_record(json.loads(metadata_file.read_text(encoding="utf-8-sig")))
        payload["metadata_path"] = str(metadata_file)
        records.append(payload)
    records.sort(
        key=lambda item: (
            _infer_run_timestamp(str(item.get("work_dir", ""))) or datetime.min,
            str(item.get("work_dir", "")),
        )
    )
    return records


def load_summary_json(summary_file: Path) -> list[dict[str, Any]]:
    payload = json.loads(summary_file.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, list):
        raise ValueError("后处理输入 JSON 必须是记录数组")
    return [_normalize_record(item) for item in payload if isinstance(item, dict)]


def sort_records_by_energy(
    records: list[dict[str, Any]],
    *,
    success_only: bool = True,
    exclude_dry_run: bool = True,
) -> list[dict[str, Any]]:
    filtered = [_normalize_record(item) for item in records]
    if success_only:
        filtered = [item for item in filtered if bool(item.get("success"))]
    if exclude_dry_run:
        filtered = [item for item in filtered if not bool(item.get("dry_run"))]
    filtered = [item for item in filtered if item.get("energy_hartree") is not None]
    return sorted(filtered, key=lambda item: float(item["energy_hartree"]))


def select_lowest_energy(records: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    ordered = sort_records_by_energy(records)
    return ordered[:limit]


def compute_run_statistics(records: list[dict[str, Any]]) -> dict[str, Any]:
    normalized = [_normalize_record(item) for item in records]
    stats: dict[str, Any] = {
        "total_runs": len(normalized),
        "success_runs": sum(1 for item in normalized if bool(item.get("success"))),
        "failed_runs": sum(1 for item in normalized if not bool(item.get("success"))),
        "dry_runs": sum(1 for item in normalized if bool(item.get("dry_run"))),
        "by_engine": {},
        "by_task": {},
    }
    for item in normalized:
        engine = str(item.get("engine", "unknown"))
        task_name = str(item.get("task_name", "unknown"))
        stats["by_engine"].setdefault(engine, 0)
        stats["by_engine"][engine] += 1
        stats["by_task"].setdefault(task_name, 0)
        stats["by_task"][task_name] += 1

    lowest = select_lowest_energy(normalized, 10)
    stats["lowest_energy_samples"] = [
        {
            "task_name": item.get("task_name"),
            "engine": item.get("engine"),
            "energy_hartree": item.get("energy_hartree"),
            "work_dir": item.get("work_dir"),
        }
        for item in lowest
    ]
    return stats


def write_metadata_summary_csv(output_file: Path, records: list[dict[str, object]]) -> None:
    with output_file.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "task_name",
                "engine",
                "success",
                "dry_run",
                "energy_hartree",
                "work_dir",
                "final_xyz",
                "command_file",
                "shell_command_file",
                "powershell_command_file",
                "message",
                "metadata_path",
            ],
        )
        writer.writeheader()
        for record in records:
            normalized = _normalize_record(record)
            writer.writerow({field: normalized.get(field, "") for field in writer.fieldnames})


def write_metadata_summary_json(output_file: Path, records: list[dict[str, object]]) -> None:
    normalized = [_normalize_record(record) for record in records]
    output_file.write_text(json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8")


def write_statistics_json(output_file: Path, stats: dict[str, Any]) -> None:
    output_file.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")


def write_generic_records_csv(output_file: Path, records: list[dict[str, Any]]) -> None:
    normalized = [_normalize_record(record) for record in records]
    with output_file.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "task_name",
                "engine",
                "success",
                "dry_run",
                "energy_hartree",
                "work_dir",
                "final_xyz",
                "primary_input",
                "command_file",
                "shell_command_file",
                "powershell_command_file",
                "message",
            ],
        )
        writer.writeheader()
        for record in normalized:
            writer.writerow({field: record.get(field, "") for field in writer.fieldnames})


def build_scan_profile(energies: list[float]) -> list[dict[str, Any]]:
    if not energies:
        return []
    minimum = min(energies)
    return [
        {
            "step": index,
            "energy_hartree": energy,
            "relative_kcal_mol": (energy - minimum) * 627.509474,
            "is_lowest": energy == minimum,
        }
        for index, energy in enumerate(energies, start=1)
    ]


def write_scan_profile_csv(output_file: Path, profile: list[dict[str, Any]]) -> None:
    with output_file.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["step", "energy_hartree", "relative_kcal_mol", "is_lowest"])
        writer.writeheader()
        for row in profile:
            writer.writerow(row)


def write_scan_profile_json(output_file: Path, profile: list[dict[str, Any]]) -> None:
    output_file.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")