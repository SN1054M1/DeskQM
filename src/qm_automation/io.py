from __future__ import annotations

from pathlib import Path

from qm_automation.models import Molecule


def read_xyz(xyz_path: Path) -> Molecule:
    lines = xyz_path.read_text(encoding="utf-8-sig").splitlines()
    if len(lines) < 3:
        raise ValueError(f"XYZ 文件内容不足: {xyz_path}")

    natoms = int(lines[0].strip())
    comment = lines[1].strip()
    atom_lines = lines[2 : 2 + natoms]
    if len(atom_lines) != natoms:
        raise ValueError(f"XYZ 原子数与文件内容不一致: {xyz_path}")

    return Molecule(
        name=xyz_path.stem,
        natoms=natoms,
        comment=comment,
        atoms_block="\n".join(atom_lines),
        source=xyz_path.resolve(),
    )


def write_xyz(path: Path, molecule: Molecule, comment: str | None = None) -> None:
    text = "\n".join(
        [
            str(molecule.natoms),
            comment if comment is not None else molecule.comment,
            molecule.atoms_block,
            "",
        ]
    )
    path.write_text(text, encoding="utf-8")