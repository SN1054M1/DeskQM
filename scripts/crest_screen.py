import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from qm_automation.config import load_config
from qm_automation.presets import format_preset_help, resolve_profile
from qm_automation.workflows import crest_search_workflow
from qm_automation.cli_shared import print_result


def main() -> None:
    parser = argparse.ArgumentParser(description="CREST conformer search workflow")
    parser.add_argument("xyz", type=Path, help="输入 xyz 文件路径")
    parser.add_argument("--preset", default="default")
    parser.add_argument("--list-presets", action="store_true")
    parser.add_argument("--charge", type=int, default=0)
    parser.add_argument("--mult", type=int, default=1)
    parser.add_argument("--method", default=None, help="默认是 gfn2，可覆盖为 gfn1 等")
    parser.add_argument("--nprocs", type=int, default=8)
    parser.add_argument("--keepdir", action="store_true", help="保留 CREST 目录中的中间文件")
    parser.add_argument("--runs-root", type=Path, default=None)
    parser.add_argument("--config-file", type=Path, default=None)
    parser.add_argument("--orca-cmd", default=None)
    parser.add_argument("--gaussian-cmd", default=None)
    parser.add_argument("--xtb-cmd", default=None)
    parser.add_argument("--crest-cmd", default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.list_presets:
        print(format_preset_help("crest", "crest"))
        return
    profile = resolve_profile("crest", "crest", args.preset, args.method, None)
    config = load_config(
        runs_root=args.runs_root,
        orca_cmd=args.orca_cmd,
        gaussian_cmd=args.gaussian_cmd,
        xtb_cmd=args.xtb_cmd,
        crest_cmd=args.crest_cmd,
        dry_run=args.dry_run,
        config_file=args.config_file,
    )
    result = crest_search_workflow(
        config=config,
        xyz_path=args.xyz,
        profile=profile,
        charge=args.charge,
        mult=args.mult,
        nprocs=args.nprocs,
        keepdir=args.keepdir,
    )
    print_result(result)


if __name__ == "__main__":
    main()