from __future__ import annotations
import sys
from pathlib import Path

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "linkit"

def _winreg():
    if sys.platform != "win32":
        raise RuntimeError("Windows startup registration is only supported on Windows.")
    import winreg
    return winreg

def _command() -> str:
    # For frozen EXE, just run the executable
    if getattr(sys, "frozen", False):
        return f'"{Path(sys.executable)}"'
    # For source mode, use pythonw to avoid console window
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    exe = pythonw if pythonw.exists() else Path(sys.executable)
    return f'"{exe}" -m linkwireless'

def install_startup() -> None:
    winreg = _winreg()
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, VALUE_NAME, 0, winreg.REG_SZ, _command())

def uninstall_startup() -> None:
    winreg = _winreg()
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        try:
            winreg.DeleteValue(key, VALUE_NAME)
        except FileNotFoundError:
            pass
