import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from qm_automation.reporting import (
    collect_run_metadata,
    compute_run_statistics,
    select_lowest_energy,
    write_metadata_summary_csv,
    write_metadata_summary_json,
    write_statistics_json,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize existing run metadata")
    parser.add_argument("runs_root", type=Path, nargs="?", default=Path("runs"), help="runs 根目录")
    parser.add_argument("--output", type=Path, default=None, help="输出 CSV 路径")
    parser.add_argument("--json-output", type=Path, default=None, help="输出 JSON 路径")
    parser.add_argument("--stats-output", type=Path, default=None, help="输出统计 JSON 路径")
    parser.add_argument("--top", type=int, default=5, help="终端显示最低能前 N 条")
    args = parser.parse_args()

    records = collect_run_metadata(args.runs_root)
    output_file = args.output or (args.runs_root / "runs_summary.csv")
    json_output_file = args.json_output or (args.runs_root / "runs_summary.json")
    stats_output_file = args.stats_output or (args.runs_root / "runs_stats.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    write_metadata_summary_csv(output_file, records)
    write_metadata_summary_json(json_output_file, records)
    stats = compute_run_statistics(records)
    write_statistics_json(stats_output_file, stats)

    success_count = sum(1 for item in records if item.get("success"))
    print(f"runs={len(records)}")
    print(f"success={success_count}")
    print(f"csv={output_file}")
    print(f"json={json_output_file}")
    print(f"stats={stats_output_file}")

    lowest_records = select_lowest_energy(records, args.top)
    for index, record in enumerate(lowest_records, start=1):
        print(
            f"top_{index}={record.get('energy_hartree')} | {record.get('task_name')} | {record.get('engine')} | {record.get('work_dir')}"
        )


if __name__ == "__main__":
    main()