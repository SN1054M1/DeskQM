from __future__ import annotations

import argparse
import json
from pathlib import Path

from qm_automation.models import RunResult, TemplateProfile
from qm_automation.presets import available_presets, format_preset_help, resolve_profile


def add_common_arguments(
    parser: argparse.ArgumentParser,
    include_basis: bool = True,
    task_name: str | None = None,
    engine_choices: tuple[str, ...] = ("auto", "orca", "gaussian", "xtb"),
) -> None:
    parser.add_argument("xyz", type=Path, help="输入 xyz 文件路径")
    parser.add_argument("--engine", choices=list(engine_choices), default="auto", help="默认按任务自动选更合适的软件")
    parser.add_argument("--preset", default="default", help="模板名。默认使用 default，也可切换到备选模板")
    parser.add_argument("--list-presets", action="store_true", help="列出当前任务与软件的可用模板后退出")
    parser.add_argument("--charge", type=int, default=0)
    parser.add_argument("--mult", type=int, default=1)
    parser.add_argument("--method", default=None, help="留空时按任务和软件自动补默认方法")
    if include_basis:
        parser.add_argument("--basis", default=None, help="留空时按任务和软件自动补默认基组；复合方法可为空")
    parser.add_argument("--nprocs", type=int, default=8)
    parser.add_argument("--memory", type=int, default=2048, help="每核 MB，ORCA 常用")
    parser.add_argument("--runs-root", type=Path, default=None, help="运行目录根路径，默认是当前目录下的 runs")
    parser.add_argument("--config-file", type=Path, default=None, help="JSON 配置文件路径，可统一写软件路径和 runs_root")
    parser.add_argument("--orca-cmd", default=None, help="直接指定 ORCA 可执行程序或启动脚本路径")
    parser.add_argument("--gaussian-cmd", default=None, help="直接指定 Gaussian 可执行程序或启动脚本路径")
    parser.add_argument("--xtb-cmd", default=None, help="直接指定 xTB 可执行程序路径")
    parser.add_argument("--crest-cmd", default=None, help="直接指定 CREST 可执行程序路径")
    parser.add_argument("--dry-run", action="store_true", help="只生成输入和命令文件，不真正提交计算")
    if task_name:
        parser.epilog = f"默认模式: {task_name} 会优先选择更常见、更顺手的软件，而不是固定 ORCA。"


def recommend_engine(task_name: str) -> str:
    recommendations = {
        "optimize": "orca",
        "frequency": "gaussian",
        "single_point": "orca",
        "uvvis": "gaussian",
        "ecd": "gaussian",
        "nmr": "orca",
        "raman": "orca",
        "ir": "gaussian",
        "vcd": "orca",
        "nearir": "orca",
        "ts_retry": "orca",
        "scan": "orca",
        "irc": "orca",
        "neb": "orca",
    }
    return recommendations.get(task_name, "orca")


def result_to_payload(result: RunResult) -> dict[str, object]:
    return {
        "success": result.success,
        "dry_run": result.dry_run,
        "engine": result.engine,
        "work_dir": str(result.work_dir),
        "final_xyz": str(result.final_xyz) if result.final_xyz else None,
        "energy_hartree": result.energy_hartree,
        "primary_input": str(result.primary_input) if result.primary_input else None,
        "command_file": str(result.command_file) if result.command_file else None,
        "shell_command_file": str(result.shell_command_file) if result.shell_command_file else None,
        "powershell_command_file": str(result.powershell_command_file) if result.powershell_command_file else None,
        "command_line": result.command_line,
        "stdout": str(result.stdout_file),
        "stderr": str(result.stderr_file),
        "metadata": str(result.metadata_file),
        "attempt_count": result.attempt_count,
        "message": result.message,
    }


def resolve_engine(task_name: str, engine: str) -> str:
    return recommend_engine(task_name) if engine == "auto" else engine


def resolve_method_basis(task_name: str, engine: str, method: str | None, basis: str | None) -> tuple[str, str]:
    defaults = {
        ("optimize", "orca"): ("r2scan-3c", ""),
        ("optimize", "gaussian"): ("b3lyp", "6-31g(d)"),
        ("optimize", "xtb"): ("2", ""),
        ("frequency", "orca"): ("r2scan-3c", ""),
        ("frequency", "gaussian"): ("b3lyp", "6-31g(d)"),
        ("single_point", "orca"): ("wb97x-d4", "def2-TZVP"),
        ("single_point", "gaussian"): ("m062x", "def2TZVP"),
        ("single_point", "xtb"): ("2", ""),
        ("uvvis", "orca"): ("cam-b3lyp", "def2-TZVPD"),
        ("uvvis", "gaussian"): ("cam-b3lyp", "def2TZVP"),
        ("ecd", "orca"): ("cam-b3lyp", "def2-TZVPD"),
        ("ecd", "gaussian"): ("cam-b3lyp", "def2TZVP"),
        ("nmr", "orca"): ("pbe0", "pcSseg-2"),
        ("nmr", "gaussian"): ("b3lyp", "6-311+g(2d,p)"),
        ("raman", "orca"): ("pbe0", "def2-TZVP"),
        ("raman", "gaussian"): ("b3lyp", "6-31+g(d,p)"),
        ("ir", "orca"): ("r2scan-3c", ""),
        ("ir", "gaussian"): ("b3lyp", "6-31g(d)"),
        ("vcd", "orca"): ("b3lyp", "def2-SVP"),
        ("nearir", "orca"): ("b3lyp", "def2-TZVP"),
        ("ts_retry", "orca"): ("r2scan-3c", ""),
    }
    default_method, default_basis = defaults[(task_name, engine)]
    return method or default_method, basis if basis is not None else default_basis


def resolve_template_profile(task_name: str, engine: str, preset: str, method: str | None, basis: str | None) -> TemplateProfile:
    return resolve_profile(task_name, engine, preset, method, basis)


def maybe_print_presets(task_name: str, engine: str, list_presets: bool) -> bool:
    if not list_presets:
        return False
    print(format_preset_help(task_name, engine))
    return True


def print_result(result: RunResult) -> None:
    print(json.dumps(result_to_payload(result), ensure_ascii=False, indent=2))


def print_results(results: list[RunResult]) -> None:
    print(json.dumps([result_to_payload(result) for result in results], ensure_ascii=False, indent=2))