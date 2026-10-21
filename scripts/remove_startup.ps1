$key = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
Remove-ItemProperty -Path $key -Name "linkit" -ErrorAction SilentlyContinue
Write-Host "linkit startup entry removed."
