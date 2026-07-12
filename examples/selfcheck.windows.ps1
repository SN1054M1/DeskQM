param(
	[string]$ConfigFile = "",
	[string]$XyzFile = "",
	[switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
if (-not $XyzFile) {
	$XyzFile = Join-Path $PSScriptRoot "methanol.xyz"
}

function Invoke-SelfCheckCommand {
	param(
		[string[]]$CommandArgs
	)
	$commandArgs = @($CommandArgs)
	if ($DryRun) {
		$commandArgs += "--dry-run"
	}
	if ($ConfigFile) {
		$commandArgs += @("--config-file", $ConfigFile)
	}
	$process = Start-Process -FilePath "python" -ArgumentList $commandArgs -NoNewWindow -Wait -PassThru
	if ($process.ExitCode -ne 0) {
		throw "Self-check command failed with exit code $($process.ExitCode): python $($commandArgs -join ' ')"
	}
}

Push-Location $RepoRoot
try {
	Write-Host "Running spectroscopy self-check from $RepoRoot"
	if ($DryRun) {
		Write-Host "Dry-run mode is enabled. External QM executables will not be launched."
	}

	Invoke-SelfCheckCommand -CommandArgs @("scripts\uvvis.py", $XyzFile, "--engine", "gaussian", "--nstates", "20", "--solvent", "acetonitrile")
	Invoke-SelfCheckCommand -CommandArgs @("scripts\nmr.py", $XyzFile, "--engine", "orca", "--solvent", "chloroform")
	Invoke-SelfCheckCommand -CommandArgs @("scripts\ir.py", $XyzFile, "--engine", "gaussian", "--solvent", "water")
	Invoke-SelfCheckCommand -CommandArgs @("scripts\vcd.py", $XyzFile, "--engine", "orca", "--preset", "hybrid", "--solvent", "methanol")
	Invoke-SelfCheckCommand -CommandArgs @("scripts\nearir.py", $XyzFile, "--engine", "orca", "--solvent", "ccl4", "--delq", "0.1")

	Write-Host "Self-check commands finished. Review runs/*/logs and each results/run_metadata.json file."
}
finally {
	Pop-Location
}