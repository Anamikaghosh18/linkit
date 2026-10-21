from __future__ import annotations
import getpass
import sys

# The credential entry keeps its historic service name so that existing
# installations keep working after the rename to connect-wireless.
SERVICE = "linkit.LPU24Online"

def _keyring():
    try:
        import keyring
        import keyring.errors  # ensures keyring.errors is always available
        return keyring
    except ImportError as exc:
        raise RuntimeError("Missing dependency. Run: pip install -r requirements.txt") from exc

def save_credentials(username: str, password: str) -> None:
    kr = _keyring()
    kr.set_password(SERVICE, "username", username)
    kr.set_password(SERVICE, "password", password)

def get_credentials():
    kr = _keyring()
    return kr.get_password(SERVICE, "username"), kr.get_password(SERVICE, "password")

def clear_credentials() -> None:
    kr = _keyring()
    for name in ("username", "password"):
        try:
            kr.delete_password(SERVICE, name)
        except kr.errors.PasswordDeleteError:
            pass

def prompt_and_save() -> None:
    if not sys.stdin.isatty():
        raise RuntimeError("First-time setup needs an interactive PowerShell/terminal window.")
    username = input("LPU portal username: ").strip()
    if not username:
        raise ValueError("Username cannot be empty.")
    password = getpass.getpass("LPU portal password (input hidden): ")
    if not password:
        raise ValueError("Password cannot be empty.")
    save_credentials(username, password)
    print("Credentials saved to Windows Credential Manager.")
