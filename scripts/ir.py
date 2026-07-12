import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import argparse

from qm_automation.cli_shared import add_common_arguments, maybe_print_presets, print_result, resolve_engine, resolve_template_profile
from qm_automation.config import load_config
from qm_automation.workflows import ir_workflow


def main() -> None:
    parser = argparse.ArgumentParser(description="IR workflow")
    add_common_arguments(parser, task_name="ir")
    parser.add_argument("--solvent", default=None, help="隐式溶剂名，例如 water、acetonitrile、chloroform")
    parser.add_argument("--solvent-model", choices=["auto", "cpcm", "pcm", "smd"], default="auto")
    args = parser.parse_args()
    engine = resolve_engine("ir", args.engine)
    if maybe_print_presets("ir", engine, args.list_presets):
        return
    profile = resolve_template_profile("ir", engine, args.preset, args.method, args.basis)
    config = load_config(
        runs_root=args.runs_root,
        orca_cmd=args.orca_cmd,
        gaussian_cmd=args.gaussian_cmd,
        xtb_cmd=args.xtb_cmd,
        crest_cmd=args.crest_cmd,
        dry_run=args.dry_run,
        config_file=args.config_file,
    )
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
    print_result(result)


if __name__ == "__main__":
    main()