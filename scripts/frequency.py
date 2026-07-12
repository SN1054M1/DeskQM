import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import argparse

from qm_automation.cli_shared import add_common_arguments, maybe_print_presets, print_result, resolve_engine, resolve_template_profile
from qm_automation.config import load_config
from qm_automation.workflows import frequency_analysis


def main() -> None:
    parser = argparse.ArgumentParser(description="Frequency workflow")
    add_common_arguments(parser, task_name="frequency")
    args = parser.parse_args()
    engine = resolve_engine("frequency", args.engine)
    if maybe_print_presets("frequency", engine, args.list_presets):
        return
    profile = resolve_template_profile("frequency", engine, args.preset, args.method, args.basis)
    config = load_config(
        runs_root=args.runs_root,
        orca_cmd=args.orca_cmd,
        gaussian_cmd=args.gaussian_cmd,
        xtb_cmd=args.xtb_cmd,
        crest_cmd=args.crest_cmd,
        dry_run=args.dry_run,
        config_file=args.config_file,
    )
    result = frequency_analysis(config, args.xyz, profile, args.charge, args.mult, args.nprocs, args.memory)
    print_result(result)


if __name__ == "__main__":
    main()