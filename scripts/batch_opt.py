import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from qm_automation.cli_shared import maybe_print_presets, resolve_engine, resolve_template_profile
from qm_automation.config import load_config
from qm_automation.workflows import batch_optimize_workflow


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch optimization workflow")
    parser.add_argument("xyz_dir", type=Path, help="包含多个 xyz 文件的目录")
    parser.add_argument("--engine", choices=["auto", "orca", "gaussian", "xtb"], default="auto")
    parser.add_argument("--preset", default="default")
    parser.add_argument("--list-presets", action="store_true")
    parser.add_argument("--charge", type=int, default=0)
    parser.add_argument("--mult", type=int, default=1)
    parser.add_argument("--method", default=None)
    parser.add_argument("--basis", default=None)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--nprocs-per-job", type=int, default=4)
    parser.add_argument("--memory", type=int, default=2048)
    parser.add_argument("--runs-root", type=Path, default=None)
    parser.add_argument("--config-file", type=Path, default=None)
    parser.add_argument("--orca-cmd", default=None)
    parser.add_argument("--gaussian-cmd", default=None)
    parser.add_argument("--xtb-cmd", default=None)
    parser.add_argument("--crest-cmd", default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    engine = resolve_engine("optimize", args.engine)
    if maybe_print_presets("optimize", engine, args.list_presets):
        return
    profile = resolve_template_profile("optimize", engine, args.preset, args.method, args.basis)
    config = load_config(
        runs_root=args.runs_root,
        orca_cmd=args.orca_cmd,
        gaussian_cmd=args.gaussian_cmd,
        xtb_cmd=args.xtb_cmd,
        crest_cmd=args.crest_cmd,
        dry_run=args.dry_run,
        config_file=args.config_file,
    )
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
    print(f"completed={len(results)}")
    print(f"summary_csv={csv_file}")
    print(f"summary_json={json_file}")


if __name__ == "__main__":
    main()