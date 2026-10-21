from __future__ import annotations
import subprocess
import sys
import re

def _run_netsh(*args: str) -> str:
    if sys.platform != "win32":
        raise RuntimeError("linkit Wi-Fi controls currently require Windows.")
    result = subprocess.run(
        ["netsh", *args], capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=20, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
    )
    return (result.stdout or "") + "\n" + (result.stderr or "")

def current_ssid() -> str | None:
    output = _run_netsh("wlan", "show", "interfaces")
    # Output is localized on some Windows installations; this parser targets English output.
    for line in output.splitlines():
        if re.match(r"^\s*SSID\s*:", line) and "BSSID" not in line:
            value = line.split(":", 1)[1].strip()
            return value or None
    return None

def visible_ssids() -> list[str]:
    output = _run_netsh("wlan", "show", "networks", "mode=bssid")
    found = []
    for line in output.splitlines():
        match = re.match(r"^\s*SSID\s+\d+\s*:\s*(.*)$", line)
        if match:
            name = match.group(1).strip()
            if name and name not in found:
                found.append(name)
    return found

def connect_using_saved_profile(ssid: str) -> tuple[bool, str]:
    # Windows usually uses the SSID as the profile name, but this is not guaranteed.
    output = _run_netsh("wlan", "connect", f"name={ssid}", f"ssid={ssid}")
    ok = "completed successfully" in output.lower() or "already in progress" in output.lower()
    return ok, output.strip()

def is_visible(ssid: str) -> bool:
    return ssid.casefold() in {item.casefold() for item in visible_ssids()}
