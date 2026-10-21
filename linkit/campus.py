"""Automatic campus Wi-Fi discovery and connection.

connect-wireless no longer asks the user for an SSID. Instead it scans the
networks that are currently in range, recognises the university networks, and
joins the strongest one it can.

Campus networks are not guaranteed to share a single pre-shared key, so the
module works in three steps:

1. Prefer a saved Windows profile whose SSID matches a visible campus network.
2. Otherwise reuse the key of an existing campus profile to create a new one
   (creating a user-scoped profile does not need administrator rights).
3. Otherwise report that no usable campus network was found.

Every ``netsh`` call is comparatively slow, so the saved-profile snapshot and
the campus key are cached for a short while.
"""

from __future__ import annotations

import re
import time

from . import wifi
from .config import DEFAULT_CAMPUS_PATTERNS, load_config

#: Network name fragments that identify a university campus network.
CAMPUS_SSID_PATTERNS = DEFAULT_CAMPUS_PATTERNS

#: Authentication modes that indicate a secured network we can join with a key.
SECURED_AUTH_MODES = ("WPA2-Personal", "WPA3-Personal", "WPA2PSK", "WPA3PSK")

#: How long the saved-profile snapshot and the campus key stay cached (seconds).
CACHE_TTL = 60.0

_cache: dict = {}


def _cached(key: str, builder):
    """Return ``builder()`` cached under ``key`` for ``CACHE_TTL`` seconds."""
    now = time.monotonic()
    entry = _cache.get(key)
    if entry and now - entry["time"] < CACHE_TTL:
        return entry["value"]
    value = builder()
    _cache[key] = {"time": now, "value": value}
    return value


def invalidate_cache() -> None:
    """Drop the cached profile snapshot (used after creating a profile)."""
    _cache.clear()


def is_campus_ssid(ssid: str, patterns: tuple[str, ...] | list[str] | None = None) -> bool:
    """Return True when ``ssid`` looks like a campus network."""
    if not ssid:
        return False
    text = ssid.strip()
    for pattern in _active_patterns(patterns):
        try:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        except re.error:
            continue
    return False


def _active_patterns(patterns: tuple[str, ...] | list[str] | None = None) -> list[str]:
    """Return the configured campus patterns plus the built-in defaults."""
    active = list(CAMPUS_SSID_PATTERNS)
    if patterns is None:
        patterns = _cached("patterns", _configured_patterns)
    for pattern in patterns or []:
        if isinstance(pattern, str) and pattern not in active:
            active.append(pattern)
    return active


def _configured_patterns() -> list[str]:
    try:
        return list(load_config().get("campus_patterns") or [])
    except Exception:
        return []


def discover_campus_networks() -> list[dict]:
    """Return the visible campus networks, strongest signal first."""
    candidates = [
        network for network in wifi.visible_networks() if is_campus_ssid(network["ssid"])
    ]
    return _sort_by_signal(candidates)


def _sort_by_signal(networks: list[dict]) -> list[dict]:
    def key(network: dict) -> tuple[int, str]:
        signal = network.get("signal")
        return (-(signal if signal is not None else -1), network["ssid"].casefold())

    return sorted(networks, key=key)


def needs_psk(network: dict) -> bool:
    """Return True when the network is a personal (PSK) secured network.

    Enterprise networks use certificates and cannot be joined with a shared
    key, so connect-wireless only creates profiles for personal networks.
    """
    auth = (network.get("auth") or "").strip().lower()
    if not auth:
        return False
    if "open" in auth or "none" in auth:
        return False
    if "enterprise" in auth or "802.1x" in auth:
        return False
    return any(mode.lower() in auth for mode in SECURED_AUTH_MODES) or "wpa" in auth


def is_open(network: dict) -> bool:
    """Return True when the network does not require a key."""
    auth = (network.get("auth") or "").strip().lower()
    if not auth:
        return False
    return "open" in auth or "none" in auth


def profile_index() -> dict[str, str]:
    """Return a mapping of saved profile name to the SSID it connects to."""
    return _cached("profiles", _build_profile_index)


def _build_profile_index() -> dict[str, str]:
    index: dict[str, str] = {}
    for profile in wifi.saved_profiles():
        try:
            ssid = wifi.profile_ssid(profile)
        except Exception:
            ssid = None
        index[profile] = ssid or profile
    return index


def saved_campus_profiles() -> list[str]:
    """Return the saved Windows profiles that belong to campus networks."""
    return [
        profile
        for profile, ssid in profile_index().items()
        if is_campus_ssid(ssid)
    ]


def find_campus_key(preferred_ssids: list[str] | None = None) -> tuple[str | None, str | None]:
    """Return ``(key, source_profile)`` taken from an existing campus profile.

    Campus buildings usually share one pre-shared key, so the key that is used
    by the largest number of campus profiles wins. Profiles pointing at the
    networks that are currently visible are preferred over the rest, because
    their key is the most likely to work for the networks we want to join.
    """
    profiles = saved_campus_profiles()
    if not profiles:
        return None, None

    index = profile_index()
    if preferred_ssids:
        wanted = {ssid.casefold() for ssid in preferred_ssids}
        visible_first = [p for p in profiles if index.get(p, "").casefold() in wanted]
        profiles = visible_first + [p for p in profiles if p not in visible_first]

    keys: dict[str, list[str]] = {}
    for profile in profiles:
        try:
            key = wifi.profile_key(profile)
        except Exception:
            key = None
        if key:
            keys.setdefault(key, []).append(profile)

    if not keys:
        return None, None

    # Most widely used key first; ties are broken by the first profile found.
    best_key = max(keys, key=lambda item: len(keys[item]))
    return best_key, keys[best_key][0]


def profile_for(ssid: str) -> str | None:
    """Return a saved profile that connects to ``ssid``, if one exists."""
    target = ssid.casefold()
    for profile, profile_ssid in profile_index().items():
        if profile_ssid.casefold() == target:
            return profile
    return None


def ensure_profile(
    ssid: str, key: str | None = None, authentication: str | None = None
) -> tuple[bool, str]:
    """Make sure a usable profile exists for ``ssid``.

    Returns ``(ok, message)``. When no profile exists and no key is available
    the call fails with an explanatory message instead of guessing a password.
    ``authentication`` optionally mirrors the security mode of the campus
    network (for example ``WPA3-Personal``).
    """
    existing = profile_for(ssid)
    if existing:
        return True, f"Using saved profile '{existing}'."

    if not key:
        return False, (
            f"No saved Wi-Fi profile for '{ssid}' and no campus key is available "
            "to create one."
        )

    ok, message = wifi.create_profile(ssid, key, authentication or "WPA2PSK")
    invalidate_cache()
    if ok:
        return True, f"Created a Wi-Fi profile for '{ssid}'."
    return False, f"Could not create a profile for '{ssid}': {message}"


def connect_to_campus() -> tuple[bool, str]:
    """Discover and join the best available campus network.

    Returns ``(ok, message)`` where ``ok`` is True when a connection attempt
    was successfully started.
    """
    networks = discover_campus_networks()
    if not networks:
        return False, "No campus Wi-Fi network is currently in range."

    visible_ssids = [network["ssid"] for network in networks]
    key, source = find_campus_key(visible_ssids)

    for network in networks:
        ssid = network["ssid"]
        profile = profile_for(ssid)

        if profile is None and is_open(network):
            # Open networks can be joined without a saved profile.
            ok, message = wifi.connect_to_ssid(ssid)
            if ok:
                return True, f"Connecting to open network '{ssid}'."
            print(f"Could not connect to '{ssid}': {message}")
            continue

        if profile is None:
            if not key or not needs_psk(network):
                continue
            created, message = ensure_profile(ssid, key, network.get("auth"))
            if not created:
                print(message)
                continue
            profile = profile_for(ssid) or ssid

        ok, message = wifi.connect_using_saved_profile(profile, ssid)
        if ok:
            detail = f" (profile '{profile}')"
            if source and key:
                detail += f", key reused from '{source}'"
            return True, f"Connecting to '{ssid}'{detail}."
        print(f"Could not connect to '{ssid}': {message}")

    return False, "None of the visible campus networks could be joined."
