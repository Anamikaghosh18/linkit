# linkit

**Automatically connect to your campus Wi-Fi network**

linkit is a lightweight Windows application that automatically detects and connects to your campus Wi-Fi network when it's in range. Simply enter your credentials once, and linkit handles the rest - running silently in the background and keeping you connected.

## Features

- **One-time setup** - Enter your credentials once through a simple interface
- **Auto-connect** - Automatically connects when the network is in range
- **Background operation** - Runs silently in your system tray
- **Windows startup** - Starts automatically when you sign in to Windows
- **Secure storage** - Credentials stored securely in Windows Credential Manager
- **Easy reset** - Change your credentials anytime through the settings menu

## Download & Install

1. Download the latest version from the [Releases page](https://github.com/Anamikaghosh18/linkit/releases)
2. Run `linkit.exe`
3. Follow the on-screen setup wizard:
   - Enter your Wi-Fi network name (SSID)
   - Enter your portal username
   - Enter your portal password
   - Click "Continue"

That's it! linkit will now:
- Start automatically with Windows
- Run in the background (check your system tray)
- Auto-connect when the network is available

## System Requirements

- Windows 10 or 11
- Wi-Fi adapter enabled
- Valid campus Wi-Fi access
- Your campus network credentials

## How to Use

### First Run
When you first run linkit, a setup window will appear asking for:
- **Wi-Fi Network Name (SSID)** - The name of your campus network
- **Portal Username** - Your campus network username
- **Portal Password** - Your campus network password

Click "Continue" to save your settings. linkit will then start automatically.

### Changing Settings
To change your credentials or network settings:
1. Right-click the linkit icon in your system tray
2. Select "Open Settings"
3. Update your information
4. Click "Continue" to save

### Reset Configuration
To clear all saved credentials:
1. Right-click the linkit icon in your system tray
2. Select "Open Settings"
3. Click "Reset" to clear all settings
4. Re-enter your credentials

### Uninstall
To remove linkit:
1. Right-click the system tray icon
2. Select "Quit"
3. Delete the `linkit.exe` file

## Privacy & Security

- Your credentials are stored in Windows Credential Manager using industry-standard encryption
- Credentials are never written to plain text files
- Only you can access your stored credentials
- linkit does not collect or transmit any personal data
- The application runs entirely on your local computer

## Troubleshooting

**linkit doesn't auto-connect**
- Ensure the Wi-Fi network name (SSID) is entered correctly
- Check that your credentials are valid
- Make sure the network is in range

**Can't find the system tray icon**
- Check the hidden icons area in your taskbar
- Run linkit.exe again to restart the application

**Need to re-enter credentials**
- Right-click the system tray icon
- Select "Open Settings"
- Click "Reset" and re-enter your information

## Support

For issues or questions, please visit the [GitHub repository](https://github.com/Anamikaghosh18/linkit/issues).

## License

This project is licensed under the terms specified in the [LICENSE](LICENSE) file.

---

## For Developers

To build from source for development purposes:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m linkwireless
```

To build the EXE locally:

```powershell
pip install pyinstaller
pyinstaller --noconfirm --clean --onefile --noconsole --name linkit --collect-all keyring --collect-all pystray --collect-all Pillow linkwireless_cli.py
```

