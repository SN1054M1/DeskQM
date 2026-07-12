import argparse
import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from qm_automation.cli_shared import add_common_arguments, maybe_print_presets, print_result, resolve_engine, resolve_template_profile
from qm_automation.config import load_config
from qm_automation.parsing import extract_energy_series
from qm_automation.reporting import build_scan_profile, write_scan_profile_csv, write_scan_profile_json
from qm_automation.workflows import scan_workflow


def main() -> None:
    parser = argparse.ArgumentParser(description="Potential energy scan workflow")
    add_common_arguments(parser, task_name="scan", engine_choices=("auto", "orca"))
    parser.add_argument("--scan-type", choices=["B", "A", "D"], required=True, help="B=键长, A=键角, D=二面角")
    parser.add_argument("--atoms", type=int, nargs="+", required=True, help="参与扫描的原子编号，从 1 开始")
    parser.add_argument("--start", type=float, required=True, help="起始值，键长用 Å，角度用度")
    parser.add_argument("--stop", type=float, required=True, help="终止值，键长用 Å，角度用度")
    parser.add_argument("--steps", type=int, required=True, help="扫描步数")
    args = parser.parse_args()

    expected_atoms = {"B": 2, "A": 3, "D": 4}[args.scan_type]
    if len(args.atoms) != expected_atoms:
        raise SystemExit(f"{args.scan_type} 扫描需要 {expected_atoms} 个原子编号")

    engine = resolve_engine("scan", args.engine)
    if maybe_print_presets("scan", engine, args.list_presets):
        return
    profile = resolve_template_profile("scan", engine, args.preset, args.method, args.basis)
    config = load_config(
        runs_root=args.runs_root,
        orca_cmd=args.orca_cmd,
        gaussian_cmd=args.gaussian_cmd,
        xtb_cmd=args.xtb_cmd,
        crest_cmd=args.crest_cmd,
        dry_run=args.dry_run,
        config_file=args.config_file,
    )
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


if __name__ == "__main__":
    main()