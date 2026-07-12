import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from qm_automation.cli_shared import maybe_print_presets, resolve_template_profile
from qm_automation.config import load_config
from qm_automation.workflows import conformer_screen_workflow


def main() -> None:
    parser = argparse.ArgumentParser(description="Conformer screening workflow")
    parser.add_argument("xyz_dir", type=Path, help="包含多个 xyz 文件的目录")
    parser.add_argument("--charge", type=int, default=0)
    parser.add_argument("--mult", type=int, default=1)
    parser.add_argument("--xtb-preset", default="default", help="xTB 预筛模板")
    parser.add_argument("--orca-preset", default="cheap", help="ORCA 精修模板")
    parser.add_argument("--xtb-method", default=None, help="覆盖 xTB 模板中的方法号")
    parser.add_argument("--orca-method", default=None, help="覆盖 ORCA 模板中的方法")
    parser.add_argument("--orca-basis", default=None, help="覆盖 ORCA 模板中的基组")
    parser.add_argument("--list-presets", action="store_true", help="列出构象筛选相关模板后退出")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--nprocs-per-job", type=int, default=4)
    parser.add_argument("--memory", type=int, default=2048)
    parser.add_argument("--runs-root", type=Path, default=None, help="运行目录根路径，默认是当前目录下的 runs")
    parser.add_argument("--config-file", type=Path, default=None, help="JSON 配置文件路径，可统一写软件路径和 runs_root")
    parser.add_argument("--orca-cmd", default=None, help="直接指定 ORCA 可执行程序或启动脚本路径")
    parser.add_argument("--gaussian-cmd", default=None, help="直接指定 Gaussian 可执行程序或启动脚本路径")
    parser.add_argument("--xtb-cmd", default=None, help="直接指定 xTB 可执行程序路径")
    parser.add_argument("--crest-cmd", default=None, help="直接指定 CREST 可执行程序路径")
    parser.add_argument("--dry-run", action="store_true", help="只生成输入和命令文件，不真正提交计算")
    args = parser.parse_args()

    if args.list_presets:
        shown_xtb = maybe_print_presets("optimize", "xtb", True)
        shown_orca = maybe_print_presets("optimize", "orca", True)
        if shown_xtb or shown_orca:
            return

    xtb_profile = resolve_template_profile("optimize", "xtb", args.xtb_preset, args.xtb_method, None)
    orca_profile = resolve_template_profile("optimize", "orca", args.orca_preset, args.orca_method, args.orca_basis)

    xyz_inputs = sorted(args.xyz_dir.glob("*.xyz"))
    results = conformer_screen_workflow(
        config=load_config(
            runs_root=args.runs_root,
            orca_cmd=args.orca_cmd,
            gaussian_cmd=args.gaussian_cmd,
            xtb_cmd=args.xtb_cmd,
            crest_cmd=args.crest_cmd,
            dry_run=args.dry_run,
            config_file=args.config_file,
        ),
        xyz_inputs=xyz_inputs,
        charge=args.charge,
        mult=args.mult,
        xtb_method=xtb_profile.method,
        orca_method=orca_profile.method,
        orca_basis=orca_profile.basis,
        workers=args.workers,
        nprocs_per_job=args.nprocs_per_job,
        memory=args.memory,
    )
    for result in results:
        print(result.message, result.work_dir)


if __name__ == "__main__":
    main()