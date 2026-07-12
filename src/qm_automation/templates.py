from __future__ import annotations

from qm_automation.models import Molecule, RetryProfile


def render_orca_input(
    molecule: Molecule,
    task_directive: str,
    method: str,
    basis: str,
    charge: int,
    mult: int,
    nprocs: int,
    maxcore_mb: int,
    retry: RetryProfile | None = None,
    extra_keywords: tuple[str, ...] = (),
    extra_blocks: tuple[str, ...] = (),
) -> str:
    # ORCA 输入保持尽量接近用户手写 inp 的样子，Python 只负责把变量填进去。
    retry_keywords = tuple(retry.extra_keywords) if retry else ()
    all_keywords = " ".join([*extra_keywords, *retry_keywords])
    return "\n".join(
        [
            f"! {task_directive} {method} {basis} {all_keywords}".strip(),
            f"%pal nprocs {nprocs} end",
            f"%maxcore {maxcore_mb}",
            *extra_blocks,
            f"* xyz {charge} {mult}",
            molecule.atoms_block,
            "*",
            "",
        ]
    )


def render_gaussian_input(
    molecule: Molecule,
    route: str,
    charge: int,
    mult: int,
    nprocs: int,
    mem_gb: int,
    footer_lines: tuple[str, ...] = (),
) -> str:
    # Gaussian 也是原生 gjf 结构，便于用户直接打开检查 route section。
    return "\n".join(
        [
            f"%nprocshared={nprocs}",
            f"%mem={mem_gb}GB",
            f"#p {route}",
            "",
            molecule.name,
            "",
            f"{charge} {mult}",
            molecule.atoms_block,
            *footer_lines,
            "",
        ]
    )


def render_orca_scan_block(scan_type: str, atom_indices: tuple[int, ...], start: float, stop: float, steps: int) -> str:
    coord = scan_type.upper()
    atoms = " ".join(str(index) for index in atom_indices)
    return "\n".join(
        [
            "%geom",
            f"  Scan {coord} {atoms} = {start:.6f}, {stop:.6f}, {steps}",
            "end",
        ]
    )


def render_orca_irc_block(direction: str, max_points: int, step_size: float) -> str:
    direction_lines = [] if direction.lower() == "both" else [f"  Direction {direction.lower()}"]
    return "\n".join(
        [
            "%irc",
            *direction_lines,
            f"  MaxIter {max_points}",
            f"  InitHess read",
            f"  Scale_Displ_SD {step_size:.6f}",
            "end",
        ]
    )


def render_orca_neb_block(product_filename: str, images: int, preopt: bool) -> str:
    preopt_value = "true" if preopt else "false"
    return "\n".join(
        [
            "%neb",
            f"  Product \"{product_filename}\"",
            f"  NImages {images}",
            f"  PreOpt {preopt_value}",
            "end",
        ]
    )


def render_orca_tddft_block(
    nroots: int,
    use_tda: bool,
    triplets: bool,
    do_nto: bool,
    simplified_mode: str,
) -> str:
    mode_lines: list[str] = []
    simplified = simplified_mode.lower()
    if simplified == "stda":
        mode_lines.append("  Mode sTDA")
    elif simplified == "stddft":
        mode_lines.append("  Mode sTDDFT")
    elif simplified != "off":
        raise ValueError(f"未知 simplified_mode: {simplified_mode}")

    return "\n".join(
        [
            "%tddft",
            f"  NRoots {nroots}",
            f"  TDA {'true' if use_tda else 'false'}",
            f"  Triplets {'true' if triplets else 'false'}",
            f"  DoNTO {'true' if do_nto else 'false'}",
            *mode_lines,
            "end",
        ]
    )


def render_orca_eprnmr_block(
    *,
    shift_all: bool,
    spinspin_elements: tuple[str, ...],
    spinspin_rthresh: float,
    print_reduced_coupling: bool,
) -> str:
    nuclei_lines = [f"  Nuclei = all {element} {{ ssall }}" for element in spinspin_elements]
    lines = ["%eprnmr"]
    if shift_all:
        lines.append("  NMRShielding 2")
    lines.extend(nuclei_lines)
    if nuclei_lines:
        lines.append(f"  SpinSpinRThresh {spinspin_rthresh:.3f}")
        lines.append(f"  PrintReducedCoupling {'true' if print_reduced_coupling else 'false'}")
    lines.append("end")
    return "\n".join(lines)


def render_orca_elprop_block(polar_order: int = 1) -> str:
    return "\n".join(
        [
            "%elprop",
            f"  Polar {polar_order}",
            "end",
        ]
    )


def render_xtb_command(
    xyz_name: str,
    task_flag: str,
    charge: int,
    mult: int,
    gfn: str,
    extra_flags: list[str] | None = None,
) -> list[str]:
    # xTB 不需要额外输入文件时，直接拼出原生命令行参数。
    flags = [xyz_name, task_flag, "--chrg", str(charge), "--uhf", str(max(mult - 1, 0)), "--gfn", gfn]
    if extra_flags:
        flags.extend(extra_flags)
    return flags