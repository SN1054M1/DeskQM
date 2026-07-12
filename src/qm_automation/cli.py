from __future__ import annotations

import argparse
import json
from pathlib import Path

from qm_automation.cli_shared import add_common_arguments, maybe_print_presets, print_result, print_results, resolve_engine, resolve_template_profile
from qm_automation.config import load_config
from qm_automation.parsing import extract_energy_series
from qm_automation.reporting import build_scan_profile, write_scan_profile_csv, write_scan_profile_json
from qm_automation.workflows import (
    batch_optimize_workflow,
    batch_single_point_workflow,
    crest_search_workflow,
    electronic_spectrum_workflow,
    frequency_analysis,
    ir_workflow,
    irc_pair_workflow,
    irc_workflow,
    nearir_workflow,
    nmr_workflow,
    neb_workflow,
    optimize_structure,
    raman_workflow,
    scan_workflow,
    single_point_energy,
    ts_retry_workflow,
    vcd_workflow,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="qm-auto", description="QM automation command line entrypoint")
    subparsers = parser.add_subparsers(dest="task", required=True)

    def add_solvation_arguments(task_parser: argparse.ArgumentParser) -> None:
        task_parser.add_argument("--solvent", default=None, help="隐式溶剂名，例如 water、acetonitrile、chloroform")
        task_parser.add_argument("--solvent-model", choices=["auto", "cpcm", "pcm", "smd"], default="auto", help="隐式溶剂模型；auto 会按软件选默认实现")

    optimize_parser = subparsers.add_parser("optimize")
    add_common_arguments(optimize_parser, task_name="optimize")

    freq_parser = subparsers.add_parser("frequency")
    add_common_arguments(freq_parser, task_name="frequency")

    sp_parser = subparsers.add_parser("single-point")
    add_common_arguments(sp_parser, task_name="single_point")

    uvvis_parser = subparsers.add_parser("uvvis")
    add_common_arguments(uvvis_parser, task_name="uvvis")
    add_solvation_arguments(uvvis_parser)
    uvvis_parser.add_argument("--nstates", type=int, default=20, help="请求的激发态数")
    uvvis_parser.add_argument("--tda", action="store_true", help="显式启用 TDA")
    uvvis_parser.add_argument("--triplets", action="store_true", help="同时请求 triplet roots")
    uvvis_parser.add_argument("--nto", action="store_true", help="为 ORCA 打开 NTO 分析")
    uvvis_parser.add_argument("--simplified-mode", choices=["off", "stda", "stddft"], default="off", help="ORCA 的 sTDA/sTDDFT 近似模式")

    ecd_parser = subparsers.add_parser("ecd")
    add_common_arguments(ecd_parser, task_name="ecd")
    add_solvation_arguments(ecd_parser)
    ecd_parser.add_argument("--nstates", type=int, default=30, help="请求的激发态数")
    ecd_parser.add_argument("--tda", action="store_true", help="显式启用 TDA")
    ecd_parser.add_argument("--triplets", action="store_true", help="同时请求 triplet roots")
    ecd_parser.add_argument("--nto", action="store_true", help="为 ORCA 打开 NTO 分析")
    ecd_parser.add_argument("--simplified-mode", choices=["off", "stda", "stddft"], default="off", help="ORCA 的 sTDA/sTDDFT 近似模式")

    nmr_parser = subparsers.add_parser("nmr")
    add_common_arguments(nmr_parser, task_name="nmr")
    add_solvation_arguments(nmr_parser)
    nmr_parser.add_argument("--gauge", choices=["giao", "csgt"], default="giao", help="NMR gauge 方案")
    nmr_parser.add_argument("--spin-spin", action="store_true", help="同时计算自旋-自旋耦合")
    nmr_parser.add_argument("--spin-spin-elements", nargs="+", default=None, help="限制自旋-自旋耦合涉及的元素，例如 C H O")
    nmr_parser.add_argument("--spin-spin-rthresh", type=float, default=5.0, help="ORCA 自旋-自旋耦合距离阈值，单位 Å")
    nmr_parser.add_argument("--reduced-coupling", action="store_true", help="ORCA 额外输出 reduced coupling 常数")

    raman_parser = subparsers.add_parser("raman")
    add_common_arguments(raman_parser, task_name="raman")
    add_solvation_arguments(raman_parser)

    ir_parser = subparsers.add_parser("ir")
    add_common_arguments(ir_parser, task_name="ir")
    add_solvation_arguments(ir_parser)

    vcd_parser = subparsers.add_parser("vcd")
    add_common_arguments(vcd_parser, task_name="vcd", engine_choices=("auto", "orca"))
    add_solvation_arguments(vcd_parser)

    nearir_parser = subparsers.add_parser("nearir")
    add_common_arguments(nearir_parser, task_name="nearir", engine_choices=("auto", "orca"))
    add_solvation_arguments(nearir_parser)
    nearir_parser.add_argument("--no-xtb-vpt2", action="store_true", help="关闭 ORCA Near-IR 默认的 xTBVPT2 近似")
    nearir_parser.add_argument("--delq", type=float, default=None, help="Near-IR/VPT2 数值位移步长")

    batch_sp_parser = subparsers.add_parser("batch-sp")
    batch_sp_parser.add_argument("xyz_dir", type=Path, help="包含多个 xyz 文件的目录")
    batch_sp_parser.add_argument("--engine", choices=["auto", "orca", "gaussian", "xtb"], default="auto")
    batch_sp_parser.add_argument("--preset", default="default")
    batch_sp_parser.add_argument("--list-presets", action="store_true")
    batch_sp_parser.add_argument("--charge", type=int, default=0)
    batch_sp_parser.add_argument("--mult", type=int, default=1)
    batch_sp_parser.add_argument("--method", default=None)
    batch_sp_parser.add_argument("--basis", default=None)
    batch_sp_parser.add_argument("--workers", type=int, default=4)
    batch_sp_parser.add_argument("--nprocs-per-job", type=int, default=4)
    batch_sp_parser.add_argument("--memory", type=int, default=2048)
    batch_sp_parser.add_argument("--runs-root", type=Path, default=None)
    batch_sp_parser.add_argument("--config-file", type=Path, default=None)
    batch_sp_parser.add_argument("--orca-cmd", default=None)
    batch_sp_parser.add_argument("--gaussian-cmd", default=None)
    batch_sp_parser.add_argument("--xtb-cmd", default=None)
    batch_sp_parser.add_argument("--crest-cmd", default=None)
    batch_sp_parser.add_argument("--dry-run", action="store_true")

    batch_opt_parser = subparsers.add_parser("batch-opt")
    batch_opt_parser.add_argument("xyz_dir", type=Path, help="包含多个 xyz 文件的目录")
    batch_opt_parser.add_argument("--engine", choices=["auto", "orca", "gaussian", "xtb"], default="auto")
    batch_opt_parser.add_argument("--preset", default="default")
    batch_opt_parser.add_argument("--list-presets", action="store_true")
    batch_opt_parser.add_argument("--charge", type=int, default=0)
    batch_opt_parser.add_argument("--mult", type=int, default=1)
    batch_opt_parser.add_argument("--method", default=None)
    batch_opt_parser.add_argument("--basis", default=None)
    batch_opt_parser.add_argument("--workers", type=int, default=4)
    batch_opt_parser.add_argument("--nprocs-per-job", type=int, default=4)
    batch_opt_parser.add_argument("--memory", type=int, default=2048)
    batch_opt_parser.add_argument("--runs-root", type=Path, default=None)
    batch_opt_parser.add_argument("--config-file", type=Path, default=None)
    batch_opt_parser.add_argument("--orca-cmd", default=None)
    batch_opt_parser.add_argument("--gaussian-cmd", default=None)
    batch_opt_parser.add_argument("--xtb-cmd", default=None)
    batch_opt_parser.add_argument("--crest-cmd", default=None)
    batch_opt_parser.add_argument("--dry-run", action="store_true")

    ts_parser = subparsers.add_parser("ts-retry")
    add_common_arguments(ts_parser, task_name="ts_retry", engine_choices=("auto", "orca"))

    scan_parser = subparsers.add_parser("scan")
    add_common_arguments(scan_parser, task_name="scan", engine_choices=("auto", "orca"))
    scan_parser.add_argument("--scan-type", choices=["B", "A", "D"], required=True)
    scan_parser.add_argument("--atoms", type=int, nargs="+", required=True)
    scan_parser.add_argument("--start", type=float, required=True)
    scan_parser.add_argument("--stop", type=float, required=True)
    scan_parser.add_argument("--steps", type=int, required=True)

    irc_parser = subparsers.add_parser("irc")
    add_common_arguments(irc_parser, task_name="irc", engine_choices=("auto", "orca"))
    irc_parser.add_argument("--direction", choices=["forward", "backward", "both"], default="both")
    irc_parser.add_argument("--max-points", type=int, default=30)
    irc_parser.add_argument("--step-size", type=float, default=0.15)

    neb_parser = subparsers.add_parser("neb")
    add_common_arguments(neb_parser, task_name="neb", engine_choices=("auto", "orca"))
    neb_parser.add_argument("--product-xyz", type=Path, required=True)
    neb_parser.add_argument("--images", type=int, default=8)
    neb_parser.add_argument("--preopt", action="store_true")

    crest_parser = subparsers.add_parser("crest")
    crest_parser.add_argument("xyz", type=Path, help="输入 xyz 文件路径")
    crest_parser.add_argument("--preset", default="default")
    crest_parser.add_argument("--list-presets", action="store_true")
    crest_parser.add_argument("--charge", type=int, default=0)
    crest_parser.add_argument("--mult", type=int, default=1)
    crest_parser.add_argument("--method", default=None)
    crest_parser.add_argument("--nprocs", type=int, default=8)
    crest_parser.add_argument("--keepdir", action="store_true")
    crest_parser.add_argument("--runs-root", type=Path, default=None)
    crest_parser.add_argument("--config-file", type=Path, default=None)
    crest_parser.add_argument("--orca-cmd", default=None)
    crest_parser.add_argument("--gaussian-cmd", default=None)
    crest_parser.add_argument("--xtb-cmd", default=None)
    crest_parser.add_argument("--crest-cmd", default=None)
    crest_parser.add_argument("--dry-run", action="store_true")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    config = load_config(
        runs_root=args.runs_root,
        orca_cmd=args.orca_cmd,
        gaussian_cmd=args.gaussian_cmd,
        xtb_cmd=args.xtb_cmd,
        crest_cmd=args.crest_cmd,
        dry_run=args.dry_run,
        config_file=args.config_file,
    )

    if args.task == "optimize":
        engine = resolve_engine("optimize", args.engine)
        if maybe_print_presets("optimize", engine, args.list_presets):
            return
        profile = resolve_template_profile("optimize", engine, args.preset, args.method, args.basis)
        result = optimize_structure(config, args.xyz, profile, args.charge, args.mult, args.nprocs, args.memory)
    elif args.task == "frequency":
        engine = resolve_engine("frequency", args.engine)
        if maybe_print_presets("frequency", engine, args.list_presets):
            return
        profile = resolve_template_profile("frequency", engine, args.preset, args.method, args.basis)
        result = frequency_analysis(config, args.xyz, profile, args.charge, args.mult, args.nprocs, args.memory)
    elif args.task == "single-point":
        engine = resolve_engine("single_point", args.engine)
        if maybe_print_presets("single_point", engine, args.list_presets):
            return
        profile = resolve_template_profile("single_point", engine, args.preset, args.method, args.basis)
        result = single_point_energy(config, args.xyz, profile, args.charge, args.mult, args.nprocs, args.memory)
    elif args.task == "uvvis":
        engine = resolve_engine("uvvis", args.engine)
        if maybe_print_presets("uvvis", engine, args.list_presets):
            return
        profile = resolve_template_profile("uvvis", engine, args.preset, args.method, args.basis)
        result = electronic_spectrum_workflow(
            config=config,
            xyz_path=args.xyz,
            profile=profile,
            charge=args.charge,
            mult=args.mult,
            nprocs=args.nprocs,
            memory=args.memory,
            task_name="uvvis",
            nstates=args.nstates,
            solvent=args.solvent,
            solvent_model=args.solvent_model,
            use_tda=args.tda,
            include_triplets=args.triplets,
            do_nto=args.nto,
            simplified_mode=args.simplified_mode,
        )
    elif args.task == "ecd":
        engine = resolve_engine("ecd", args.engine)
        if maybe_print_presets("ecd", engine, args.list_presets):
            return
        profile = resolve_template_profile("ecd", engine, args.preset, args.method, args.basis)
        result = electronic_spectrum_workflow(
            config=config,
            xyz_path=args.xyz,
            profile=profile,
            charge=args.charge,
            mult=args.mult,
            nprocs=args.nprocs,
            memory=args.memory,
            task_name="ecd",
            nstates=args.nstates,
            solvent=args.solvent,
            solvent_model=args.solvent_model,
            use_tda=args.tda,
            include_triplets=args.triplets,
            do_nto=args.nto,
            simplified_mode=args.simplified_mode,
        )
    elif args.task == "nmr":
        engine = resolve_engine("nmr", args.engine)
        if maybe_print_presets("nmr", engine, args.list_presets):
            return
        profile = resolve_template_profile("nmr", engine, args.preset, args.method, args.basis)
        result = nmr_workflow(
            config=config,
            xyz_path=args.xyz,
            profile=profile,
            charge=args.charge,
            mult=args.mult,
            nprocs=args.nprocs,
            memory=args.memory,
            solvent=args.solvent,
            solvent_model=args.solvent_model,
            gauge=args.gauge,
            include_spinspin=args.spin_spin,
            spinspin_elements=tuple(args.spin_spin_elements or ()),
            spinspin_rthresh=args.spin_spin_rthresh,
            print_reduced_coupling=args.reduced_coupling,
        )
    elif args.task == "raman":
        engine = resolve_engine("raman", args.engine)
        if maybe_print_presets("raman", engine, args.list_presets):
            return
        profile = resolve_template_profile("raman", engine, args.preset, args.method, args.basis)
        result = raman_workflow(
            config=config,
            xyz_path=args.xyz,
            profile=profile,
            charge=args.charge,
            mult=args.mult,
            nprocs=args.nprocs,
            memory=args.memory,
            solvent=args.solvent,
            solvent_model=args.solvent_model,
        )
    elif args.task == "ir":
        engine = resolve_engine("ir", args.engine)
        if maybe_print_presets("ir", engine, args.list_presets):
            return
        profile = resolve_template_profile("ir", engine, args.preset, args.method, args.basis)
        result = ir_workflow(
            config=config,
            xyz_path=args.xyz,
            profile=profile,
            charge=args.charge,
            mult=args.mult,
            nprocs=args.nprocs,
            memory=args.memory,
            solvent=args.solvent,
            solvent_model=args.solvent_model,
        )
    elif args.task == "vcd":
        engine = resolve_engine("vcd", args.engine)
        if maybe_print_presets("vcd", engine, args.list_presets):
            return
        profile = resolve_template_profile("vcd", engine, args.preset, args.method, args.basis)
        result = vcd_workflow(
            config=config,
            xyz_path=args.xyz,
            profile=profile,
            charge=args.charge,
            mult=args.mult,
            nprocs=args.nprocs,
            memory=args.memory,
            solvent=args.solvent,
            solvent_model=args.solvent_model,
        )
    elif args.task == "nearir":
        engine = resolve_engine("nearir", args.engine)
        if maybe_print_presets("nearir", engine, args.list_presets):
            return
        profile = resolve_template_profile("nearir", engine, args.preset, args.method, args.basis)
        result = nearir_workflow(
            config=config,
            xyz_path=args.xyz,
            profile=profile,
            charge=args.charge,
            mult=args.mult,
            nprocs=args.nprocs,
            memory=args.memory,
            solvent=args.solvent,
            solvent_model=args.solvent_model,
            use_xtb_vpt2=not args.no_xtb_vpt2,
            delq=args.delq,
        )
    elif args.task == "batch-sp":
        engine = resolve_engine("single_point", args.engine)
        if maybe_print_presets("single_point", engine, args.list_presets):
            return
        profile = resolve_template_profile("single_point", engine, args.preset, args.method, args.basis)
        xyz_inputs = sorted(args.xyz_dir.glob("*.xyz"))
        if not xyz_inputs:
            raise SystemExit(f"未在目录中找到 xyz 文件: {args.xyz_dir}")
        results, csv_file, json_file = batch_single_point_workflow(
            config=config,
            xyz_inputs=xyz_inputs,
            profile=profile,
            charge=args.charge,
            mult=args.mult,
            workers=args.workers,
            nprocs_per_job=args.nprocs_per_job,
            memory=args.memory,
        )
        print_results(results)
        print(json.dumps({"summary_csv": str(csv_file), "summary_json": str(json_file)}, ensure_ascii=False, indent=2))
        return
    elif args.task == "batch-opt":
        engine = resolve_engine("optimize", args.engine)
        if maybe_print_presets("optimize", engine, args.list_presets):
            return
        profile = resolve_template_profile("optimize", engine, args.preset, args.method, args.basis)
        xyz_inputs = sorted(args.xyz_dir.glob("*.xyz"))
        if not xyz_inputs:
            raise SystemExit(f"未在目录中找到 xyz 文件: {args.xyz_dir}")
        results, csv_file, json_file = batch_optimize_workflow(
            config=config,
            xyz_inputs=xyz_inputs,
            profile=profile,
            charge=args.charge,
            mult=args.mult,
            workers=args.workers,
            nprocs_per_job=args.nprocs_per_job,
            memory=args.memory,
        )
        print_results(results)
        print(json.dumps({"summary_csv": str(csv_file), "summary_json": str(json_file)}, ensure_ascii=False, indent=2))
        return
    elif args.task == "ts-retry":
        engine = resolve_engine("ts_retry", args.engine)
        if maybe_print_presets("ts_retry", engine, args.list_presets):
            return
        profile = resolve_template_profile("ts_retry", engine, args.preset, args.method, args.basis)
        result = ts_retry_workflow(config, args.xyz, profile, args.charge, args.mult, args.nprocs, args.memory)
    elif args.task == "scan":
        expected_atoms = {"B": 2, "A": 3, "D": 4}[args.scan_type]
        if len(args.atoms) != expected_atoms:
            raise SystemExit(f"{args.scan_type} 扫描需要 {expected_atoms} 个原子编号")
        engine = resolve_engine("scan", args.engine)
        if maybe_print_presets("scan", engine, args.list_presets):
            return
        profile = resolve_template_profile("scan", engine, args.preset, args.method, args.basis)
        result = scan_workflow(
            config=config,
            xyz_path=args.xyz,
            profile=profile,
            charge=args.charge,
            mult=args.mult,
            nprocs=args.nprocs,
            memory=args.memory,
            scan_type=args.scan_type,
            atom_indices=tuple(args.atoms),
            start=args.start,
            stop=args.stop,
            steps=args.steps,
        )
        print_result(result)
        if not result.dry_run:
            profile_data = build_scan_profile(extract_energy_series("orca", result.stdout_file, result.stderr_file))
            if profile_data:
                results_dir = result.work_dir / "results"
                csv_file = results_dir / "scan_profile.csv"
                json_file = results_dir / "scan_profile.json"
                lowest_file = results_dir / "scan_lowest.json"
                write_scan_profile_csv(csv_file, profile_data)
                write_scan_profile_json(json_file, profile_data)
                lowest = min(profile_data, key=lambda item: float(item["energy_hartree"]))
                lowest_file.write_text(json.dumps(lowest, ensure_ascii=False, indent=2), encoding="utf-8")
        return
    elif args.task == "irc":
        engine = resolve_engine("irc", args.engine)
        if maybe_print_presets("irc", engine, args.list_presets):
            return
        profile = resolve_template_profile("irc", engine, args.preset, args.method, args.basis)
        if args.direction == "both":
            results, csv_file, json_file = irc_pair_workflow(
                config=config,
                xyz_path=args.xyz,
                profile=profile,
                charge=args.charge,
                mult=args.mult,
                nprocs=args.nprocs,
                memory=args.memory,
                max_points=args.max_points,
                step_size=args.step_size,
            )
            print_results(results)
            print(json.dumps({"summary_csv": str(csv_file), "summary_json": str(json_file)}, ensure_ascii=False, indent=2))
            return
        result = irc_workflow(
            config=config,
            xyz_path=args.xyz,
            profile=profile,
            charge=args.charge,
            mult=args.mult,
            nprocs=args.nprocs,
            memory=args.memory,
            direction=args.direction,
            max_points=args.max_points,
            step_size=args.step_size,
        )
    elif args.task == "neb":
        engine = resolve_engine("neb", args.engine)
        if maybe_print_presets("neb", engine, args.list_presets):
            return
        profile = resolve_template_profile("neb", engine, args.preset, args.method, args.basis)
        result = neb_workflow(
            config=config,
            reactant_xyz=args.xyz,
            product_xyz=args.product_xyz,
            profile=profile,
            charge=args.charge,
            mult=args.mult,
            nprocs=args.nprocs,
            memory=args.memory,
            images=args.images,
            preopt=args.preopt,
        )
    elif args.task == "crest":
        if maybe_print_presets("crest", "crest", args.list_presets):
            return
        profile = resolve_template_profile("crest", "crest", args.preset, args.method, None)
        result = crest_search_workflow(
            config=config,
            xyz_path=args.xyz,
            profile=profile,
            charge=args.charge,
            mult=args.mult,
            nprocs=args.nprocs,
            keepdir=args.keepdir,
        )
    else:
        raise ValueError(f"未知任务: {args.task}")

    print_result(result)


if __name__ == "__main__":
    main()