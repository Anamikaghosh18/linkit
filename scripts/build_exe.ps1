$ErrorActionPreference = "Stop"
if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
  Write-Error "Virtual environment not found. Run scripts\setup.ps1 first."
}
& .\.venv\Scripts\python.exe -m pip install pyinstaller
& .\.venv\Scripts\pyinstaller.exe --noconfirm --clean --onefile --noconsole --name linkit --collect-all keyring --collect-all pystray --collect-all Pillow linkit_cli.py
Write-Host "Built EXE: .\dist\linkit.exe"
Write-Host "Keep the EXE in a permanent folder before registering startup."
