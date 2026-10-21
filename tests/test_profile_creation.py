"""Tests for the WLAN profile XML that connect-wireless generates.

The generated XML has to match what Windows itself writes, otherwise the
profile cannot be added or the pre-shared key cannot be read back later.
"""

import os

import pytest

from linkit import wifi


def _netsh_recorder(monkeypatch, outputs):
    """Record every ``netsh`` call and reply with the queued outputs."""
    calls = []

    def fake_run_netsh(*args):
        calls.append(list(args))
        index = min(len(calls) - 1, len(outputs) - 1)
        return outputs[index]

    monkeypatch.setattr(wifi, "_run_netsh", fake_run_netsh)
    return calls


def test_build_profile_xml_uses_wpa2_for_wpa2_networks():
    xml = wifi._build_profile_xml("LPU Wireless", "123456789a", "WPA2-Personal")

    assert "<authentication>WPA2PSK</authentication>" in xml
    assert "<encryption>AES</encryption>" in xml
    assert "transitionMode" not in xml


def test_build_profile_xml_uses_wpa3_with_transition_mode():
    xml = wifi._build_profile_xml("LPU Wireless", "123456789a", "WPA3-Personal")

    assert "<authentication>WPA3SAE</authentication>" in xml
    assert "<transitionMode" in xml
    assert ">true</transitionMode>" in xml


def test_build_profile_xml_accepts_the_netsh_style_names():
    xml = wifi._build_profile_xml("LPU Wireless", "123456789a", "WPA3SAE")

    assert "<authentication>WPA3SAE</authentication>" in xml


def test_build_profile_xml_contains_the_key_and_the_hex_ssid():
    xml = wifi._build_profile_xml("LPU Wireless", "123456789a", "WPA3-Personal")

    assert "<keyMaterial>123456789a</keyMaterial>" in xml
    assert "<protected>false</protected>" in xml
    assert "<hex>4C505520576972656C657373</hex>" in xml
    assert "<name>LPU Wireless</name>" in xml


def test_build_profile_xml_escapes_special_characters():
    xml = wifi._build_profile_xml("LPU & Co", "a<b>c", "WPA2-Personal")

    assert "<name>LPU &amp; Co</name>" in xml
    assert "<keyMaterial>a&lt;b&gt;c</keyMaterial>" in xml


def test_create_profile_stores_the_profile_for_all_users(monkeypatch):
    calls = _netsh_recorder(monkeypatch, ["Profile LPU Wireless is added on interface Wi-Fi."])

    ok, message = wifi.create_profile("LPU Wireless", "123456789a", "WPA3-Personal")

    assert ok
    assert "is added" in message
    assert calls[0][:3] == ["wlan", "add", "profile"]
    assert calls[0][-1] == "user=all"


def test_create_profile_falls_back_to_the_current_user_scope(monkeypatch):
    calls = _netsh_recorder(
        monkeypatch,
        [
            "The profile could not be added because of permission issues.",
            "Profile LPU Wireless is added on interface Wi-Fi.",
        ],
    )

    ok, message = wifi.create_profile("LPU Wireless", "123456789a")

    assert ok
    assert "is added" in message
    assert [call[-1] for call in calls] == ["user=all", "user=current"]


def test_create_profile_reports_a_failure(monkeypatch):
    _netsh_recorder(monkeypatch, ["The profile could not be added."])

    ok, message = wifi.create_profile("LPU Wireless", "123456789a")

    assert not ok
    assert "could not be added" in message


def test_create_profile_removes_the_temporary_xml_file(monkeypatch):
    seen = {}

    def fake_run_netsh(*args):
        filename = args[3].split("=", 1)[1].strip('"')
        seen["filename"] = filename
        with open(filename, encoding="utf-8") as handle:
            seen["xml"] = handle.read()
        return "Profile LPU Wireless is added on interface Wi-Fi."

    monkeypatch.setattr(wifi, "_run_netsh", fake_run_netsh)

    ok, _ = wifi.create_profile("LPU Wireless", "123456789a")

    assert ok
    assert "<keyMaterial>123456789a</keyMaterial>" in seen["xml"]
    assert not os.path.exists(seen["filename"])


def test_profile_scope_defaults_to_all_users():
    assert wifi.PROFILE_SCOPE == "all"
    assert wifi.FALLBACK_PROFILE_SCOPE == "current"
