from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
from dataclasses import asdict
from pathlib import Path
from typing import Callable

from qm_automation.config import AppConfig
from qm_automation.io import write_xyz
from qm_automation.models import Molecule, RetryProfile, RunResult, TaskContext, TemplateProfile
from qm_automation.parsing import extract_energy_hartree, extract_gaussian_final_xyz
from qm_automation.templates import render_gaussian_input, render_orca_input, render_xtb_command


def _write_metadata(result: RunResult) -> None:
    payload = asdict(result)
    payload = {key: str(value) if isinstance(value, Path) else value for key, value in payload.items()}
    result.metadata_file.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _copy_if_exists(source: Path, target: Path) -> Path | None:
    if source.exists():
        shutil.copy2(source, target)
        return target
    return None


def _quote_command(command: list[str]) -> str:
    return shlex.join(command)


def _render_powershell_command(command: list[str]) -> str:
    escaped = [f'"{part.replace("\"", "`\"")}"' for part in command]
    return " ".join(escaped)


def _write_command_files(command_dir: Path, prefix: str, command: list[str], working_dir: Path) -> tuple[Path, Path, Path, str]:
    # 同时生成通用文本、Linux shell、Windows PowerShell 三种复跑脚本。
    command_line = _quote_command(command)
    command_file = command_dir / f"{prefix}.txt"
    shell_file = command_dir / f"{prefix}.sh"
    powershell_file = command_dir / f"{prefix}.ps1"
    command_file.write_text(f"cwd: {working_dir}\n{command_line}\n", encoding="utf-8")
    shell_file.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        f"cd {shlex.quote(str(working_dir))}\n"
        f"{command_line}\n",
        encoding="utf-8",
    )
    powershell_file.write_text(
        f"Set-Location \"{working_dir}\"\n{_render_powershell_command(command)}\n",
        encoding="utf-8",
    )
    try:
        os.chmod(shell_file, 0o755)
    except OSError:
        pass
    return command_file, shell_file, powershell_file, command_line


def _build_result(
    *,
    success: bool,
    engine: str,
    context: TaskContext,
    final_xyz: Path | None,
    energy_hartree: float | None,
    primary_input: Path | None,
    command_file: Path | None,
    shell_command_file: Path | None,
    powershell_command_file: Path | None,
    command_line: str,
    stdout_file: Path,
    stderr_file: Path,
    metadata_file: Path,
    attempt_count: int,
    message: str,
    dry_run: bool,
) -> RunResult:
    result = RunResult(
        success=success,
        engine=engine,
        work_dir=context.run_dir,
        final_xyz=final_xyz,
        energy_hartree=energy_hartree,
        primary_input=primary_input,
        command_file=command_file,
        shell_command_file=shell_command_file,
        powershell_command_file=powershell_command_file,
        command_line=command_line,
        stdout_file=stdout_file,
        stderr_file=stderr_file,
        metadata_file=metadata_file,
        attempt_count=attempt_count,
        message=message,
        dry_run=dry_run,
    )
    _write_metadata(result)
    return result


def _completed_process_success(stdout: Path, stderr: Path, returncode: int, markers: tuple[str, ...]) -> bool:
    if returncode != 0:
        return False
    stdout_text = stdout.read_text(encoding="utf-8", errors="ignore") if stdout.exists() else ""
    stderr_text = stderr.read_text(encoding="utf-8", errors="ignore") if stderr.exists() else ""
    text = "\n".join([stdout_text, stderr_text])
    return any(marker.lower() in text.lower() for marker in markers)


def _missing_command_result(engine: str, context: TaskContext, stdout_file: Path, stderr_file: Path, metadata_file: Path, attempt_count: int) -> RunResult:
    return _build_result(
        success=False,
        engine=engine,
        context=context,
        final_xyz=None,
        energy_hartree=None,
        primary_input=None,
        command_file=None,
        shell_command_file=None,
        powershell_command_file=None,
        command_line="",
        stdout_file=stdout_file,
        stderr_file=stderr_file,
        metadata_file=metadata_file,
        attempt_count=attempt_count,
        message=f"未找到 {engine} 可执行程序，请检查环境变量或安装配置",
        dry_run=False,
    )


def _completion_message(engine: str, success: bool, final_xyz: Path | None, failure_message: str) -> str:
    if not success:
        return failure_message
    if final_xyz is None:
        return f"{engine} 任务完成，未检测到导出的最终结构文件"
    return f"{engine} 任务完成"


def run_orca_job(
    config: AppConfig,
    context: TaskContext,
    molecule: Molecule,
    profile: TemplateProfile,
    charge: int,
    mult: int,
    nprocs: int,
    maxcore_mb: int,
    retries: list[RetryProfile],
    extra_blocks: tuple[str, ...] = (),
    setup_attempt_dir: Callable[[Path], None] | None = None,
) -> RunResult:
    final_xyz = None
    success = False
    attempts_used = 0
    stdout_file = context.logs_dir / "orca.stdout.log"
    stderr_file = context.logs_dir / "orca.stderr.log"
    metadata_file = context.results_dir / "run_metadata.json"
    last_input_file: Path | None = None
    last_command_file: Path | None = None
    last_shell_file: Path | None = None
    last_powershell_file: Path | None = None
    last_command_line = ""

    for index, retry in enumerate(retries, start=1):
        attempts_used = index
        attempt_dir = context.attempts_dir / f"attempt_{index:02d}"
        attempt_dir.mkdir(parents=True, exist_ok=False)
        input_file = attempt_dir / "job.inp"
        last_input_file = input_file
        input_file.write_text(
            render_orca_input(
                molecule=molecule,
                task_directive=profile.driver,
                method=profile.method,
                basis=profile.basis,
                charge=charge,
                mult=mult,
                nprocs=nprocs,
                maxcore_mb=maxcore_mb + retry.maxcore_step_mb,
                retry=retry,
                extra_keywords=profile.extra_keywords,
                extra_blocks=extra_blocks,
            ),
            encoding="utf-8",
        )
        write_xyz(attempt_dir / f"{molecule.name}.xyz", molecule)
        if setup_attempt_dir is not None:
            setup_attempt_dir(attempt_dir)
        command = [config.orca.command, input_file.name]
        last_command_file, last_shell_file, last_powershell_file, last_command_line = _write_command_files(
            context.command_dir,
            f"orca_attempt_{index:02d}",
            command,
            attempt_dir,
        )
        if config.dry_run:
            return _build_result(
                success=True,
                engine="orca",
                context=context,
                final_xyz=None,
                energy_hartree=None,
                primary_input=last_input_file,
                command_file=last_command_file,
                shell_command_file=last_shell_file,
                powershell_command_file=last_powershell_file,
                command_line=last_command_line,
                stdout_file=stdout_file,
                stderr_file=stderr_file,
                metadata_file=metadata_file,
                attempt_count=attempts_used,
                message="ORCA dry-run 完成，已生成输入文件和命令文件",
                dry_run=True,
            )
        try:
            with stdout_file.open("a", encoding="utf-8") as stdout_handle, stderr_file.open("a", encoding="utf-8") as stderr_handle:
                completed = subprocess.run(
                    command,
                    cwd=attempt_dir,
                    stdout=stdout_handle,
                    stderr=stderr_handle,
                    text=True,
                    check=False,
                )
        except FileNotFoundError:
            return _missing_command_result("orca", context, stdout_file, stderr_file, metadata_file, attempts_used)
        candidate_xyz = attempt_dir / "job.xyz"
        copied = _copy_if_exists(candidate_xyz, context.results_dir / f"final_attempt_{index:02d}.xyz")
        if _completed_process_success(stdout_file, stderr_file, completed.returncode, ("orca terminated normally",)):
            success = True
            final_xyz = copied
            break

    return _build_result(
        success=success,
        engine="orca",
        context=context,
        final_xyz=final_xyz,
        energy_hartree=extract_energy_hartree("orca", stdout_file, stderr_file),
        primary_input=last_input_file,
        command_file=last_command_file,
        shell_command_file=last_shell_file,
        powershell_command_file=last_powershell_file,
        command_line=last_command_line,
        stdout_file=stdout_file,
        stderr_file=stderr_file,
        metadata_file=metadata_file,
        attempt_count=attempts_used,
        message=_completion_message("ORCA", success, final_xyz, "ORCA 任务失败，已耗尽重试策略"),
        dry_run=False,
    )


def run_gaussian_job(
    config: AppConfig,
    context: TaskContext,
    molecule: Molecule,
    profile: TemplateProfile,
    charge: int,
    mult: int,
    nprocs: int,
    mem_gb: int,
    footer_lines: tuple[str, ...] = (),
) -> RunResult:
    input_file = context.input_dir / "job.gjf"
    stdout_file = context.logs_dir / "gaussian.stdout.log"
    stderr_file = context.logs_dir / "gaussian.stderr.log"
    metadata_file = context.results_dir / "run_metadata.json"
    route_parts = [profile.driver, *profile.extra_keywords]
    if profile.basis:
        route_parts.append(f"{profile.method}/{profile.basis}")
    else:
        route_parts.append(profile.method)
    input_file.write_text(
        render_gaussian_input(
            molecule=molecule,
            route=" ".join(route_parts),
            charge=charge,
            mult=mult,
            nprocs=nprocs,
            mem_gb=mem_gb,
            footer_lines=footer_lines,
        ),
        encoding="utf-8",
    )
    command = [config.gaussian.command, input_file.name]
    command_file, shell_file, powershell_file, command_line = _write_command_files(context.command_dir, "gaussian_command", command, context.input_dir)
    if config.dry_run:
        return _build_result(
            success=True,
            engine="gaussian",
            context=context,
            final_xyz=None,
            energy_hartree=None,
            primary_input=input_file,
            command_file=command_file,
            shell_command_file=shell_file,
            powershell_command_file=powershell_file,
            command_line=command_line,
            stdout_file=stdout_file,
            stderr_file=stderr_file,
            metadata_file=metadata_file,
            attempt_count=1,
            message="Gaussian dry-run 完成，已生成输入文件和命令文件",
            dry_run=True,
        )
    try:
        with stdout_file.open("w", encoding="utf-8") as stdout_handle, stderr_file.open("w", encoding="utf-8") as stderr_handle:
            completed = subprocess.run(
                command,
                cwd=context.input_dir,
                stdout=stdout_handle,
                stderr=stderr_handle,
                text=True,
                check=False,
            )
    except FileNotFoundError:
        return _missing_command_result("gaussian", context, stdout_file, stderr_file, metadata_file, 1)
    success = _completed_process_success(stdout_file, stderr_file, completed.returncode, ("normal termination",))
    final_xyz = _copy_if_exists(context.input_dir / "job.xyz", context.results_dir / "final.xyz")
    if final_xyz is None and "opt" in profile.driver.lower():
        final_xyz = extract_gaussian_final_xyz(stdout_file, stderr_file, context.results_dir / "final.xyz", molecule.name)
    return _build_result(
        success=success,
        engine="gaussian",
        context=context,
        final_xyz=final_xyz,
        energy_hartree=extract_energy_hartree("gaussian", stdout_file, stderr_file),
        primary_input=input_file,
        command_file=command_file,
        shell_command_file=shell_file,
        powershell_command_file=powershell_file,
        command_line=command_line,
        stdout_file=stdout_file,
        stderr_file=stderr_file,
        metadata_file=metadata_file,
        attempt_count=1,
        message=_completion_message("Gaussian", success, final_xyz, "Gaussian 任务失败"),
        dry_run=False,
    )


def run_xtb_job(
    config: AppConfig,
    context: TaskContext,
    molecule: Molecule,
    profile: TemplateProfile,
    charge: int,
    mult: int,
) -> RunResult:
    stdout_file = context.logs_dir / "xtb.stdout.log"
    stderr_file = context.logs_dir / "xtb.stderr.log"
    metadata_file = context.results_dir / "run_metadata.json"
    xyz_file = context.input_dir / f"{molecule.name}.xyz"
    write_xyz(xyz_file, molecule)
    command = [
        config.xtb.command,
        *render_xtb_command(xyz_file.name, profile.driver, charge, mult, profile.method, list(profile.extra_flags)),
    ]
    command_file, shell_file, powershell_file, command_line = _write_command_files(context.command_dir, "xtb_command", command, context.input_dir)
    if config.dry_run:
        return _build_result(
            success=True,
            engine="xtb",
            context=context,
            final_xyz=None,
            energy_hartree=None,
            primary_input=xyz_file,
            command_file=command_file,
            shell_command_file=shell_file,
            powershell_command_file=powershell_file,
            command_line=command_line,
            stdout_file=stdout_file,
            stderr_file=stderr_file,
            metadata_file=metadata_file,
            attempt_count=1,
            message="xTB dry-run 完成，已生成输入文件和命令文件",
            dry_run=True,
        )
    try:
        with stdout_file.open("w", encoding="utf-8") as stdout_handle, stderr_file.open("w", encoding="utf-8") as stderr_handle:
            completed = subprocess.run(
                command,
                cwd=context.input_dir,
                stdout=stdout_handle,
                stderr=stderr_handle,
                text=True,
                check=False,
            )
    except FileNotFoundError:
        return _missing_command_result("xtb", context, stdout_file, stderr_file, metadata_file, 1)
    final_xyz = _copy_if_exists(context.input_dir / "xtbopt.xyz", context.results_dir / "final.xyz")
    success = _completed_process_success(stdout_file, stderr_file, completed.returncode, ("normal termination of xtb",))
    return _build_result(
        success=success,
        engine="xtb",
        context=context,
        final_xyz=final_xyz,
        energy_hartree=extract_energy_hartree("xtb", stdout_file, stderr_file),
        primary_input=xyz_file,
        command_file=command_file,
        shell_command_file=shell_file,
        powershell_command_file=powershell_file,
        command_line=command_line,
        stdout_file=stdout_file,
        stderr_file=stderr_file,
        metadata_file=metadata_file,
        attempt_count=1,
        message=_completion_message("xTB", success, final_xyz, "xTB 任务失败"),
        dry_run=False,
    )


def run_crest_job(
    config: AppConfig,
    context: TaskContext,
    molecule: Molecule,
    profile: TemplateProfile,
    charge: int,
    mult: int,
    nprocs: int,
    extra_flags: tuple[str, ...] = (),
) -> RunResult:
    stdout_file = context.logs_dir / "crest.stdout.log"
    stderr_file = context.logs_dir / "crest.stderr.log"
    metadata_file = context.results_dir / "run_metadata.json"
    xyz_file = context.input_dir / f"{molecule.name}.xyz"
    write_xyz(xyz_file, molecule)

    gfn_flag = f"--{profile.method}"
    command = [
        config.crest.command,
        xyz_file.name,
        gfn_flag,
        "--chrg",
        str(charge),
        "--uhf",
        str(max(mult - 1, 0)),
        "-T",
        str(nprocs),
        *profile.extra_flags,
        *extra_flags,
    ]
    command_file, shell_file, powershell_file, command_line = _write_command_files(context.command_dir, "crest_command", command, context.input_dir)
    if config.dry_run:
        return _build_result(
            success=True,
            engine="crest",
            context=context,
            final_xyz=None,
            energy_hartree=None,
            primary_input=xyz_file,
            command_file=command_file,
            shell_command_file=shell_file,
            powershell_command_file=powershell_file,
            command_line=command_line,
            stdout_file=stdout_file,
            stderr_file=stderr_file,
            metadata_file=metadata_file,
            attempt_count=1,
            message="CREST dry-run 完成，已生成输入文件和命令文件",
            dry_run=True,
        )
    try:
        with stdout_file.open("w", encoding="utf-8") as stdout_handle, stderr_file.open("w", encoding="utf-8") as stderr_handle:
            completed = subprocess.run(
                command,
                cwd=context.input_dir,
                stdout=stdout_handle,
                stderr=stderr_handle,
                text=True,
                check=False,
            )
    except FileNotFoundError:
        return _missing_command_result("crest", context, stdout_file, stderr_file, metadata_file, 1)

    final_xyz = _copy_if_exists(context.input_dir / "crest_best.xyz", context.results_dir / "crest_best.xyz")
    _copy_if_exists(context.input_dir / "crest_conformers.xyz", context.results_dir / "crest_conformers.xyz")
    success = completed.returncode == 0
    return _build_result(
        success=success,
        engine="crest",
        context=context,
        final_xyz=final_xyz,
        energy_hartree=None,
        primary_input=xyz_file,
        command_file=command_file,
        shell_command_file=shell_file,
        powershell_command_file=powershell_file,
        command_line=command_line,
        stdout_file=stdout_file,
        stderr_file=stderr_file,
        metadata_file=metadata_file,
        attempt_count=1,
        message=_completion_message("CREST", success, final_xyz, "CREST 任务失败"),
        dry_run=False,
    )