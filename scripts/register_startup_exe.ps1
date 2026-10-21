$ErrorActionPreference = "Stop"
$exe = (Resolve-Path ".\dist\connect-wireless.exe").Path
$key = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
Set-ItemProperty -Path $key -Name "linkit" -Value "`"$exe`""
Write-Host "connect-wireless registered to start at Windows sign-in."
