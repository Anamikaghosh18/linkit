from __future__ import annotations
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path


def _run_netsh(*args: str) -> str:
    if sys.platform != "win32":
        raise RuntimeError("connect-wireless Wi-Fi controls currently require Windows.")
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

def _parse_visible_networks(output: str) -> list[dict]:
    """Parse the text output of ``netsh wlan show networks mode=bssid``.

    Kept separate from the netsh call so it can be unit tested without Windows.
    """
    networks: list[dict] = []
    current: dict | None = None
    for raw in output.splitlines():
        line = raw.rstrip()
        match = re.match(r"^\s*SSID\s+\d+\s*:\s*(.*)$", line)
        if match:
            name = match.group(1).strip()
            if not name:
                current = None
                continue
            current = _merge_network(networks, name)
            continue
        if current is None:
            continue
        auth_match = re.match(r"^\s*Authentication\s*:\s*(.*)$", line)
        if auth_match:
            auth = auth_match.group(1).strip()
            if auth and not current["auth"]:
                current["auth"] = auth
            continue
        signal_match = re.match(r"^\s*Signal\s*:\s*(\d+)\s*%", line)
        if signal_match:
            signal = int(signal_match.group(1))
            if current["signal"] is None or signal > current["signal"]:
                current["signal"] = signal
            continue
        channel_match = re.match(r"^\s*Channel\s*:\s*(\d+)", line)
        if channel_match:
            channel = int(channel_match.group(1))
            if current["channel"] is None:
                current["channel"] = channel
    return networks


def _merge_network(networks: list[dict], name: str) -> dict:
    """Return the entry for ``name``, creating it when the SSID is new."""
    for network in networks:
        if network["ssid"] == name:
            return network
    network = {"ssid": name, "signal": None, "auth": "", "channel": None}
    networks.append(network)
    return network


def visible_networks() -> list[dict]:
    """Return the visible Wi-Fi networks as dicts.

    Each dict has the keys ``ssid``, ``signal`` (0-100 or None), ``auth`` and
    ``channel``. The parser targets the English output of
    ``netsh wlan show networks mode=bssid``.
    """
    output = _run_netsh("wlan", "show", "networks", "mode=bssid")
    return _parse_visible_networks(output)


def visible_ssids() -> list[str]:
    found: list[str] = []
    for network in visible_networks():
        name = network["ssid"]
        if name and name not in found:
            found.append(name)
    return found


def saved_profiles() -> list[str]:
    """Return the names of the Wi-Fi profiles saved for the current user."""
    output = _run_netsh("wlan", "show", "profiles")
    profiles: list[str] = []
    for line in output.splitlines():
        match = re.match(
            r"^\s*(?:All User Profile|Current User Profile)\s*:\s*(.*)$", line
        )
        if match:
            name = match.group(1).strip()
            if name and name != "<None>" and name not in profiles:
                profiles.append(name)
    return profiles


def connect_to_ssid(ssid: str) -> tuple[bool, str]:
    """Ask Windows to join a network directly by SSID.

    This works for open networks that have no saved profile. Secured networks
    need :func:`connect_using_saved_profile` because Windows needs the key.
    """
    output = _run_netsh("wlan", "connect", f"ssid={ssid}")
    lowered = output.lower()
    ok = (
        "completed successfully" in lowered
        or "request completed" in lowered
        or "already in progress" in lowered
        or "connection request" in lowered
    )
    return ok, output.strip()


def connect_using_saved_profile(profile: str, ssid: str | None = None) -> tuple[bool, str]:
    """Ask Windows to join a network using a saved profile.

    ``profile`` is the name of the saved profile. ``ssid`` is only supplied
    when the profile name differs from the SSID it connects to.
    """
    args = ["wlan", "connect", f"name={profile}"]
    if ssid and ssid.casefold() != profile.casefold():
        args.append(f"ssid={ssid}")
    output = _run_netsh(*args)
    lowered = output.lower()
    ok = (
        "completed successfully" in lowered
        or "request completed" in lowered
        or "already in progress" in lowered
        or "connection request" in lowered
    )
    return ok, output.strip()

def is_visible(ssid: str) -> bool:
    return ssid.casefold() in {item.casefold() for item in visible_ssids()}


def _parse_profile_key(output: str) -> str | None:
    """Extract the pre-shared key from ``netsh wlan show profile`` output.

    Two formats are produced by Windows depending on the driver/locale:

    * text  -> ``Key Content            : 123456789a``
    * XML   -> ``<keyMaterial>123456789a</keyMaterial>``
    """
    match = re.search(r"<keyMaterial>(.*?)</keyMaterial>", output, re.IGNORECASE | re.DOTALL)
    if match:
        key = match.group(1).strip()
        return key or None
    match = re.search(r"^\s*Key\s+Content\s*:\s*(.*)$", output, re.IGNORECASE | re.MULTILINE)
    if match:
        key = match.group(1).strip().strip('"')
        return key or None
    return None


def _parse_profile_ssid(output: str) -> str | None:
    """Extract the SSID a saved profile refers to.

    Handles both the XML export (``<name>`` inside ``<SSIDConfig>``) and the
    text output (``SSID name : "LPU Wireless"``).
    """
    match = re.search(r"<SSIDConfig>(.*?)</SSIDConfig>", output, re.IGNORECASE | re.DOTALL)
    if match:
        name_match = re.search(r"<name>(.*?)</name>", match.group(1), re.IGNORECASE | re.DOTALL)
        if name_match:
            name = name_match.group(1).strip()
            if name:
                return name
    match = re.search(r"^\s*SSID\s+name\s*:\s*(.*)$", output, re.IGNORECASE | re.MULTILINE)
    if match:
        name = match.group(1).strip().strip('"')
        if name:
            return name
    return None


def profile_key(profile: str) -> str | None:
    """Return the pre-shared key stored in a saved Wi-Fi profile.

    ``netsh wlan show profile ... key=clear`` exposes the plain-text key to the
    owner of the profile, which lets connect-wireless reuse an existing campus
    key for other campus SSIDs without asking the user for it.
    """
    output = _run_netsh("wlan", "show", "profile", f'name={profile}', "key=clear")
    return _parse_profile_key(output)


def profile_ssid(profile: str) -> str | None:
    """Return the SSID a saved Wi-Fi profile refers to."""
    output = _run_netsh("wlan", "show", "profile", f'name={profile}')
    return _parse_profile_ssid(output)


def profile_authentication(profile: str) -> str | None:
    """Return the authentication mode of a saved profile.

    Windows lists several modes for transitional networks (for example
    ``WPA3-Personal`` and ``WPA2-Personal``); the first one is returned.
    """
    output = _run_netsh("wlan", "show", "profile", f'name={profile}')
    match = re.search(
        r"^\s*Authentication\s*:\s*(.+)$", output, re.IGNORECASE | re.MULTILINE
    )
    if match:
        value = match.group(1).strip()
        return value or None
    match = re.search(
        r"<authentication>(.*?)</authentication>", output, re.IGNORECASE | re.DOTALL
    )
    if match:
        value = match.group(1).strip()
        return value or None
    return None


#: Profile scope used when creating new Wi-Fi profiles.
#:
#: ``all`` stores the profile for every user on the machine, which keeps the
#: pre-shared key readable through ``netsh wlan show profile ... key=clear``.
#: A ``current``-scoped profile hides its key, so connect-wireless could never
#: reuse a key it had created itself. ``all`` does not require administrator rights.
PROFILE_SCOPE = "all"

#: The scope used when the preferred one is rejected by Windows.
FALLBACK_PROFILE_SCOPE = "current"


def create_profile(
    ssid: str, key: str, authentication: str = "WPA2PSK"
) -> tuple[bool, str]:
    """Create a WPA2/WPA3 personal profile for ``ssid`` using ``key``.

    Adding a Wi-Fi profile does not require administrator rights, so
    connect-wireless can bootstrap profiles for campus networks the user has
    never joined before.
    ``authentication`` allows the caller to match the security mode of the
    campus network (``WPA2PSK`` or ``WPA3SAE``).

    The profile is stored with :data:`PROFILE_SCOPE` scope so that the key
    stays readable and connect-wireless can reuse it for other campus SSIDs. If
    Windows rejects that scope the user-scoped variant is tried instead.
    """
    xml = _build_profile_xml(ssid, key, authentication)
    output = ""
    for scope in (PROFILE_SCOPE, FALLBACK_PROFILE_SCOPE):
        output = _add_profile_xml(xml, scope)
        if _profile_added(output):
            return True, output.strip()
    return False, output.strip()


#: Markers that show ``netsh`` refused to store the profile.
PROFILE_ERROR_MARKERS = (
    "could not be added",
    "not added",
    "failed",
    "error",
    "denied",
)


def _profile_added(output: str) -> bool:
    """Return True when ``netsh`` reports that the profile was added.

    The wording of a successful run is ``Profile <name> is added on interface
    <name>.`` while a rejection reads ``The profile could not be added ...``,
    so the error markers are checked first.
    """
    lowered = output.lower()
    if any(marker in lowered for marker in PROFILE_ERROR_MARKERS):
        return False
    return "added" in lowered and "profile" in lowered


def _build_profile_xml(ssid: str, key: str, authentication: str) -> str:
    """Return the WLAN profile XML for ``ssid``/``key``.

    WPA3 networks are created in transition mode, which mirrors the campus
    profiles exported by Windows and keeps the network reachable by WPA2
    clients as well.
    """
    auth = (authentication or "WPA2PSK").strip().upper()
    if auth in {"WPA3-SAE", "WPA3SAE", "WPA3-PERSONAL", "WPA3PERSONAL"}:
        auth_xml = "WPA3SAE"
        encryption = "AES"
        transition = (
            '                <transitionMode xmlns="http://www.microsoft.com'
            '/networking/WLAN/profile/v4">true</transitionMode>\n'
        )
    elif auth in {"WPA2PSK", "WPA2-PERSONAL", "WPA2PERSONAL"}:
        auth_xml = "WPA2PSK"
        encryption = "AES"
        transition = ""
    else:
        auth_xml = auth
        encryption = "AES"
        transition = ""

    return f"""<?xml version="1.0"?>
<WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1">
    <name>{_xml_escape(ssid)}</name>
    <SSIDConfig>
        <SSID>
            <hex>{_hex_ssid(ssid)}</hex>
            <name>{_xml_escape(ssid)}</name>
        </SSID>
    </SSIDConfig>
    <connectionType>ESS</connectionType>
    <connectionMode>manual</connectionMode>
    <MSM>
        <security>
            <authEncryption>
                <authentication>{_xml_escape(auth_xml)}</authentication>
                <encryption>{_xml_escape(encryption)}</encryption>
                <useOneX>false</useOneX>
{transition}            </authEncryption>
            <sharedKey>
                <keyType>passPhrase</keyType>
                <protected>false</protected>
                <keyMaterial>{_xml_escape(key)}</keyMaterial>
            </sharedKey>
        </security>
    </MSM>
</WLANProfile>
"""


def _add_profile_xml(xml: str, scope: str) -> str:
    """Write ``xml`` to a temporary file and hand it to ``netsh``."""
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", suffix=".xml", delete=False, encoding="utf-8"
        ) as handle:
            handle.write(xml)
            temp_path = handle.name
        return _run_netsh(
            "wlan", "add", "profile", f'filename="{temp_path}"', f"user={scope}"
        )
    finally:
        if temp_path:
            try:
                os.unlink(temp_path)
            except OSError:
                pass


def _hex_ssid(ssid: str) -> str:
    """Return the hex encoding of an SSID as used in WLAN profiles."""
    return ssid.encode("utf-8").hex().upper()


def _xml_escape(value: str) -> str:
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
