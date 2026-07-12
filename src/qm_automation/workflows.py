from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import replace
from pathlib import Path
import shutil

from qm_automation.config import AppConfig
from qm_automation.engines import run_crest_job, run_gaussian_job, run_orca_job, run_xtb_job
from qm_automation.io import read_xyz
from qm_automation.models import RetryProfile, RunResult, TemplateProfile
from qm_automation.reporting import write_results_csv, write_results_json
from qm_automation.templates import (
    render_orca_elprop_block,
    render_orca_eprnmr_block,
    render_orca_irc_block,
    render_orca_neb_block,
    render_orca_scan_block,
    render_orca_tddft_block,
)
from qm_automation.workspace import create_task_context


def default_orca_retries(task_type: str) -> list[RetryProfile]:
    # ORCA 在自动化里更适合承担“反复试错”的角色，所以这里集中封装重试策略。
    base = [RetryProfile(labels=["base"])]
    if task_type == "ts":
        return base + [
            RetryProfile(labels=["slowconv"], extra_keywords=["SlowConv", "VeryTightSCF"]),
            RetryProfile(labels=["cnvg"], extra_keywords=["SlowConv", "SOSCF"], maxcore_step_mb=512),
        ]
    return base + [
        RetryProfile(labels=["slowconv"], extra_keywords=["SlowConv"]),
        RetryProfile(labels=["soscf"], extra_keywords=["SlowConv", "SOSCF"], maxcore_step_mb=256),
    ]


def optimize_structure(
    config: AppConfig,
    xyz_path: Path,
    profile: TemplateProfile,
    charge: int,
    mult: int,
    nprocs: int,
    memory: int,
) -> RunResult:
    # 几何优化默认优先 ORCA：一方面它对现代复合方法友好，另一方面重试参数更容易程序化管理。
    molecule = read_xyz(xyz_path)
    context = create_task_context(config.runs_root, "optimize", molecule.name)
    if profile.engine == "orca":
        return run_orca_job(config, context, molecule, profile, charge, mult, nprocs, memory, default_orca_retries("opt"))
    if profile.engine == "gaussian":
        return run_gaussian_job(config, context, molecule, profile, charge, mult, nprocs, max(memory // 1024, 1))
    if profile.engine == "xtb":
        profile = replace(profile, extra_flags=(*profile.extra_flags, "--parallel", str(nprocs)))
        return run_xtb_job(config, context, molecule, profile, charge, mult)
    raise ValueError(f"不支持的引擎: {profile.engine}")


def frequency_analysis(
    config: AppConfig,
    xyz_path: Path,
    profile: TemplateProfile,
    charge: int,
    mult: int,
    nprocs: int,
    memory: int,
) -> RunResult:
    # 频率默认优先 Gaussian：很多用户更熟悉其 route section，而且频率输出格式较稳定。
    molecule = read_xyz(xyz_path)
    context = create_task_context(config.runs_root, "frequency", molecule.name)
    if profile.engine == "orca":
        return run_orca_job(config, context, molecule, profile, charge, mult, nprocs, memory, default_orca_retries("freq"))
    if profile.engine == "gaussian":
        return run_gaussian_job(config, context, molecule, profile, charge, mult, nprocs, max(memory // 1024, 1))
    raise ValueError("频率分析目前仅支持 ORCA 或 Gaussian")


def single_point_energy(
    config: AppConfig,
    xyz_path: Path,
    profile: TemplateProfile,
    charge: int,
    mult: int,
    nprocs: int,
    memory: int,
) -> RunResult:
    # 单点能默认优先 ORCA，是因为它更适合和前面的 ORCA 优化/重试链条直接衔接。
    molecule = read_xyz(xyz_path)
    context = create_task_context(config.runs_root, "single_point", molecule.name)
    if profile.engine == "orca":
        return run_orca_job(config, context, molecule, profile, charge, mult, nprocs, memory, default_orca_retries("sp"))
    if profile.engine == "gaussian":
        return run_gaussian_job(config, context, molecule, profile, charge, mult, nprocs, max(memory // 1024, 1))
    if profile.engine == "xtb":
        profile = replace(profile, extra_flags=(*profile.extra_flags, "--parallel", str(nprocs)))
        return run_xtb_job(config, context, molecule, profile, charge, mult)
    raise ValueError(f"不支持的引擎: {profile.engine}")


def ts_retry_workflow(
    config: AppConfig,
    xyz_path: Path,
    profile: TemplateProfile,
    charge: int,
    mult: int,
    nprocs: int,
    memory: int,
) -> RunResult:
    # 过渡态试错最需要程序化降级与重复尝试，目前先专注在 ORCA 上做深。
    molecule = read_xyz(xyz_path)
    context = create_task_context(config.runs_root, "ts_retry", molecule.name)
    if profile.engine != "orca":
        raise ValueError("当前过渡态自动重试工作流仅实现 ORCA")
    return run_orca_job(config, context, molecule, profile, charge, mult, nprocs, memory, default_orca_retries("ts"))


def conformer_screen_workflow(
    config: AppConfig,
    xyz_inputs: list[Path],
    charge: int,
    mult: int,
    xtb_method: str,
    orca_method: str,
    orca_basis: str,
    workers: int,
    nprocs_per_job: int,
    memory: int,
) -> list[RunResult]:
    # 构象筛选天然分层：xTB 做廉价预筛，ORCA 做后续精修，这比单一软件更贴近实际工作流。
    xtb_results: list[RunResult] = []
    for xyz_path in xyz_inputs:
        xtb_profile = TemplateProfile("optimize", "xtb", "screen", "构象预筛 xTB 模板", xtb_method, "", "--opt", (), ("--parallel", str(nprocs_per_job)))
        xtb_results.append(
            optimize_structure(
                config=config,
                xyz_path=xyz_path,
                profile=xtb_profile,
                charge=charge,
                mult=mult,
                nprocs=nprocs_per_job,
                memory=memory,
            )
        )

    successful_xtb = [result for result in xtb_results if result.final_xyz is not None]
    orca_targets = [result.final_xyz for result in successful_xtb if result.final_xyz is not None]
    if not orca_targets:
        return xtb_results

    final_results: list[RunResult] = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        orca_profile = TemplateProfile("optimize", "orca", "refine", "构象精修 ORCA 模板", orca_method, orca_basis, "OPT", ("TightSCF",), ())
        future_map = {
            executor.submit(
                optimize_structure,
                config,
                xyz_path,
                orca_profile,
                charge,
                mult,
                nprocs_per_job,
                memory,
            ): xyz_path
            for xyz_path in orca_targets
        }
        for future in as_completed(future_map):
            final_results.append(future.result())
    return xtb_results + final_results


def batch_single_point_workflow(
    config: AppConfig,
    xyz_inputs: list[Path],
    profile: TemplateProfile,
    charge: int,
    mult: int,
    workers: int,
    nprocs_per_job: int,
    memory: int,
) -> tuple[list[RunResult], Path, Path]:
    # 批量单点强调并行和统一汇总，因此在单结构工作流外再包一层批量调度与 summary 输出。
    if not xyz_inputs:
        raise ValueError("批量单点目录中未找到任何 xyz 文件")

    batch_name = xyz_inputs[0].parent.name if xyz_inputs else "empty_batch"
    batch_context = create_task_context(config.runs_root, "batch_single_point", batch_name)
    results: list[RunResult] = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_map = {
            executor.submit(
                single_point_energy,
                config,
                xyz_path,
                profile,
                charge,
                mult,
                nprocs_per_job,
                memory,
            ): xyz_path
            for xyz_path in xyz_inputs
        }
        for future in as_completed(future_map):
            results.append(future.result())

    results.sort(key=lambda item: str(item.primary_input or item.work_dir))
    csv_file = batch_context.results_dir / "batch_summary.csv"
    json_file = batch_context.results_dir / "batch_summary.json"
    write_results_csv(csv_file, results)
    write_results_json(json_file, results)
    return results, csv_file, json_file


def batch_optimize_workflow(
    config: AppConfig,
    xyz_inputs: list[Path],
    profile: TemplateProfile,
    charge: int,
    mult: int,
    workers: int,
    nprocs_per_job: int,
    memory: int,
) -> tuple[list[RunResult], Path, Path]:
    if not xyz_inputs:
        raise ValueError("批量优化目录中未找到任何 xyz 文件")

    batch_name = xyz_inputs[0].parent.name
    batch_context = create_task_context(config.runs_root, "batch_optimize", batch_name)
    results: list[RunResult] = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_map = {
            executor.submit(
                optimize_structure,
                config,
                xyz_path,
                profile,
                charge,
                mult,
                nprocs_per_job,
                memory,
            ): xyz_path
            for xyz_path in xyz_inputs
        }
        for future in as_completed(future_map):
            results.append(future.result())

    results.sort(key=lambda item: str(item.primary_input or item.work_dir))
    csv_file = batch_context.results_dir / "batch_optimize_summary.csv"
    json_file = batch_context.results_dir / "batch_optimize_summary.json"
    write_results_csv(csv_file, results)
    write_results_json(json_file, results)
    return results, csv_file, json_file


def scan_workflow(
    config: AppConfig,
    xyz_path: Path,
    profile: TemplateProfile,
    charge: int,
    mult: int,
    nprocs: int,
    memory: int,
    scan_type: str,
    atom_indices: tuple[int, ...],
    start: float,
    stop: float,
    steps: int,
) -> RunResult:
    # 势能面扫描需要在原始 ORCA 输入中显式附加 %geom Scan 块，因此单独抽成任务脚本。
    if profile.engine != "orca":
        raise ValueError("当前 scan 工作流仅实现 ORCA")
    molecule = read_xyz(xyz_path)
    context = create_task_context(config.runs_root, "scan", molecule.name)
    scan_block = render_orca_scan_block(scan_type, atom_indices, start, stop, steps)
    return run_orca_job(
        config,
        context,
        molecule,
        profile,
        charge,
        mult,
        nprocs,
        memory,
        default_orca_retries("opt"),
        extra_blocks=(scan_block,),
    )


def irc_workflow(
    config: AppConfig,
    xyz_path: Path,
    profile: TemplateProfile,
    charge: int,
    mult: int,
    nprocs: int,
    memory: int,
    direction: str,
    max_points: int,
    step_size: float,
) -> RunResult:
    # IRC 通常建立在已确认的 TS 结构上，这里先实现 ORCA 版路径跟踪。
    if profile.engine != "orca":
        raise ValueError("当前 irc 工作流仅实现 ORCA")
    molecule = read_xyz(xyz_path)
    context = create_task_context(config.runs_root, f"irc_{direction}", molecule.name)
    irc_block = render_orca_irc_block(direction, max_points, step_size)
    return run_orca_job(
        config,
        context,
        molecule,
        profile,
        charge,
        mult,
        nprocs,
        memory,
        default_orca_retries("ts"),
        extra_blocks=(irc_block,),
    )


def irc_pair_workflow(
    config: AppConfig,
    xyz_path: Path,
    profile: TemplateProfile,
    charge: int,
    mult: int,
    nprocs: int,
    memory: int,
    max_points: int,
    step_size: float,
) -> tuple[list[RunResult], Path, Path]:
    molecule = read_xyz(xyz_path)
    summary_context = create_task_context(config.runs_root, "irc_pair", molecule.name)
    results = [
        irc_workflow(config, xyz_path, profile, charge, mult, nprocs, memory, "forward", max_points, step_size),
        irc_workflow(config, xyz_path, profile, charge, mult, nprocs, memory, "backward", max_points, step_size),
    ]
    csv_file = summary_context.results_dir / "irc_pair_summary.csv"
    json_file = summary_context.results_dir / "irc_pair_summary.json"
    write_results_csv(csv_file, results)
    write_results_json(json_file, results)
    return results, csv_file, json_file


def neb_workflow(
    config: AppConfig,
    reactant_xyz: Path,
    product_xyz: Path,
    profile: TemplateProfile,
    charge: int,
    mult: int,
    nprocs: int,
    memory: int,
    images: int,
    preopt: bool,
) -> RunResult:
    # NEB 需要反应物和产物双端点文件，因此在每次尝试目录中额外复制 product.xyz。
    if profile.engine != "orca":
        raise ValueError("当前 neb 工作流仅实现 ORCA")
    molecule = read_xyz(reactant_xyz)
    context = create_task_context(config.runs_root, "neb", molecule.name)
    neb_block = render_orca_neb_block("product.xyz", images, preopt)

    def setup_attempt_dir(attempt_dir: Path) -> None:
        shutil.copy2(product_xyz, attempt_dir / "product.xyz")

    return run_orca_job(
        config,
        context,
        molecule,
        profile,
        charge,
        mult,
        nprocs,
        memory,
        default_orca_retries("ts"),
        extra_blocks=(neb_block,),
        setup_attempt_dir=setup_attempt_dir,
    )


def crest_search_workflow(
    config: AppConfig,
    xyz_path: Path,
    profile: TemplateProfile,
    charge: int,
    mult: int,
    nprocs: int,
    keepdir: bool,
) -> RunResult:
    molecule = read_xyz(xyz_path)
    context = create_task_context(config.runs_root, "crest", molecule.name)
    extra_flags = ("--keepdir",) if keepdir else ()
    return run_crest_job(config, context, molecule, profile, charge, mult, nprocs, extra_flags=extra_flags)


def _append_profile_keywords(profile: TemplateProfile, *keywords: str) -> TemplateProfile:
    extra = tuple(keyword for keyword in keywords if keyword)
    return replace(profile, extra_keywords=profile.extra_keywords + extra)


def _apply_solvent_keywords(profile: TemplateProfile, solvent: str | None, solvent_model: str) -> TemplateProfile:
    if not solvent:
        return profile
    model = solvent_model.lower()
    if profile.engine == "orca":
        if model not in {"auto", "cpcm", "pcm"}:
            raise ValueError("ORCA 当前仅通过 CPCM 暴露隐式溶剂，请使用 --solvent-model auto/cpcm")
        return _append_profile_keywords(profile, f"CPCM({solvent})")
    if profile.engine == "gaussian":
        if model == "auto":
            model = "smd"
        if model == "smd":
            return _append_profile_keywords(profile, f"scrf=(smd,solvent={solvent})")
        if model in {"pcm", "cpcm"}:
            return _append_profile_keywords(profile, f"scrf=(pcm,solvent={solvent})")
        raise ValueError("Gaussian 当前支持 --solvent-model auto/smd/pcm")
    raise ValueError(f"当前引擎不支持隐式溶剂: {profile.engine}")


def _molecule_elements(molecule) -> tuple[str, ...]:
    elements: list[str] = []
    for line in molecule.atoms_block.splitlines():
        parts = line.split()
        if not parts:
            continue
        element = parts[0]
        if element not in elements:
            elements.append(element)
    return tuple(elements)


def electronic_spectrum_workflow(
    config: AppConfig,
    xyz_path: Path,
    profile: TemplateProfile,
    charge: int,
    mult: int,
    nprocs: int,
    memory: int,
    *,
    task_name: str,
    nstates: int,
    solvent: str | None,
    solvent_model: str,
    use_tda: bool,
    include_triplets: bool,
    do_nto: bool,
    simplified_mode: str,
) -> RunResult:
    molecule = read_xyz(xyz_path)
    context = create_task_context(config.runs_root, task_name, molecule.name)
    profile = _apply_solvent_keywords(profile, solvent, solvent_model)
    if profile.engine == "orca":
        tddft_block = render_orca_tddft_block(nstates, use_tda, include_triplets, do_nto, simplified_mode)
        return run_orca_job(
            config,
            context,
            molecule,
            profile,
            charge,
            mult,
            nprocs,
            memory,
            default_orca_retries("sp"),
            extra_blocks=(tddft_block,),
        )
    if profile.engine == "gaussian":
        td_options = [f"nstates={nstates}"]
        if include_triplets:
            td_options.append("triplets")
        gaussian_profile = _append_profile_keywords(profile, f"td=({','.join(td_options)})", "tda" if use_tda else "")
        return run_gaussian_job(config, context, molecule, gaussian_profile, charge, mult, nprocs, max(memory // 1024, 1))
    raise ValueError("电子光谱工作流目前仅支持 ORCA 或 Gaussian")


def nmr_workflow(
    config: AppConfig,
    xyz_path: Path,
    profile: TemplateProfile,
    charge: int,
    mult: int,
    nprocs: int,
    memory: int,
    *,
    solvent: str | None,
    solvent_model: str,
    gauge: str,
    include_spinspin: bool,
    spinspin_elements: tuple[str, ...],
    spinspin_rthresh: float,
    print_reduced_coupling: bool,
) -> RunResult:
    molecule = read_xyz(xyz_path)
    context = create_task_context(config.runs_root, "nmr", molecule.name)
    profile = _apply_solvent_keywords(profile, solvent, solvent_model)
    gauge_name = gauge.lower()
    if profile.engine == "orca":
        if gauge_name != "giao":
            raise ValueError("ORCA 当前工作流仅开放 GIAO NMR，请使用 --gauge giao")
        selected_elements = spinspin_elements or _molecule_elements(molecule)
        eprnmr_block = render_orca_eprnmr_block(
            shift_all=True,
            spinspin_elements=selected_elements if include_spinspin else (),
            spinspin_rthresh=spinspin_rthresh,
            print_reduced_coupling=print_reduced_coupling,
        )
        orca_profile = _append_profile_keywords(profile, "NMR")
        return run_orca_job(
            config,
            context,
            molecule,
            orca_profile,
            charge,
            mult,
            nprocs,
            memory,
            default_orca_retries("sp"),
            extra_blocks=(eprnmr_block,),
        )
    if profile.engine == "gaussian":
        nmr_options = [gauge_name.upper()]
        if include_spinspin:
            nmr_options.append("SpinSpin")
        gaussian_profile = _append_profile_keywords(profile, f"nmr=({','.join(nmr_options)})")
        return run_gaussian_job(config, context, molecule, gaussian_profile, charge, mult, nprocs, max(memory // 1024, 1))
    raise ValueError("NMR 工作流目前仅支持 ORCA 或 Gaussian")


def raman_workflow(
    config: AppConfig,
    xyz_path: Path,
    profile: TemplateProfile,
    charge: int,
    mult: int,
    nprocs: int,
    memory: int,
    *,
    solvent: str | None,
    solvent_model: str,
) -> RunResult:
    molecule = read_xyz(xyz_path)
    context = create_task_context(config.runs_root, "raman", molecule.name)
    profile = _apply_solvent_keywords(profile, solvent, solvent_model)
    if profile.engine == "orca":
        return run_orca_job(
            config,
            context,
            molecule,
            profile,
            charge,
            mult,
            nprocs,
            memory,
            default_orca_retries("freq"),
            extra_blocks=(render_orca_elprop_block(1),),
        )
    if profile.engine == "gaussian":
        return run_gaussian_job(config, context, molecule, profile, charge, mult, nprocs, max(memory // 1024, 1))
    raise ValueError("Raman 工作流目前仅支持 ORCA 或 Gaussian")


def ir_workflow(
    config: AppConfig,
    xyz_path: Path,
    profile: TemplateProfile,
    charge: int,
    mult: int,
    nprocs: int,
    memory: int,
    *,
    solvent: str | None,
    solvent_model: str,
) -> RunResult:
    molecule = read_xyz(xyz_path)
    context = create_task_context(config.runs_root, "ir", molecule.name)
    profile = _apply_solvent_keywords(profile, solvent, solvent_model)
    if profile.engine == "orca":
        return run_orca_job(config, context, molecule, profile, charge, mult, nprocs, memory, default_orca_retries("freq"))
    if profile.engine == "gaussian":
        return run_gaussian_job(config, context, molecule, profile, charge, mult, nprocs, max(memory // 1024, 1))
    raise ValueError("IR 工作流目前仅支持 ORCA 或 Gaussian")


def vcd_workflow(
    config: AppConfig,
    xyz_path: Path,
    profile: TemplateProfile,
    charge: int,
    mult: int,
    nprocs: int,
    memory: int,
    *,
    solvent: str | None,
    solvent_model: str,
) -> RunResult:
    if profile.engine != "orca":
        raise ValueError("VCD 工作流当前仅实现 ORCA")
    molecule = read_xyz(xyz_path)
    context = create_task_context(config.runs_root, "vcd", molecule.name)
    profile = _apply_solvent_keywords(profile, solvent, solvent_model)
    freq_block = "\n".join(["%freq", "  doVCD true", "end"])
    return run_orca_job(
        config,
        context,
        molecule,
        profile,
        charge,
        mult,
        nprocs,
        memory,
        default_orca_retries("freq"),
        extra_blocks=(freq_block,),
    )


def nearir_workflow(
    config: AppConfig,
    xyz_path: Path,
    profile: TemplateProfile,
    charge: int,
    mult: int,
    nprocs: int,
    memory: int,
    *,
    solvent: str | None,
    solvent_model: str,
    use_xtb_vpt2: bool,
    delq: float | None,
) -> RunResult:
    if profile.engine != "orca":
        raise ValueError("Near-IR 工作流当前仅实现 ORCA")
    molecule = read_xyz(xyz_path)
    context = create_task_context(config.runs_root, "nearir", molecule.name)
    profile = _apply_solvent_keywords(profile, solvent, solvent_model)
    block_lines = ["%freq", f"  XTBVPT2 {'true' if use_xtb_vpt2 else 'false'}"]
    if delq is not None:
        block_lines.append(f"  DELQ {delq:.6f}")
    block_lines.append("end")
    return run_orca_job(
        config,
        context,
        molecule,
        profile,
        charge,
        mult,
        nprocs,
        memory,
        default_orca_retries("freq"),
        extra_blocks=("\n".join(block_lines),),
    )