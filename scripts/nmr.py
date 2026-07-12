import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import argparse

from qm_automation.cli_shared import add_common_arguments, maybe_print_presets, print_result, resolve_engine, resolve_template_profile
from qm_automation.config import load_config
from qm_automation.workflows import nmr_workflow


def main() -> None:
    parser = argparse.ArgumentParser(description="NMR workflow")
    add_common_arguments(parser, task_name="nmr")
    parser.add_argument("--solvent", default=None, help="隐式溶剂名，例如 water、acetonitrile、chloroform")
    parser.add_argument("--solvent-model", choices=["auto", "cpcm", "pcm", "smd"], default="auto")
    parser.add_argument("--gauge", choices=["giao", "csgt"], default="giao")
    parser.add_argument("--spin-spin", action="store_true", help="同时计算自旋-自旋耦合")
    parser.add_argument("--spin-spin-elements", nargs="+", default=None, help="限制自旋-自旋耦合涉及的元素，例如 C H O")
    parser.add_argument("--spin-spin-rthresh", type=float, default=5.0, help="ORCA 自旋-自旋耦合距离阈值，单位 Å")
    parser.add_argument("--reduced-coupling", action="store_true", help="ORCA 额外输出 reduced coupling 常数")
    args = parser.parse_args()
    engine = resolve_engine("nmr", args.engine)
    if maybe_print_presets("nmr", engine, args.list_presets):
        return
    profile = resolve_template_profile("nmr", engine, args.preset, args.method, args.basis)
    config = load_config(
        runs_root=args.runs_root,
        orca_cmd=args.orca_cmd,
        gaussian_cmd=args.gaussian_cmd,
        xtb_cmd=args.xtb_cmd,
        crest_cmd=args.crest_cmd,
        dry_run=args.dry_run,
        config_file=args.config_file,
    )
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
    print_result(result)


if __name__ == "__main__":
    main()