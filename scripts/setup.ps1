param()

if (-not (Get-Command make -ErrorAction SilentlyContinue)) {
  Write-Error 'make is required to run this script. Install it via Chocolatey (choco install make) or Git for Windows.'
  exit 1
}

make setup
