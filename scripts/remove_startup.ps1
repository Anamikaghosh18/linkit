$key = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
Remove-ItemProperty -Path $key -Name "linkit" -ErrorAction SilentlyContinue
Write-Host "connect-wireless startup entry removed."
