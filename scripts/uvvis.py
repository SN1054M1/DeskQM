import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import argparse

from qm_automation.cli_shared import add_common_arguments, maybe_print_presets, print_result, resolve_engine, resolve_template_profile
from qm_automation.config import load_config
from qm_automation.workflows import electronic_spectrum_workflow


def main() -> None:
    parser = argparse.ArgumentParser(description="UV/Vis workflow")
    add_common_arguments(parser, task_name="uvvis")
    parser.add_argument("--solvent", default=None, help="隐式溶剂名，例如 water、acetonitrile、chloroform")
    parser.add_argument("--solvent-model", choices=["auto", "cpcm", "pcm", "smd"], default="auto")
    parser.add_argument("--nstates", type=int, default=20, help="请求的激发态数")
    parser.add_argument("--tda", action="store_true", help="显式启用 TDA")
    parser.add_argument("--triplets", action="store_true", help="同时请求 triplet roots")
    parser.add_argument("--nto", action="store_true", help="为 ORCA 打开 NTO 分析")
    parser.add_argument("--simplified-mode", choices=["off", "stda", "stddft"], default="off")
    args = parser.parse_args()
    engine = resolve_engine("uvvis", args.engine)
    if maybe_print_presets("uvvis", engine, args.list_presets):
        return
    profile = resolve_template_profile("uvvis", engine, args.preset, args.method, args.basis)
    config = load_config(
        runs_root=args.runs_root,
        orca_cmd=args.orca_cmd,
        gaussian_cmd=args.gaussian_cmd,
        xtb_cmd=args.xtb_cmd,
        crest_cmd=args.crest_cmd,
        dry_run=args.dry_run,
        config_file=args.config_file,
    )
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
    print_result(result)


if __name__ == "__main__":
    main()