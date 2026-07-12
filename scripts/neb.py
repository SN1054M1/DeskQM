import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from qm_automation.cli_shared import add_common_arguments, maybe_print_presets, print_result, resolve_engine, resolve_template_profile
from qm_automation.config import load_config
from qm_automation.workflows import neb_workflow


def main() -> None:
    parser = argparse.ArgumentParser(description="NEB workflow")
    add_common_arguments(parser, task_name="neb", engine_choices=("auto", "orca"))
    parser.add_argument("--product-xyz", type=Path, required=True, help="产物端点 xyz 文件")
    parser.add_argument("--images", type=int, default=8, help="NEB 图像数")
    parser.add_argument("--preopt", action="store_true", help="启用 ORCA 的端点预优化")
    args = parser.parse_args()

    engine = resolve_engine("neb", args.engine)
    if maybe_print_presets("neb", engine, args.list_presets):
        return
    profile = resolve_template_profile("neb", engine, args.preset, args.method, args.basis)
    config = load_config(
        runs_root=args.runs_root,
        orca_cmd=args.orca_cmd,
        gaussian_cmd=args.gaussian_cmd,
        xtb_cmd=args.xtb_cmd,
        crest_cmd=args.crest_cmd,
        dry_run=args.dry_run,
        config_file=args.config_file,
    )
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
    print_result(result)


if __name__ == "__main__":
    main()