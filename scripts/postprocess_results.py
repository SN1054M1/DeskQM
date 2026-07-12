import json
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from qm_automation.reporting import (
    compute_run_statistics,
    load_summary_json,
    select_lowest_energy,
    sort_records_by_energy,
    write_generic_records_csv,
    write_statistics_json,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Postprocess summary JSON files")
    parser.add_argument("summary_json", type=Path, help="输入 summary JSON，例如 batch_summary.json 或 runs_summary.json")
    parser.add_argument("--top", type=int, default=10, help="保留最低能前 N 条")
    parser.add_argument("--output-csv", type=Path, default=None, help="输出排序后 CSV")
    parser.add_argument("--output-json", type=Path, default=None, help="输出排序后 JSON")
    parser.add_argument("--stats-output", type=Path, default=None, help="输出统计 JSON")
    parser.add_argument("--include-failed", action="store_true", help="允许失败任务保留在排序前的集合中")
    parser.add_argument("--include-dry-run", action="store_true", help="允许 dry-run 记录进入排序前集合")
    args = parser.parse_args()

    records = load_summary_json(args.summary_json)
    ordered = sort_records_by_energy(
        records,
        success_only=not args.include_failed,
        exclude_dry_run=not args.include_dry_run,
    )
    lowest = ordered[: args.top]

    output_csv = args.output_csv or args.summary_json.with_name(args.summary_json.stem + ".lowest.csv")
    output_json = args.output_json or args.summary_json.with_name(args.summary_json.stem + ".lowest.json")
    stats_output = args.stats_output or args.summary_json.with_name(args.summary_json.stem + ".stats.json")

    write_generic_records_csv(output_csv, lowest)
    output_json.write_text(json.dumps(lowest, ensure_ascii=False, indent=2), encoding="utf-8")
    write_statistics_json(stats_output, compute_run_statistics(records))

    print(f"input={args.summary_json}")
    print(f"selected={len(lowest)}")
    print(f"csv={output_csv}")
    print(f"json={output_json}")
    print(f"stats={stats_output}")
    for index, record in enumerate(lowest, start=1):
        print(f"top_{index}={record.get('energy_hartree')} | {record.get('task_name')} | {record.get('engine')} | {record.get('work_dir')}")


if __name__ == "__main__":
    main()