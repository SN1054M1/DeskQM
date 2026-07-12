import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from qm_automation.reporting import collect_run_metadata, compute_run_statistics, select_lowest_energy


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect local workstation runs")
    parser.add_argument("runs_root", type=Path, nargs="?", default=Path("runs"), help="runs 根目录")
    parser.add_argument("--latest", type=int, default=10, help="显示最近若干条记录")
    parser.add_argument("--failed", type=int, default=10, help="显示最近失败若干条记录")
    parser.add_argument("--lowest", type=int, default=10, help="显示最低能若干条记录")
    args = parser.parse_args()

    records = collect_run_metadata(args.runs_root)
    stats = compute_run_statistics(records)
    print(f"total_runs={stats['total_runs']}")
    print(f"success_runs={stats['success_runs']}")
    print(f"failed_runs={stats['failed_runs']}")
    print(f"dry_runs={stats['dry_runs']}")

    latest_records = list(reversed(records[-args.latest :]))
    for index, record in enumerate(latest_records, start=1):
        print(f"latest_{index}={record.get('task_name')} | {record.get('engine')} | {record.get('success')} | {record.get('work_dir')}")

    failed_records = [record for record in reversed(records) if not bool(record.get("success"))][: args.failed]
    for index, record in enumerate(failed_records, start=1):
        print(f"failed_{index}={record.get('task_name')} | {record.get('engine')} | {record.get('message')} | {record.get('work_dir')}")

    lowest_records = select_lowest_energy(records, args.lowest)
    for index, record in enumerate(lowest_records, start=1):
        print(f"lowest_{index}={record.get('energy_hartree')} | {record.get('task_name')} | {record.get('engine')} | {record.get('work_dir')}")


if __name__ == "__main__":
    main()