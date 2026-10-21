$ErrorActionPreference = "Stop"
Write-Host "linkit setup"
py -3.12 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
& .\.venv\Scripts\python.exe -m linkwireless setup
Write-Host "Setup complete. Test with: .\.venv\Scripts\python.exe -m linkwireless status"
