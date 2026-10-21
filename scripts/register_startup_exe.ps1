$ErrorActionPreference = "Stop"
$exe = (Resolve-Path ".\dist\linkit.exe").Path
$key = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
Set-ItemProperty -Path $key -Name "linkit" -Value "`"$exe`""
Write-Host "linkit registered to start at Windows sign-in."
