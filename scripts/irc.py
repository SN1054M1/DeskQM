import argparse
import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from qm_automation.cli_shared import add_common_arguments, maybe_print_presets, print_result, print_results, resolve_engine, resolve_template_profile
from qm_automation.config import load_config
from qm_automation.workflows import irc_pair_workflow, irc_workflow


def main() -> None:
    parser = argparse.ArgumentParser(description="IRC workflow")
    add_common_arguments(parser, task_name="irc", engine_choices=("auto", "orca"))
    parser.add_argument("--direction", choices=["forward", "backward", "both"], default="both", help="IRC 路径方向")
    parser.add_argument("--max-points", type=int, default=30, help="IRC 最大步数")
    parser.add_argument("--step-size", type=float, default=0.15, help="IRC 初始步长缩放")
    args = parser.parse_args()

    engine = resolve_engine("irc", args.engine)
    if maybe_print_presets("irc", engine, args.list_presets):
        return
    profile = resolve_template_profile("irc", engine, args.preset, args.method, args.basis)
    config = load_config(
        runs_root=args.runs_root,
        orca_cmd=args.orca_cmd,
        gaussian_cmd=args.gaussian_cmd,
        xtb_cmd=args.xtb_cmd,
        crest_cmd=args.crest_cmd,
        dry_run=args.dry_run,
        config_file=args.config_file,
    )
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
    print_result(result)


if __name__ == "__main__":
    main()