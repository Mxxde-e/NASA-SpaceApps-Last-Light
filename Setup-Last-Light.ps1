param([string]$Python = 'python')
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) {
  & $Python -c "import sys; assert sys.version_info >= (3,12), 'Python 3.12 or newer is required'"
  if ($LASTEXITCODE -ne 0) { throw 'Install Python 3.12+ or provide -Python with its executable path.' }
  & $Python -m venv .venv
  if ($LASTEXITCODE -ne 0) { throw 'Could not create the Python environment.' }
}
& .\.venv\Scripts\python.exe -m pip install -r backend\requirements.lock.txt
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
& .\.venv\Scripts\python.exe -m backend.acquire
if ($LASTEXITCODE -ne 0) { throw 'NASA data acquisition or verification failed.' }
Write-Host 'Ready. Double-click Start-Last-Light.cmd to open the local app.'
