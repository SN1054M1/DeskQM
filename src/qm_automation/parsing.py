from __future__ import annotations

import re
from pathlib import Path


ATOMIC_SYMBOLS: dict[int, str] = {
    1: "H",
    2: "He",
    3: "Li",
    4: "Be",
    5: "B",
    6: "C",
    7: "N",
    8: "O",
    9: "F",
    10: "Ne",
    11: "Na",
    12: "Mg",
    13: "Al",
    14: "Si",
    15: "P",
    16: "S",
    17: "Cl",
    18: "Ar",
    19: "K",
    20: "Ca",
    21: "Sc",
    22: "Ti",
    23: "V",
    24: "Cr",
    25: "Mn",
    26: "Fe",
    27: "Co",
    28: "Ni",
    29: "Cu",
    30: "Zn",
    31: "Ga",
    32: "Ge",
    33: "As",
    34: "Se",
    35: "Br",
    36: "Kr",
    53: "I",
}


ENERGY_PATTERNS: dict[str, re.Pattern[str]] = {
    "orca": re.compile(r"FINAL SINGLE POINT ENERGY\s+(-?\d+\.\d+)", re.IGNORECASE),
    "gaussian": re.compile(r"SCF Done:\s+E\([^)]+\)\s+=\s+(-?\d+\.\d+)", re.IGNORECASE),
    "xtb": re.compile(r"TOTAL ENERGY\s+(-?\d+\.\d+)", re.IGNORECASE),
}


def _read_output_text(stdout_file: Path, stderr_file: Path) -> str:
    chunks: list[str] = []
    if stdout_file.exists():
        chunks.append(stdout_file.read_text(encoding="utf-8-sig", errors="ignore"))
    if stderr_file.exists():
        chunks.append(stderr_file.read_text(encoding="utf-8-sig", errors="ignore"))
    return "\n".join(chunks)


def extract_energy_hartree(engine: str, stdout_file: Path, stderr_file: Path) -> float | None:
    pattern = ENERGY_PATTERNS.get(engine)
    if pattern is None:
        return None

    text = _read_output_text(stdout_file, stderr_file)
    if not text:
        return None

    matches = pattern.findall(text)
    if not matches:
        return None
    return float(matches[-1])


def extract_energy_series(engine: str, stdout_file: Path, stderr_file: Path) -> list[float]:
    pattern = ENERGY_PATTERNS.get(engine)
    if pattern is None:
        return []
    text = _read_output_text(stdout_file, stderr_file)
    if not text:
        return []
    matches = pattern.findall(text)
    return [float(match) for match in matches]


def extract_gaussian_final_xyz(stdout_file: Path, stderr_file: Path, output_file: Path, title: str) -> Path | None:
    text = _read_output_text(stdout_file, stderr_file)
    if not text:
        return None

    lines = text.splitlines()
    latest_block: list[str] = []
    index = 0
    while index < len(lines):
        if lines[index].strip().lower().startswith("standard orientation:"):
            index += 1
            while index < len(lines) and not lines[index].strip().startswith("---"):
                index += 1
            if index >= len(lines):
                break
            index += 1
            for _ in range(3):
                if index < len(lines):
                    index += 1

            block: list[str] = []
            while index < len(lines) and not lines[index].strip().startswith("---"):
                block.append(lines[index])
                index += 1
            if block:
                latest_block = block
            continue
        index += 1

    if not latest_block:
        return None

    xyz_lines: list[str] = []
    for row in latest_block:
        parts = row.split()
        if len(parts) < 6:
            continue
        atomic_number = int(parts[1])
        symbol = ATOMIC_SYMBOLS.get(atomic_number)
        if symbol is None:
            return None
        xyz_lines.append(f"{symbol} {parts[3]} {parts[4]} {parts[5]}")

    if not xyz_lines:
        return None

    output_file.write_text(
        "\n".join(
            [
                str(len(xyz_lines)),
                title,
                *xyz_lines,
                "",
            ]
        ),
        encoding="utf-8",
    )
    return output_file