from __future__ import annotations

from qm_automation.models import TemplateProfile


# 这里集中定义“默认方案 + 备选方案”。
# Python 只负责从这些模板里选配置，再生成对应软件的原生输入和命令。
PRESET_CATALOG: dict[str, dict[str, dict[str, TemplateProfile]]] = {
    "optimize": {
        "orca": {
            "default": TemplateProfile("optimize", "orca", "default", "快速稳健几何优化，适合大多数常规结构", "r2scan-3c", "", "OPT", ("TightSCF",)),
            "hybrid": TemplateProfile("optimize", "orca", "hybrid", "杂化泛函优化，适合后续接高等级单点", "wb97x-d4", "def2-TZVP", "OPT", ("RIJCOSX", "DEFGRID3", "TightSCF")),
            "cheap": TemplateProfile("optimize", "orca", "cheap", "更便宜的预优化模板，适合先粗略收敛", "b97-3c", "", "OPT", ("TightSCF",)),
        },
        "gaussian": {
            "default": TemplateProfile("optimize", "gaussian", "default", "常规 DFT 几何优化", "b3lyp", "6-31g(d)", "opt"),
            "robust": TemplateProfile("optimize", "gaussian", "robust", "带更稳健 SCF 与积分网格的优化", "m062x", "def2SVP", "opt", ("scf=xqc", "integral=ultrafine")),
            "tight": TemplateProfile("optimize", "gaussian", "tight", "更严格的收敛标准", "pbe0", "def2TZVP", "opt=tight", ("scf=xqc",)),
        },
        "xtb": {
            "default": TemplateProfile("optimize", "xtb", "default", "GFN2-xTB 快速优化", "2", "", "--opt"),
            "fast": TemplateProfile("optimize", "xtb", "fast", "GFN1-xTB 更快预优化", "1", "", "--opt"),
            "tight": TemplateProfile("optimize", "xtb", "tight", "更严格的 xTB 优化收敛", "2", "", "--opt", (), ("--cycles", "400")),
        },
    },
    "frequency": {
        "gaussian": {
            "default": TemplateProfile("frequency", "gaussian", "default", "常规谐振频率分析", "b3lyp", "6-31g(d)", "freq"),
            "robust": TemplateProfile("frequency", "gaussian", "robust", "更稳健的频率分析模板", "m062x", "def2SVP", "freq", ("scf=xqc", "integral=ultrafine")),
            "thermo": TemplateProfile("frequency", "gaussian", "thermo", "适合热化学输出的较常见模板", "wb97xd", "def2TZVP", "freq", ("scf=xqc",)),
        },
        "orca": {
            "default": TemplateProfile("frequency", "orca", "default", "ORCA 频率分析", "r2scan-3c", "", "FREQ", ("TightSCF",)),
            "hybrid": TemplateProfile("frequency", "orca", "hybrid", "杂化泛函频率分析", "wb97x-d4", "def2-TZVP", "FREQ", ("RIJCOSX", "TightSCF")),
            "tight": TemplateProfile("frequency", "orca", "tight", "更严格的 SCF 频率分析", "pbe0", "def2-TZVP", "FREQ", ("VeryTightSCF",)),
        },
    },
    "single_point": {
        "orca": {
            "default": TemplateProfile("single_point", "orca", "default", "较通用的 DFT 单点模板", "wb97x-d4", "def2-TZVP", "SP", ("RIJCOSX", "TightSCF")),
            "doublehybrid": TemplateProfile("single_point", "orca", "doublehybrid", "双杂化单点模板", "dsd-blyp", "def2-QZVP", "SP", ("D4", "RIJCOSX", "TightSCF")),
            "cheap": TemplateProfile("single_point", "orca", "cheap", "较廉价的单点模板", "b97-3c", "", "SP", ("TightSCF",)),
        },
        "gaussian": {
            "default": TemplateProfile("single_point", "gaussian", "default", "Gaussian 常规单点模板", "m062x", "def2TZVP", "sp"),
            "robust": TemplateProfile("single_point", "gaussian", "robust", "更稳健的单点 SCF 模板", "wb97xd", "def2TZVP", "sp", ("scf=xqc", "integral=ultrafine")),
            "cheap": TemplateProfile("single_point", "gaussian", "cheap", "较廉价的单点模板", "b3lyp", "6-31g(d)", "sp"),
        },
        "xtb": {
            "default": TemplateProfile("single_point", "xtb", "default", "GFN2-xTB 单点", "2", "", "--sp"),
            "fast": TemplateProfile("single_point", "xtb", "fast", "GFN1-xTB 更快单点", "1", "", "--sp"),
            "gbsa": TemplateProfile("single_point", "xtb", "gbsa", "带 GBSA 水溶剂的 xTB 单点", "2", "", "--sp", (), ("--gbsa", "water")),
        },
    },
    "uvvis": {
        "orca": {
            "default": TemplateProfile("uvvis", "orca", "default", "常规 UV/Vis TDDFT 模板", "cam-b3lyp", "def2-TZVPD", "SP", ("RIJCOSX", "DEFGRID3", "TightSCF")),
            "compact": TemplateProfile("uvvis", "orca", "compact", "更省资源的 UV/Vis 模板", "wb97x-d4", "def2-SVP", "SP", ("RIJCOSX", "TightSCF")),
            "diffuse": TemplateProfile("uvvis", "orca", "diffuse", "更适合含 Rydberg/电荷转移成分的模板", "cam-b3lyp", "ma-def2-TZVP", "SP", ("RIJCOSX", "DEFGRID3", "TightSCF")),
        },
        "gaussian": {
            "default": TemplateProfile("uvvis", "gaussian", "default", "常规 UV/Vis TDDFT 模板", "cam-b3lyp", "def2TZVP", "sp"),
            "compact": TemplateProfile("uvvis", "gaussian", "compact", "更省资源的 UV/Vis 模板", "wb97xd", "6-31+g(d,p)", "sp", ("scf=xqc",)),
            "diffuse": TemplateProfile("uvvis", "gaussian", "diffuse", "更适合含 Rydberg/电荷转移成分的模板", "cam-b3lyp", "6-311+g(2d,p)", "sp", ("scf=xqc", "integral=ultrafine")),
        },
    },
    "ecd": {
        "orca": {
            "default": TemplateProfile("ecd", "orca", "default", "常规 ECD TDDFT 模板", "cam-b3lyp", "def2-TZVPD", "SP", ("RIJCOSX", "DEFGRID3", "TightSCF")),
            "compact": TemplateProfile("ecd", "orca", "compact", "更省资源的 ECD 模板", "wb97x-d4", "def2-SVP", "SP", ("RIJCOSX", "TightSCF")),
            "diffuse": TemplateProfile("ecd", "orca", "diffuse", "更强调弥散函数的 ECD 模板", "cam-b3lyp", "ma-def2-TZVP", "SP", ("RIJCOSX", "DEFGRID3", "TightSCF")),
        },
        "gaussian": {
            "default": TemplateProfile("ecd", "gaussian", "default", "常规 ECD TDDFT 模板", "cam-b3lyp", "def2TZVP", "sp"),
            "compact": TemplateProfile("ecd", "gaussian", "compact", "更省资源的 ECD 模板", "wb97xd", "6-31+g(d,p)", "sp", ("scf=xqc",)),
            "diffuse": TemplateProfile("ecd", "gaussian", "diffuse", "更强调弥散函数的 ECD 模板", "cam-b3lyp", "6-311+g(2d,p)", "sp", ("scf=xqc", "integral=ultrafine")),
        },
    },
    "nmr": {
        "orca": {
            "default": TemplateProfile("nmr", "orca", "default", "GIAO NMR 屏蔽张量模板", "pbe0", "pcSseg-2", "SP", ("TightSCF",)),
            "robust": TemplateProfile("nmr", "orca", "robust", "更稳健的 NMR 模板", "pbe0", "pcSseg-3", "SP", ("DEFGRID3", "TightSCF")),
            "cheap": TemplateProfile("nmr", "orca", "cheap", "较廉价的 NMR 模板", "b3lyp", "def2-TZVP", "SP", ("TightSCF",)),
        },
        "gaussian": {
            "default": TemplateProfile("nmr", "gaussian", "default", "Gaussian NMR 屏蔽张量模板", "b3lyp", "6-311+g(2d,p)", "sp"),
            "robust": TemplateProfile("nmr", "gaussian", "robust", "更稳健的 Gaussian NMR 模板", "pbe1pbe", "def2TZVP", "sp", ("scf=xqc", "integral=ultrafine")),
            "cheap": TemplateProfile("nmr", "gaussian", "cheap", "较廉价的 Gaussian NMR 模板", "b3lyp", "6-31g(d)", "sp"),
        },
    },
    "raman": {
        "orca": {
            "default": TemplateProfile("raman", "orca", "default", "解析 Raman 活度模板", "pbe0", "def2-TZVP", "FREQ", ("RIJCOSX", "TightSCF")),
            "robust": TemplateProfile("raman", "orca", "robust", "更稳健的 Raman 模板", "wb97x-d4", "def2-TZVP", "FREQ", ("RIJCOSX", "DEFGRID3", "TightSCF")),
            "cheap": TemplateProfile("raman", "orca", "cheap", "较廉价的 Raman 模板", "b3lyp", "def2-SVP", "FREQ", ("RIJCOSX", "TightSCF")),
        },
        "gaussian": {
            "default": TemplateProfile("raman", "gaussian", "default", "Gaussian Raman 频率模板", "b3lyp", "6-31+g(d,p)", "freq=raman"),
            "robust": TemplateProfile("raman", "gaussian", "robust", "更稳健的 Gaussian Raman 模板", "pbe1pbe", "def2TZVP", "freq=raman", ("scf=xqc", "integral=ultrafine")),
            "cheap": TemplateProfile("raman", "gaussian", "cheap", "较廉价的 Gaussian Raman 模板", "b3lyp", "6-31g(d)", "freq=raman"),
        },
    },
    "ir": {
        "orca": {
            "default": TemplateProfile("ir", "orca", "default", "IR 光谱频率模板", "r2scan-3c", "", "FREQ", ("TightSCF",)),
            "hybrid": TemplateProfile("ir", "orca", "hybrid", "杂化泛函 IR 模板", "wb97x-d4", "def2-TZVP", "FREQ", ("RIJCOSX", "TightSCF")),
            "tight": TemplateProfile("ir", "orca", "tight", "更稳健的 IR 模板", "pbe0", "def2-TZVP", "FREQ", ("RIJCOSX", "DEFGRID3", "TightSCF")),
        },
        "gaussian": {
            "default": TemplateProfile("ir", "gaussian", "default", "Gaussian IR 光谱模板", "b3lyp", "6-31g(d)", "freq"),
            "robust": TemplateProfile("ir", "gaussian", "robust", "更稳健的 Gaussian IR 模板", "m062x", "def2SVP", "freq", ("scf=xqc", "integral=ultrafine")),
            "thermo": TemplateProfile("ir", "gaussian", "thermo", "适合热化学与 IR 一起输出的模板", "wb97xd", "def2TZVP", "freq", ("scf=xqc",)),
        },
    },
    "vcd": {
        "orca": {
            "default": TemplateProfile("vcd", "orca", "default", "ORCA VCD 解析频率模板", "b3lyp", "def2-SVP", "AnFreq", ("TightSCF",)),
            "hybrid": TemplateProfile("vcd", "orca", "hybrid", "更常用的杂化泛函 VCD 模板", "pbe0", "def2-TZVP", "AnFreq", ("RIJCOSX", "TightSCF")),
            "robust": TemplateProfile("vcd", "orca", "robust", "更稳健的 VCD 模板", "wb97x-d4", "def2-TZVP", "AnFreq", ("RIJCOSX", "DEFGRID3", "TightSCF")),
        },
    },
    "nearir": {
        "orca": {
            "default": TemplateProfile("nearir", "orca", "default", "ORCA Near-IR 模板，含泛频与组合带近似", "b3lyp", "def2-TZVP", "FREQ", ("RIJCOSX", "NEARIR", "TightSCF")),
            "hybrid": TemplateProfile("nearir", "orca", "hybrid", "更高等级的 Near-IR 模板", "pbe0", "def2-TZVP", "FREQ", ("RIJCOSX", "NEARIR", "TightSCF")),
            "doublehybrid": TemplateProfile("nearir", "orca", "doublehybrid", "适合配合 xTBVPT2 的双杂化 Near-IR 模板", "b2plyp", "def2-TZVP", "NumFREQ", ("RIJCOSX", "NEARIR", "TightSCF")),
        },
    },
    "ts_retry": {
        "orca": {
            "default": TemplateProfile("ts_retry", "orca", "default", "常规过渡态搜索与频率确认", "r2scan-3c", "", "OptTS Freq", ("TightSCF",)),
            "hybrid": TemplateProfile("ts_retry", "orca", "hybrid", "杂化泛函过渡态模板", "wb97x-d4", "def2-SVP", "OptTS Freq", ("RIJCOSX", "TightSCF")),
            "aggressive": TemplateProfile("ts_retry", "orca", "aggressive", "更激进的收敛模板，适合难收敛 TS", "r2scan-3c", "", "OptTS Freq", ("VeryTightSCF", "SlowConv", "SOSCF")),
        },
    },
    "scan": {
        "orca": {
            "default": TemplateProfile("scan", "orca", "default", "常规约束扫描模板", "r2scan-3c", "", "OPT", ("TightSCF",)),
            "cheap": TemplateProfile("scan", "orca", "cheap", "较廉价的扫描模板，适合先摸势能面", "b97-3c", "", "OPT", ("TightSCF",)),
            "hybrid": TemplateProfile("scan", "orca", "hybrid", "较高等级扫描模板", "wb97x-d4", "def2-SVP", "OPT", ("RIJCOSX", "TightSCF")),
        },
    },
    "irc": {
        "orca": {
            "default": TemplateProfile("irc", "orca", "default", "常规 IRC 路径跟踪模板", "r2scan-3c", "", "IRC", ("TightSCF",)),
            "hybrid": TemplateProfile("irc", "orca", "hybrid", "杂化泛函 IRC 模板", "wb97x-d4", "def2-SVP", "IRC", ("RIJCOSX", "TightSCF")),
            "robust": TemplateProfile("irc", "orca", "robust", "更稳健的 IRC 模板", "r2scan-3c", "", "IRC", ("VeryTightSCF", "SlowConv")),
        },
    },
    "neb": {
        "orca": {
            "default": TemplateProfile("neb", "orca", "default", "常规 NEB-TS 模板", "r2scan-3c", "", "NEB-TS", ("TightSCF",)),
            "cheap": TemplateProfile("neb", "orca", "cheap", "较廉价的 NEB-CI 模板", "b97-3c", "", "NEB-CI", ("TightSCF",)),
            "hybrid": TemplateProfile("neb", "orca", "hybrid", "杂化泛函 NEB-TS 模板", "wb97x-d4", "def2-SVP", "NEB-TS", ("RIJCOSX", "TightSCF")),
        },
    },
    "crest": {
        "crest": {
            "default": TemplateProfile("crest", "crest", "default", "常规 CREST 构象搜索", "gfn2", "", "crest", (), ("--ewin", "6")),
            "quick": TemplateProfile("crest", "crest", "quick", "较快的 CREST 预筛模板", "gfn2", "", "crest", (), ("--quick",)),
            "exhaustive": TemplateProfile("crest", "crest", "exhaustive", "更彻底的 CREST 构象搜索", "gfn2", "", "crest", (), ("--ewin", "12", "--noreftopo")),
        },
    },
}


def available_presets(task_name: str, engine: str) -> list[TemplateProfile]:
    task_catalog = PRESET_CATALOG.get(task_name, {})
    engine_catalog = task_catalog.get(engine, {})
    return list(engine_catalog.values())


def resolve_profile(task_name: str, engine: str, preset_name: str | None, method: str | None, basis: str | None) -> TemplateProfile:
    task_catalog = PRESET_CATALOG.get(task_name, {})
    engine_catalog = task_catalog.get(engine)
    if not engine_catalog:
        raise ValueError(f"任务 {task_name} 暂不支持引擎 {engine} 的模板")

    selected_name = preset_name or "default"
    if selected_name not in engine_catalog:
        candidates = ", ".join(engine_catalog)
        raise ValueError(f"未知模板 {selected_name}，可选值: {candidates}")

    base = engine_catalog[selected_name]
    return TemplateProfile(
        task_name=base.task_name,
        engine=base.engine,
        preset_name=base.preset_name,
        description=base.description,
        method=method or base.method,
        basis=base.basis if basis is None else basis,
        driver=base.driver,
        extra_keywords=base.extra_keywords,
        extra_flags=base.extra_flags,
    )


def format_preset_help(task_name: str, engine: str) -> str:
    profiles = available_presets(task_name, engine)
    if not profiles:
        return f"{task_name}/{engine}: 暂无可用模板"
    lines = [f"{task_name}/{engine} 可用模板:"]
    for profile in profiles:
        basis_part = f"/{profile.basis}" if profile.basis else ""
        lines.append(f"- {profile.preset_name}: {profile.method}{basis_part} | {profile.description}")
    return "\n".join(lines)