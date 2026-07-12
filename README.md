# QM Automation

面向命令行的量化计算自动化脚本集合。不是固定以某一个程序为主，而是按任务优先调用更擅长的软件，并把原始输入文件和原始命令单独保存出来，尽量保持传统量化命令行工作流的感觉。

## 目标

- 输入通常为 xyz 文件。
- 每次任务自动建立独立工作目录。
- 中间文件按子目录分层保存，便于事后排查。
- 对常见重复试错场景提供自动重试、参数降级与并行调度。
- 不同任务使用不同脚本，统一放在 scripts 目录下。

## 一句话理解

这个项目不是新的量化程序，而是一个命令行“调度层”：

- 你提供 xyz 结构。
- 它帮你生成 ORCA / Gaussian / xTB / CREST 的原生输入和命令。
- 它帮你建立独立工作目录、保存日志、保存复跑脚本、做少量自动重试与汇总。
- 真正干活的仍然是 ORCA、Gaussian、xTB、CREST 本体。

如果你只想快速抓住重点，可以先记住下面 4 句话：

1. 单个结构优化通常先用 `optimize.py`。
2. 批量结构就用 `batch_opt.py` 或 `batch_sp.py`。
3. 构象预筛可用 `crest_screen.py` 或 `conformer_screen.py`。
4. 第一次先加 `--dry-run`，确认路径和输入文件没问题再真跑。

## 3 分钟上手

如果你只想尽快跑起来，不想先看完整文档，可以直接照这个顺序做。

### 第一步：准备一个配置文件

在项目根目录新建 `qm_auto_config.json`：

```json
{
  "runs_root": "D:/qm_runs",
  "orca_cmd": "D:/orca_6_0_1/orca.exe",
  "gaussian_cmd": "C:/Gaussian16/g16.exe",
  "xtb_cmd": "D:/xtb/xtb.exe",
  "crest_cmd": "D:/crest/crest.exe"
}
```

如果你暂时只装了 ORCA，就只保留 `orca_cmd` 也可以。

### 第二步：先试一次 dry-run

```powershell
python scripts\optimize.py .\molecule.xyz --config-file .\qm_auto_config.json --dry-run
```

如果这一步没报错，说明：

- Python 能正常运行脚本
- xyz 文件格式基本没问题
- 软件路径至少写对了
- 输入文件和命令文件已经成功生成

### 第三步：正式跑一个最简单任务

```powershell
python scripts\optimize.py .\molecule.xyz --config-file .\qm_auto_config.json
```

### 第四步：查看结果

```powershell
python scripts\inspect_runs.py .\runs
```

如果你只记 3 条最常用命令，通常就是这三条：

```powershell
python scripts\optimize.py .\molecule.xyz --config-file .\qm_auto_config.json --dry-run
python scripts\optimize.py .\molecule.xyz --config-file .\qm_auto_config.json
python scripts\inspect_runs.py .\runs
```

### 常见场景直接照抄

单个结构优化：

```powershell
python scripts\optimize.py .\molecule.xyz --config-file .\qm_auto_config.json
```

单个结构频率：

```powershell
python scripts\frequency.py .\molecule.xyz --config-file .\qm_auto_config.json
```

单个结构单点能：

```powershell
python scripts\single_point.py .\molecule.xyz --config-file .\qm_auto_config.json
```

一批 xyz 批量优化：

```powershell
python scripts\batch_opt.py .\ensemble\ --config-file .\qm_auto_config.json --engine xtb --workers 8 --nprocs-per-job 2
```

一批 xyz 批量单点：

```powershell
python scripts\batch_sp.py .\ensemble\ --config-file .\qm_auto_config.json --engine orca --workers 6 --nprocs-per-job 2
```

先做 CREST 构象搜索：

```powershell
python scripts\crest_screen.py .\molecule.xyz --config-file .\qm_auto_config.json --nprocs 8
```

### 看不懂一堆脚本时，先这样选

- 只想优化一个结构：`optimize.py`
- 只想算一个结构能量：`single_point.py`
- 只想算频率：`frequency.py`
- 想看电子吸收或 ECD：`uvvis.py` 或 `ecd.py`
- 想看 NMR：`nmr.py`
- 想看振动光谱：`ir.py`、`raman.py`、`vcd.py`、`nearir.py`
- 有很多 xyz 一起跑：`batch_opt.py` 或 `batch_sp.py`
- 想先做构象筛选：`crest_screen.py` 或 `conformer_screen.py`
- 想看最近哪些任务成功/失败：`inspect_runs.py`

### 第一次使用时最容易踩的坑

- 没写 `--config-file`，结果脚本去找默认命令名，报找不到软件
- 第一次就直接真跑，没有先 `--dry-run`
- `xyz` 第一行原子数不对，第二行不是注释行
- 软件路径里有空格，但命令行没加引号
- 把 ORCA、Gaussian、xTB、CREST 当成 Python 包来理解，其实它们都是外部程序

## 通俗上手指南

下面按“第一次用”的思路来写，不假定你已经熟悉项目内部结构。

### 1. 你需要先准备什么

- 一个 xyz 文件，例如 `molecule.xyz`
- 至少装好一种量化软件：ORCA、Gaussian、xTB、CREST 里的任意一种
- Python 3.11+

如果你目前最常用的是：

- 几何优化：优先从 ORCA 或 xTB 开始
- 频率：优先从 Gaussian 或 ORCA 开始
- 构象搜索：优先从 CREST 或 xTB 开始

### 2. 最推荐的路径指定方式

如果你不希望脚本修改当前环境变量，就不要先执行 `$env:ORCA_CMD=...` 或 `export ORCA_CMD=...`。

最推荐的是准备一个 JSON 配置文件，例如：

```json
{
  "runs_root": "D:/qm_runs",
  "orca_cmd": "D:/orca_6_0_1/orca.exe",
  "gaussian_cmd": "C:/Gaussian16/g16.exe",
  "xtb_cmd": "D:/xtb/xtb.exe",
  "crest_cmd": "D:/crest/crest.exe"
}
```

然后统一这样调用：

```powershell
python scripts\optimize.py .\molecule.xyz --config-file .\qm_auto_config.json
```

这样做的好处是：

- 不改系统 PATH
- 不依赖当前终端环境变量
- 以后所有脚本共用一套路径配置
- Windows 和 Linux 可以各放一份配置文件

### 3. 第一次跑，先 dry-run

第一次不要急着真跑，先只生成输入和命令文件：

```powershell
python scripts\optimize.py .\molecule.xyz --config-file .\qm_auto_config.json --dry-run
```

看什么：

- 命令有没有报“找不到软件”
- `commands/` 里生成的命令是不是你想要的
- `inputs/` 里的原始输入文件是不是符合你的习惯

如果 dry-run 没问题，再去掉 `--dry-run` 真跑。

### 4. 日常最常用的几个脚本

- `optimize.py`：单个结构优化
- `frequency.py`：单个结构频率
- `single_point.py`：单个结构单点能
- `uvvis.py`：UV/Vis 光谱
- `nmr.py`：NMR 屏蔽张量 / J 耦合
- `ir.py`：IR 光谱
- `vcd.py`：VCD 光谱
- `nearir.py`：Near-IR 近似流程
- `batch_opt.py`：一个目录里很多 xyz 批量优化
- `batch_sp.py`：一个目录里很多 xyz 批量单点
- `crest_screen.py`：CREST 构象搜索
- `conformer_screen.py`：xTB 预筛后 ORCA 精修
- `inspect_runs.py`：快速看最近任务和失败任务
- `summarize_runs.py`：把已有 runs 目录汇总成表

### 5. 一个最简单的日常流程

如果你只想从一个 xyz 开始做优化，最简单就是：

```powershell
python scripts\optimize.py .\molecule.xyz --config-file .\qm_auto_config.json --dry-run
python scripts\optimize.py .\molecule.xyz --config-file .\qm_auto_config.json
python scripts\inspect_runs.py .\runs
```

如果你有一批 xyz 要一起优化：

```powershell
python scripts\batch_opt.py .\ensemble\ --config-file .\qm_auto_config.json --engine xtb --workers 8 --nprocs-per-job 2
```

如果你想先做构象搜索：

```powershell
python scripts\crest_screen.py .\molecule.xyz --config-file .\qm_auto_config.json --preset default --nprocs 8
```

### 6. 运行后目录里会看到什么

每次运行都会自动建一个新的任务目录，里面通常有：

- `inputs/`：原始输入文件
- `logs/`：标准输出、标准错误
- `results/`：最终结构、metadata、汇总结果
- `attempts/`：每次尝试的中间文件
- `commands/`：原生命令、`.sh`、`.ps1` 复跑脚本

你可以把它理解成：脚本帮你把“这次计算相关的东西”打包整理好，方便事后回看和手工复跑。

### 7. CREST 是否已经包含在项目里

是，已经包含。

目前与 CREST 直接相关的内容有：

- `crest_screen.py`：直接做 CREST 构象搜索
- `crest_cmd` / `--crest-cmd` / `CREST_CMD`：指定 CREST 可执行程序路径
- `examples/config.windows.json` 和 `examples/config.linux.json`：都已经预留了 `crest_cmd`

也就是说，CREST 不是“以后再加”的计划项，而是现在就能直接用的现有功能。

## 已实现任务

- `optimize.py`: 几何优化，支持 ORCA/Gaussian/xTB
- `frequency.py`: 频率分析，支持 ORCA/Gaussian
- `single_point.py`: 单点能，支持 ORCA/Gaussian/xTB
- `uvvis.py`: UV/Vis 激发态吸收，支持 ORCA/Gaussian，可调态数、TDA、隐式溶剂、NTO
- `ecd.py`: ECD 电子圆二色，支持 ORCA/Gaussian，可调态数、TDA、隐式溶剂、NTO
- `nmr.py`: NMR 屏蔽张量，支持 ORCA/Gaussian，可选 spin-spin 耦合与 gauge 方案
- `raman.py`: Raman 光谱，支持 ORCA/Gaussian，可结合隐式溶剂
- `ir.py`: IR 光谱，支持 ORCA/Gaussian，可结合隐式溶剂
- `vcd.py`: VCD 振动圆二色，当前支持 ORCA
- `nearir.py`: Near-IR 泛频/组合带近似，当前支持 ORCA
- `batch_sp.py`: 批量单点并行计算，并输出 CSV/JSON 汇总
- `batch_opt.py`: 批量优化，并输出 CSV/JSON 汇总
- `conformer_screen.py`: 多构象并行筛选，默认 xTB 预筛后 ORCA 精修
- `crest_screen.py`: CREST 构象搜索，适合个人工作站做本地预筛
- `ts_retry.py`: 过渡态优化重试流程，针对常见 SCF/收敛失败自动试错
- `scan.py`: ORCA 势能面扫描，支持键长/键角/二面角扫描
- `irc.py`: ORCA IRC 路径跟踪
- `neb.py`: ORCA NEB 反应路径搜索，读取反应物/产物双端点
- `summarize_runs.py`: 汇总已有 runs 目录中的 metadata 为 CSV
- `postprocess_results.py`: 对 batch 或 runs 的 summary JSON 做后处理、筛最低能、输出统计
- `inspect_runs.py`: 面向个人工作站的本地运行概览，快速看最新、失败和最低能结果

## 默认软件选择

- `optimize.py`: 默认 ORCA，理由是现代复合方法和自动重试更容易封装。
- `frequency.py`: 默认 Gaussian，理由是大量用户对其频率输入和输出更熟悉。
- `single_point.py`: 默认 ORCA，适合承接前面的 ORCA 优化结果继续做高等级单点。
- `uvvis.py`: 默认 Gaussian，原因是 TD route section 对多数用户更直观；ORCA 也可用。
- `ecd.py`: 默认 Gaussian，原因是很多用户习惯直接在 TD 输出里查看 ECD 数据；ORCA 也可用。
- `nmr.py`: 默认 ORCA，原因是 GIAO 与 spin-spin 相关控制块更容易结构化暴露。
- `raman.py`: 默认 ORCA，原因是解析 Raman 活度与极化率导数链更直接。
- `ir.py`: 默认 Gaussian，原因是很多用户会把它直接视为常规频率任务的光谱化入口。
- `vcd.py`: 默认 ORCA，因为当前实现直接依赖 ORCA 的解析 VCD 链。
- `nearir.py`: 默认 ORCA，因为当前实现直接依赖 ORCA 的 NEARIR / XTBVPT2 工作流。
- `conformer_screen.py`: 默认 xTB 预筛 + ORCA 精修，这是更贴近实际批处理的组合。
- `ts_retry.py`: 默认 ORCA，因为过渡态任务最需要自动重试和参数试错。

如果你更熟悉另一套软件，仍然可以用 `--engine` 显式覆盖。

除了默认模板，现在每个任务还提供多套备选模板，可通过 `--preset` 切换，并用 `--list-presets` 查看。

## 安装

### Windows

```powershell
cd c:\Users\procy\Desktop\QM_automation
python -m pip install -e .
```

如果你只想直接运行脚本，也可以不安装，直接使用 `python scripts\xxx.py ...`。

### Linux

```bash
cd ~/QM_automation
python3 -m pip install -e .
```

如果不想安装，同样可以直接运行：

```bash
python3 scripts/optimize.py ./molecule.xyz --dry-run
```

## 可执行程序配置

优先读取环境变量，也可在命令行中覆盖。三种常见方式如下。

### 方式 1：直接放进 PATH

如果 `orca`、`g16`、`xtb` 已经在系统 PATH 中，脚本会自动找到它们。

### 方式 2：设置环境变量

脚本默认读取以下环境变量：

- `ORCA_CMD`
- `GAUSSIAN_CMD`
- `XTB_CMD`
- `CREST_CMD`

例如：

```powershell
$env:ORCA_CMD = "orca"
$env:GAUSSIAN_CMD = "g16"
$env:XTB_CMD = "xtb"
$env:CREST_CMD = "crest"
```

Linux 下例如：

```bash
export ORCA_CMD=/opt/orca/orca
export GAUSSIAN_CMD=/opt/g16/g16
export XTB_CMD=/opt/xtb/xtb
export CREST_CMD=/opt/crest/crest
```

如果可执行程序不在 PATH 中，可以直接写绝对路径，例如：

```powershell
$env:ORCA_CMD = "D:\orca_6_0_1\orca.exe"
$env:GAUSSIAN_CMD = "C:\Gaussian16\g16.exe"
$env:XTB_CMD = "D:\xtb\xtb.exe"
$env:CREST_CMD = "D:\crest\crest.exe"
```

### 方式 3：命令行临时指定

这对多版本软件并存时很有用：

```powershell
python scripts\optimize.py .\molecule.xyz --orca-cmd "D:\orca_6_0_1\orca.exe"
python scripts\frequency.py .\molecule.xyz --gaussian-cmd "C:\Gaussian16\g16.exe"
python scripts\single_point.py .\molecule.xyz --xtb-cmd "D:\xtb\xtb.exe" --engine xtb
python scripts\crest_screen.py .\molecule.xyz --crest-cmd "D:\crest\crest.exe"
```

命令行参数优先级高于环境变量。

### 方式 4：使用 JSON 配置文件

当你需要在 Windows 和 Linux 上分别维护一套固定路径时，这种方式更省事。

示例配置文件 `qm_auto_config.json`：

```json
{
  "runs_root": "D:/qm_runs",
  "orca_cmd": "D:/orca_6_0_1/orca.exe",
  "gaussian_cmd": "C:/Gaussian16/g16.exe",
  "xtb_cmd": "D:/xtb/xtb.exe",
  "crest_cmd": "D:/crest/crest.exe"
}
```

Linux 版本示例：

```json
{
  "runs_root": "/data/qm_runs",
  "orca_cmd": "/opt/orca/orca",
  "gaussian_cmd": "/opt/g16/g16",
  "xtb_cmd": "/opt/xtb/xtb",
  "crest_cmd": "/opt/crest/crest"
}
```

使用方式：

```powershell
python scripts\optimize.py .\molecule.xyz --config-file .\qm_auto_config.json
```

```bash
python3 scripts/optimize.py ./molecule.xyz --config-file ./qm_auto_config.json
```

仓库里也提供了可直接复制修改的示例：

- [examples/config.windows.json](examples/config.windows.json)
- [examples/config.linux.json](examples/config.linux.json)

## 运行前准备

建议先确认：

- Python 版本不少于 3.11。
- ORCA、Gaussian、xTB 至少有你要用到的一种可以在命令行启动。
- 输入 xyz 文件的第一行原子数正确，第二行为注释行。
- 如果使用 Gaussian，相关环境初始化脚本与许可证已可用。
- Linux 下建议确认可执行权限、环境模块或 profile 脚本已经正确加载。

一个最小自检思路是先跑 dry-run，只生成输入和命令，不实际提交计算。

如果准备正式投入使用，建议再做一次“真实外部程序实跑”的最小自检，而不是只停留在 dry-run。

## 快速示例

```powershell
python scripts\optimize.py .\molecule.xyz
python scripts\optimize.py .\molecule.xyz --engine orca --preset hybrid
python scripts\optimize.py .\molecule.xyz --dry-run
python scripts\optimize.py .\molecule.xyz --runs-root D:\qm_runs
python scripts\optimize.py .\molecule.xyz --config-file .\qm_auto_config.json
python scripts\frequency.py .\molecule.xyz
python scripts\frequency.py .\molecule.xyz --engine gaussian --preset thermo
python scripts\single_point.py .\molecule.xyz --engine gaussian --method m062x --basis def2TZVP
python scripts\single_point.py .\molecule.xyz --engine orca --preset doublehybrid
python scripts\uvvis.py .\molecule.xyz --engine gaussian --nstates 30 --solvent acetonitrile
python scripts\uvvis.py .\molecule.xyz --engine orca --nstates 40 --tda --nto --simplified-mode stddft
python scripts\ecd.py .\molecule.xyz --engine gaussian --nstates 40 --solvent methanol
python scripts\nmr.py .\molecule.xyz --engine orca --spin-spin --spin-spin-elements C H --solvent chloroform
python scripts\raman.py .\molecule.xyz --engine orca --solvent water
python scripts\ir.py .\molecule.xyz --engine gaussian --solvent water
python scripts\vcd.py .\molecule.xyz --engine orca --preset hybrid --solvent methanol
python scripts\nearir.py .\molecule.xyz --engine orca --solvent ccl4 --delq 0.1
python scripts\batch_sp.py .\ensemble\ --engine orca --preset cheap --workers 6 --nprocs-per-job 2
python scripts\batch_opt.py .\ensemble\ --engine xtb --workers 8 --nprocs-per-job 2
python scripts\crest_screen.py .\molecule.xyz --preset exhaustive --nprocs 8 --keepdir
python scripts\scan.py .\ts_guess.xyz --scan-type B --atoms 1 2 --start 1.20 --stop 2.80 --steps 12
python scripts\irc.py .\ts_guess.xyz --direction both --max-points 40 --step-size 0.12
python scripts\neb.py .\reactant.xyz --product-xyz .\product.xyz --images 8 --preopt
python scripts\conformer_screen.py .\ensemble\ --workers 4 --orca-method b97-3c
python scripts\conformer_screen.py .\ensemble\ --xtb-preset tight --orca-preset hybrid
python scripts\ts_retry.py .\guess.xyz --nprocs 8 --memory 2048
python scripts\ts_retry.py .\guess.xyz --preset aggressive
python scripts\optimize.py .\molecule.xyz --engine orca --list-presets
python scripts\summarize_runs.py .\runs
python scripts\postprocess_results.py .\runs\runs_summary.json --top 10
python scripts\inspect_runs.py .\runs --latest 10 --failed 10 --lowest 10
```

```bash
python3 scripts/optimize.py ./molecule.xyz
python3 scripts/optimize.py ./molecule.xyz --dry-run
python3 scripts/optimize.py ./molecule.xyz --orca-cmd /opt/orca/orca
python3 scripts/frequency.py ./molecule.xyz --gaussian-cmd /opt/g16/g16
python3 scripts/uvvis.py ./molecule.xyz --engine gaussian --nstates 30 --solvent acetonitrile
python3 scripts/ecd.py ./molecule.xyz --engine orca --nstates 40 --tda --nto
python3 scripts/nmr.py ./molecule.xyz --engine orca --spin-spin --spin-spin-elements C H
python3 scripts/raman.py ./molecule.xyz --engine gaussian --solvent water
python3 scripts/ir.py ./molecule.xyz --engine gaussian --solvent water
python3 scripts/vcd.py ./molecule.xyz --engine orca --preset hybrid --solvent methanol
python3 scripts/nearir.py ./molecule.xyz --engine orca --delq 0.1
python3 scripts/batch_sp.py ./ensemble/ --engine xtb --workers 8 --nprocs-per-job 1
python3 scripts/batch_opt.py ./ensemble/ --engine xtb --workers 8 --nprocs-per-job 2
python3 scripts/crest_screen.py ./molecule.xyz --preset quick --nprocs 8
python3 scripts/scan.py ./ts_guess.xyz --scan-type D --atoms 1 2 3 4 --start -180 --stop 180 --steps 24
python3 scripts/irc.py ./ts_guess.xyz --direction forward --max-points 30
python3 scripts/neb.py ./reactant.xyz --product-xyz ./product.xyz --images 12
python3 scripts/conformer_screen.py ./ensemble/ --xtb-preset tight --orca-preset hybrid --workers 4
python3 scripts/postprocess_results.py ./runs/runs_summary.json --top 10
```

脚本可直接运行，不强制先执行 `pip install -e .`。

## 投用前最小实跑自检

dry-run 只能证明参数和输入生成逻辑基本正常，但不能证明外部 QM 程序真的能在你当前环境里跑通。

真正投入使用前，建议至少拿一个很小的测试分子做一次最小实跑自检。建议最少覆盖这 5 类：

1. UV/Vis
2. NMR
3. IR
4. VCD
5. Near-IR

仓库里已经放了两个可直接改路径的示例：

- [examples/selfcheck.windows.ps1](examples/selfcheck.windows.ps1)
- [examples/selfcheck.linux.sh](examples/selfcheck.linux.sh)

仓库里也同时提供了一个很小的默认测试结构：[examples/methanol.xyz](examples/methanol.xyz)。

这两个脚本默认都会使用这个样例结构，因此你可以先不准备自己的 xyz，直接先做一轮链路检查。

Windows 用法示例：

```powershell
powershell -ExecutionPolicy Bypass -File .\examples\selfcheck.windows.ps1 -DryRun
powershell -ExecutionPolicy Bypass -File .\examples\selfcheck.windows.ps1 -ConfigFile .\examples\config.windows.json
```

Linux 用法示例：

```bash
DRY_RUN=1 bash ./examples/selfcheck.linux.sh
bash ./examples/selfcheck.linux.sh ./examples/config.linux.json
```

说明：

- `dry-run` 模式下，不需要真实 ORCA / Gaussian 路径，主要用于检查命令行参数、输入文件生成和工作目录组织是否正常。
- 真实实跑模式下，建议传入平台对应的配置文件，或者由命令行参数显式指定 QM 程序路径。
- Windows 脚本支持 `-ConfigFile`、`-XyzFile` 和 `-DryRun`。
- Linux 脚本支持“第一个参数是配置文件、第二个参数是 xyz 文件”，并可通过环境变量 `DRY_RUN=1` 切到 dry-run。

这一步主要不是检查“化学结果够不够好”，而是检查：

- 外部程序能否正常启动
- 当前版本是否接受这些 route/block/keyword
- 日志和结果文件是否能完整落盘

建议通过标准：

- 命令没有报“找不到可执行程序”
- `results/run_metadata.json` 中 `success` 为 `true`
- 日志里没有明显的 keyword 报错或 SCF 直接崩溃
- ORCA / Gaussian 的正常结束标记存在

更具体地说，真实实跑后建议优先检查这几处：

- `results/run_metadata.json`：先看 `success`、`engine`、`dry_run`、`stdout`、`stderr` 这些字段是否合理。
- `logs/` 目录：优先看 `orca.stdout.log` / `gaussian.stdout.log`，其次再看对应的 `stderr`。
- `commands/` 目录：如果你怀疑调用方式不对，直接看生成的 `.txt`、`.sh`、`.ps1` 命令文件。

对日志关键词，当前代码里的成功判定和下面这两个标记一致：

- ORCA：标准输出里出现 `ORCA TERMINATED NORMALLY`
- Gaussian：标准输出或标准错误里出现 `Normal termination`

如果 `run_metadata.json` 里 `success=false`，建议按这个顺序排查：

1. 先看 `stderr` 里是否是“命令不存在”或路径错误。
2. 再看 `stdout` 里是否有 route / keyword / block 不被当前版本接受。
3. 再看是否是 SCF 不收敛、内存不足、并行设置过高这类运行时问题。
4. 如果命令文件本身就不符合你的环境习惯，直接修改配置文件里的 `orca_cmd` / `gaussian_cmd` 后重跑。

对第一次真实联调，建议不要一开始就上很大的分子。像 [examples/methanol.xyz](examples/methanol.xyz) 这种小分子更适合先确认：

- 程序能启动
- 输入能被接受
- 日志能正确写入
- 任务目录结构符合预期

如果只想最省时间地先做第一轮确认，优先顺序建议是：

1. `ir.py`
2. `uvvis.py`
3. `nmr.py`
4. `vcd.py`
5. `nearir.py`

也就是说，先把最基础的 IR 和 UV/Vis 跑通，再继续往更依赖程序细节的 VCD / Near-IR 走。

## 光谱工作流说明

这次新增的光谱类任务，优先覆盖个人工作站上最常见、最容易真正落地的四类：

- `uvvis.py`: 电子吸收光谱
- `ecd.py`: 电子圆二色
- `nmr.py`: NMR 屏蔽张量与可选 J 耦合
- `raman.py`: Raman 振动光谱

在这一版基础上，又继续补了三类更偏振动光谱的工作流：

- `ir.py`: 把常规频率任务显式作为 IR 光谱入口来跑
- `vcd.py`: 振动圆二色
- `nearir.py`: 泛频和组合带主导的 Near-IR 近似流程

设计原则不是一次把所有高阶谱学功能都塞进去，而是先把最常用、最容易影响结果的因素显式暴露出来。

### 1. UV/Vis 和 ECD

最常见会影响结果的因素包括：

- 激发态数 `--nstates`
- 是否用 TDA `--tda`
- 是否考虑隐式溶剂 `--solvent` 与 `--solvent-model`
- 是否需要更适合 Rydberg 或电荷转移态的弥散基组
- 对 ORCA，是否导出 NTO `--nto`
- 对较大体系，是否改用 `--simplified-mode stda` 或 `stddft`

经验上：

- 普通有机分子的 UV/Vis，可以从 `default` 模板开始
- 如果怀疑有明显电荷转移或 Rydberg 成分，优先换 `diffuse` 模板
- ECD 通常建议比普通 UV/Vis 多要一些态，例如 30 到 50 个
- 如果只是快速看谱形，TDA 往往是一个实用近似

示例：

```powershell
python scripts\uvvis.py .\molecule.xyz --engine gaussian --nstates 30 --solvent acetonitrile
python scripts\ecd.py .\molecule.xyz --engine orca --nstates 40 --tda --nto --solvent methanol
```

### 2. NMR

NMR 里最常见的影响因素包括：

- 结构是否已经在合适理论级别优化好
- gauge 方案 `--gauge`
- 基组是否足够适合 NMR
- 是否考虑溶剂
- 是否需要自旋-自旋耦合 `--spin-spin`

当前行为：

- ORCA 走 GIAO 主线，并可加 spin-spin 控制
- Gaussian 可在 `giao` 与 `csgt` 间切换，并可加 `SpinSpin`

注意：

- NMR 最怕“结构不对却直接算谱”
- 如果是相对化学位移，标准参考分子的计算应与目标分子保持相同方法和基组
- 隐式溶剂能改进一部分结果，但特定氢键、配位和缔合作用通常仍需要显式分子

示例：

```powershell
python scripts\nmr.py .\molecule.xyz --engine orca --spin-spin --spin-spin-elements C H --solvent chloroform
python scripts\nmr.py .\molecule.xyz --engine gaussian --gauge csgt --solvent dimethylsulfoxide
```

### 3. Raman

Raman 的关键影响因素通常包括：

- 几何是否是真正驻点
- 频率方法与结构方法是否一致
- 是否考虑隐式溶剂
- 基组里是否带弥散函数，以及由此带来的近似误差

当前实现：

- ORCA 通过频率任务附加极化率求导块来得到 Raman 活度
- Gaussian 使用 `freq=raman`

注意：

- 这里首先得到的是 Raman 活度，不是实验谱图里已经按激光线和温度修正后的最终强度
- 如果你的目标是和具体实验激光条件逐点比强度，还需要后续用外部工具或自定义脚本换算

示例：

```powershell
python scripts\raman.py .\molecule.xyz --engine orca --solvent water
python scripts\raman.py .\molecule.xyz --engine gaussian --preset robust
```

### 4. IR、VCD 和 Near-IR

这三类都建立在“频率必须有物理意义”这个前提上，所以最先要看的不是参数，而是结构和方法是否匹配。

IR：

- 本质上仍是频率任务，但这里单独拆成 `ir.py`，目的是把“我要的是谱学输出”这件事和一般热化学频率任务区分开
- 适合直接显式指定溶剂，作为溶液相 IR 的起点

VCD：

- 当前只开放 ORCA
- 依赖解析频率链，不支持数值频率路线
- 对构型、手性中心和溶剂模型更敏感，通常不建议把它当作“随手一算”的附带结果

Near-IR：

- 当前只开放 ORCA
- 本质上是基于 NEARIR 近似加入泛频和组合带，不等于完整高精度振动态后处理
- 默认保留 xTBVPT2 近似，可用 `--no-xtb-vpt2` 关闭
- `--delq` 可用于调数值位移步长

示例：

```powershell
python scripts\ir.py .\molecule.xyz --engine gaussian --solvent water
python scripts\vcd.py .\molecule.xyz --engine orca --preset hybrid --solvent methanol
python scripts\nearir.py .\molecule.xyz --engine orca --solvent ccl4 --delq 0.1
```

### 5. 当前边界

目前这批工作流重点是“先把主流谱学计算跑通并把高频影响因素显式参数化”，还没有进一步自动化这些后处理：

- 自动卷积成最终可画谱线
- NMR 参考物自动扣除
- 构象加权平均谱
- 振动缩放因子自动套用
- 直接驱动 `orca_mapspc`、`orca_nmrspectrum` 这类外部后处理工具
- VCD 谱线后处理与符号约定统一化
- Near-IR 结果的自动泛频/组合带可视化与实验条件映射

这些不是做不到，而是故意先不混进第一版主流程里，避免在你真正投入使用前把链条拉得太长。

不过在继续扩功能前，优先建议先完成上面的最小实跑自检。对投用来说，那一步比再加一类谱更重要。

## Python 扮演的角色

- Python 只负责创建工作目录、生成原始输入、发起命令、整理日志和重试。
- 真正提交给量化程序的命令会写入每个任务目录下的 `commands/` 子目录。
- 同时会生成通用文本、Linux `.sh` 和 Windows PowerShell `.ps1` 三种复跑文件。
- ORCA 的 `job.inp`、Gaussian 的 `job.gjf`、xTB 的原始 xyz 输入都会保存在运行目录里，可直接拿去手工复跑。
- `--dry-run` 模式下不会真正启动量化程序，只会生成这些原始文件。
- 复跑脚本内部会自动切换到正确工作目录，不要求你手工 `cd` 到输入文件所在目录。

## 模板思路

- `default` 表示推荐起点，优先考虑通用性。
- 备选模板会偏向不同需求，例如 `cheap`、`robust`、`hybrid`、`doublehybrid`、`aggressive`。
- 你仍可在选定模板后继续用 `--method`、`--basis` 做小范围覆写，不需要从零手写完整输入。

## 工作目录结构

每次运行会生成类似目录：

```text
runs/
  optimize_20260709_120000_name/
    inputs/
    scratch/
    logs/
    results/
    attempts/
    commands/
      attempt_01/
      attempt_02/
```

更准确地说：

- `inputs/`: Gaussian 与 xTB 的主输入位置。
- `attempts/`: ORCA 每次重试各自独立的输入和中间文件。
- `commands/`: 实际执行的命令文本和跨平台复跑脚本。
- `logs/`: 标准输出和标准错误。
- `results/`: 汇总后的结果文件和 metadata。

批量单点任务还会额外生成：

- `batch_summary.csv`: 适合快速筛选和排序。
- `batch_summary.json`: 适合后续再加工。

批量优化任务还会额外生成：

- `batch_optimize_summary.csv`: 批量优化汇总表。
- `batch_optimize_summary.json`: 批量优化 JSON 汇总。

运行汇总与后处理常见产物：

- `runs_summary.csv`: 全部 runs 的表格汇总。
- `runs_summary.json`: 全部 runs 的 JSON 汇总。
- `runs_stats.json`: 成功率、引擎分布、任务分布、最低能样本统计。
- `*.lowest.csv` / `*.lowest.json`: 从 summary JSON 中筛出的最低能记录。

扫描任务常见产物：

- `scan_profile.csv`: 每个扫描点的绝对能量与相对能量。
- `scan_profile.json`: 同一份扫描曲线的 JSON 版本。
- `scan_lowest.json`: 自动筛出的最低能扫描点。

在 `commands/` 下通常会看到：

- `*.txt`: 记录实际工作目录和命令行。
- `*.sh`: Linux 下可直接 `bash xxx.sh` 复跑。
- `*.ps1`: Windows PowerShell 下可直接复跑。

## 推荐上手顺序

1. 先用 `--dry-run` 检查生成的输入文件和命令是否符合你的习惯。
2. 再跑一个最简单的小分子优化任务，确认软件路径与输出识别正常。
3. 最后再上批量构象筛选或过渡态自动重试这类更重的任务。

## 常见命令模式

### 1. 只生成输入，不运行

```powershell
python scripts\optimize.py .\molecule.xyz --dry-run
```

```bash
python3 scripts/optimize.py ./molecule.xyz --dry-run
```

### 2. 使用指定 ORCA 路径

```powershell
python scripts\optimize.py .\molecule.xyz --orca-cmd "D:\orca_6_0_1\orca.exe"
```

```bash
python3 scripts/optimize.py ./molecule.xyz --orca-cmd /opt/orca/orca
```

### 3. 把运行目录写到另一块硬盘

```powershell
python scripts\optimize.py .\molecule.xyz --runs-root D:\qm_runs
```

```bash
python3 scripts/optimize.py ./molecule.xyz --runs-root /data/qm_runs
```

### 4. 查看可用模板

```powershell
python scripts\single_point.py .\molecule.xyz --engine orca --list-presets
```

### 5. 先 xTB 预筛，再 ORCA 精修

```powershell
python scripts\conformer_screen.py .\ensemble\ --xtb-preset tight --orca-preset hybrid --workers 4
```

### 6. 批量单点并行 + 输出汇总表

```powershell
python scripts\batch_sp.py .\ensemble\ --engine orca --preset cheap --workers 6 --nprocs-per-job 2
```

```bash
python3 scripts/batch_sp.py ./ensemble/ --engine xtb --workers 8 --nprocs-per-job 1
```

### 6A. 批量优化

```powershell
python scripts\batch_opt.py .\ensemble\ --engine xtb --workers 8 --nprocs-per-job 2
```

```bash
python3 scripts/batch_opt.py ./ensemble/ --engine xtb --workers 8 --nprocs-per-job 2
```

### 6B. CREST 构象搜索

```powershell
python scripts\crest_screen.py .\molecule.xyz --preset exhaustive --nprocs 8 --keepdir
```

```bash
python3 scripts/crest_screen.py ./molecule.xyz --preset quick --nprocs 8
```

### 7. 势能面扫描

```powershell
python scripts\scan.py .\scan_guess.xyz --scan-type B --atoms 1 2 --start 1.20 --stop 2.80 --steps 12
python scripts\scan.py .\scan_guess.xyz --scan-type D --atoms 1 2 3 4 --start -180 --stop 180 --steps 24 --preset cheap
```

```bash
python3 scripts/scan.py ./scan_guess.xyz --scan-type A --atoms 1 2 3 --start 90 --stop 150 --steps 13
```

### 8. IRC 路径跟踪

```powershell
python scripts\irc.py .\ts_guess.xyz --direction both --max-points 40 --step-size 0.12
```

```bash
python3 scripts/irc.py ./ts_guess.xyz --direction forward --max-points 30
```

`--direction both` 现在会显式生成 forward 和 backward 两套独立运行，并额外输出 `irc_pair_summary.csv/json`。

### 9. NEB 反应路径搜索

```powershell
python scripts\neb.py .\reactant.xyz --product-xyz .\product.xyz --images 8 --preopt
```

```bash
python3 scripts/neb.py ./reactant.xyz --product-xyz ./product.xyz --images 12
```

### 10. 汇总已有运行记录

```powershell
python scripts\summarize_runs.py .\runs
```

```bash
python3 scripts/summarize_runs.py ./runs
```

### 11. 对 summary JSON 做后处理

```powershell
python scripts\postprocess_results.py .\runs\runs_summary.json --top 10
python scripts\postprocess_results.py .\runs\batch_summary.json --top 20 --output-csv .\lowest20.csv
```

```bash
python3 scripts/postprocess_results.py ./runs/runs_summary.json --top 10
```

### 12. 查看个人工作站本地运行概览

```powershell
python scripts\inspect_runs.py .\runs --latest 10 --failed 10 --lowest 10
```

```bash
python3 scripts/inspect_runs.py ./runs --latest 10 --failed 10 --lowest 10
```

## 常见后处理用途

- 从批量单点结果中直接筛出最低能前若干结构。
- 把 dry-run、失败任务和成功任务分开统计。
- 快速查看不同引擎、不同任务的运行数量。
- 给后续人工复核或再计算提供一个更干净的候选列表。

## 新任务说明

- `scan.py` 当前先实现 ORCA 版扫描，适合先摸键长拉伸、键角变化或二面角转动的势能面。
- `irc.py` 当前先实现 ORCA 版 IRC，适合在过渡态频率确认之后继续跟踪前后方向路径。
- `neb.py` 当前先实现 ORCA 版双端点 NEB，适合已有反应物和产物猜测结构的场景。
- `crest_screen.py` 适合个人工作站先做本地 CREST 构象搜索，再把候选交给 xTB/ORCA 深化。
- `batch_opt.py` 适合一个目录里很多 xyz 的日常本地批量优化。
- `inspect_runs.py` 适合个人工作站随手查看最近跑了什么、哪里失败了、最低能是谁。
- `scan.py`、`irc.py`、`neb.py` 都支持 `--dry-run`，因此可以先检查 `%geom`、`%irc` 或 `%neb` 块是否符合你的习惯。

## Linux 说明

- 路径分隔符使用 `/`，命令建议用 `python3`。
- 如果软件依赖模块系统，可先执行 `module load orca`、`module load gaussian`、`module load xtb`，再运行脚本。
- 如果 Gaussian 需要 source 环境脚本，建议先在当前 shell 中完成，再启动本工具。
- 运行生成的 `.sh` 复跑脚本前，可直接执行 `bash commands/orca_attempt_01.sh` 这类命令。
- `.ps1` 复跑脚本会自动 `Set-Location` 到对应目录，再执行量化命令。

## 个人工作站建议

- 优先用 `batch_opt.py`、`batch_sp.py` 控制并行度，而不是一次手开很多终端。
- 若本机内存有限，可把 `--workers` 设低、把 `--nprocs-per-job` 设高，避免同时起太多量化进程。
- 若以构象问题为主，可先 `crest_screen.py`，再把最低能候选交给 `conformer_screen.py` 或 `batch_sp.py`。
- 每天结束前用 `inspect_runs.py` 或 `summarize_runs.py` 检查失败任务和最低能结果，避免第二天再翻日志。

## 建议新增任务方向

- `crest_screen.py`: 与 CREST 联动的更完整构象搜索。
- `batch_frequency.py`: 一批结构统一做频率并汇总热力学校正。
- `lowest_structures.py`: 自动复制或导出最低能前 N 个结构。

## 说明

- 本项目默认只负责生成输入、调度计算、保存日志和整理结果。
- ORCA/Gaussian/xTB 本体安装与许可证需用户自行保证。
- 若输入 xyz 中包含多个结构，推荐使用 `conformer_screen.py` 批量处理。