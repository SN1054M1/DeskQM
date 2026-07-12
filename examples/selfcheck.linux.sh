#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
CONFIG_FILE="${1:-}"
XYZ_FILE="${2:-$SCRIPT_DIR/methanol.xyz}"
DRY_RUN="${DRY_RUN:-0}"

run_selfcheck() {
	local args=("$@")
	if [[ -n "$CONFIG_FILE" ]]; then
		args+=(--config-file "$CONFIG_FILE")
	fi
	if [[ "$DRY_RUN" == "1" ]]; then
		args+=(--dry-run)
	fi
	python3 "${args[@]}"
}

cd "$REPO_ROOT"
echo "Running spectroscopy self-check from $REPO_ROOT"
if [[ "$DRY_RUN" == "1" ]]; then
	echo "Dry-run mode is enabled. External QM executables will not be launched."
fi

run_selfcheck scripts/uvvis.py "$XYZ_FILE" --engine gaussian --nstates 20 --solvent acetonitrile
run_selfcheck scripts/nmr.py "$XYZ_FILE" --engine orca --solvent chloroform
run_selfcheck scripts/ir.py "$XYZ_FILE" --engine gaussian --solvent water
run_selfcheck scripts/vcd.py "$XYZ_FILE" --engine orca --preset hybrid --solvent methanol
run_selfcheck scripts/nearir.py "$XYZ_FILE" --engine orca --solvent ccl4 --delq 0.1

echo "Self-check commands finished. Review runs/*/logs and each results/run_metadata.json file."