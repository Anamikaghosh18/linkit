"""Tests for the Windows ``netsh`` output parsers.

The parsers are pure functions so they can be checked on any platform without
touching the machine's wireless stack.
"""

import pytest

from linkit import wifi


VISIBLE_NETWORKS_OUTPUT = """Interface name : Wi-Fi
There are 2 networks currently visible.

SSID 1 : LPU Wireless
    Network type            : Infrastructure
    Authentication          : WPA3-Personal
    Encryption              : GCMP-256
    BSSID 1                 : 44:95:3b:b9:a2:d0
         Signal             : 83%
         Radio type         : 802.11ax
         Band               : 2.4 GHz
         Channel            : 5
         Basic rates (Mbps) : 1 2 5.5 11

SSID 2 : Campus Guest
    Network type            : Infrastructure
    Authentication          : Open
    Encryption              : None
    BSSID 1                 : aa:bb:cc:dd:ee:ff
         Signal             : 45%
         Radio type         : 802.11n
         Channel            : 11
"""

PROFILE_TEXT_OUTPUT = """Profile LPU Wireless on interface Wi-Fi:
=======================================================================

Applied: All User Profile

Profile information
-------------------
    Version                : 1
    Type                   : Wireless LAN
    Name                   : LPU Wireless

Connectivity settings
---------------------
    Number of SSIDs        : 1
    SSID name              : "LPU Wireless"
    Network type           : Infrastructure

Security settings
-----------------
    Authentication         : WPA3-Personal
    Cipher                 : GCMP-256
    Security key           : Present
    Key Content            : 123456789a
"""

PROFILE_XML_OUTPUT = """<?xml version="1.0" encoding="UTF-8"?>
<WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1">
    <name>LPU Wireless</name>
    <SSIDConfig>
        <SSID>
            <hex>4C505520576972656C657373</hex>
            <name>LPU Wireless</name>
        </SSID>
    </SSIDConfig>
    <connectionType>ESS</connectionType>
    <MSM>
        <security>
            <authEncryption>
                <authentication>WPA2PSK</authentication>
                <encryption>AES</encryption>
            </authEncryption>
            <sharedKey>
                <keyType>passPhrase</keyType>
                <keyMaterial>secretkey</keyMaterial>
            </sharedKey>
        </security>
    </MSM>
</WLANProfile>
"""


def test_parse_visible_networks_reads_ssid_auth_signal_and_channel():
    networks = wifi._parse_visible_networks(VISIBLE_NETWORKS_OUTPUT)

    assert [network["ssid"] for network in networks] == ["LPU Wireless", "Campus Guest"]

    first = networks[0]
    assert first["auth"] == "WPA3-Personal"
    assert first["signal"] == 83
    assert first["channel"] == 5

    second = networks[1]
    assert second["auth"] == "Open"
    assert second["signal"] == 45
    assert second["channel"] == 11


def test_parse_visible_networks_keeps_the_strongest_signal_for_duplicate_ssids():
    output = """SSID 1 : LPU Wireless
    Authentication          : WPA3-Personal
         Signal             : 40%
         Channel            : 6

SSID 2 : LPU Wireless
    Authentication          : WPA3-Personal
         Signal             : 91%
         Channel            : 11
"""
    networks = wifi._parse_visible_networks(output)

    assert len(networks) == 1
    assert networks[0]["signal"] == 91
    assert networks[0]["channel"] == 6


def test_parse_visible_networks_ignores_empty_ssid_entries():
    output = """SSID 1 :
    Authentication          : Open

SSID 2 : LPU Wireless
    Authentication          : WPA3-Personal
         Signal             : 70%
"""
    networks = wifi._parse_visible_networks(output)

    assert [network["ssid"] for network in networks] == ["LPU Wireless"]


def test_parse_visible_networks_returns_empty_list_for_no_networks():
    output = "There are 0 networks currently visible.\n"
    assert wifi._parse_visible_networks(output) == []


def test_parse_profile_key_reads_text_format():
    assert wifi._parse_profile_key(PROFILE_TEXT_OUTPUT) == "123456789a"


def test_parse_profile_key_reads_xml_format():
    assert wifi._parse_profile_key(PROFILE_XML_OUTPUT) == "secretkey"


def test_parse_profile_key_returns_none_when_key_is_absent():
    output = "Security key           : Absent\n    Key Content            : \n"
    assert wifi._parse_profile_key(output) is None


def test_parse_profile_key_returns_none_for_unrelated_output():
    assert wifi._parse_profile_key("no profile found") is None


def test_parse_profile_ssid_reads_text_format():
    assert wifi._parse_profile_ssid(PROFILE_TEXT_OUTPUT) == "LPU Wireless"


def test_parse_profile_ssid_reads_xml_format():
    assert wifi._parse_profile_ssid(PROFILE_XML_OUTPUT) == "LPU Wireless"


def test_parse_profile_ssid_returns_none_when_missing():
    assert wifi._parse_profile_ssid("nothing here") is None


def test_saved_profiles_ignores_none_entries(monkeypatch):
    output = """Group policy profiles (read only)
---------------------------------
    <None>

User profiles
-------------
    All User Profile     : LPU Wireless
    All User Profile     : LPU Library
"""
    monkeypatch.setattr(wifi, "_run_netsh", lambda *args: output)

    assert wifi.saved_profiles() == ["LPU Wireless", "LPU Library"]


def test_saved_profiles_handles_current_user_profile_label(monkeypatch):
    output = "    Current User Profile : LPU Wireless\n"
    monkeypatch.setattr(wifi, "_run_netsh", lambda *args: output)

    assert wifi.saved_profiles() == ["LPU Wireless"]


def test_hex_ssid_matches_windows_encoding():
    assert wifi._hex_ssid("LPU Wireless") == "4C505520576972656C657373"


def test_xml_escape_protects_profile_xml():
    escaped = wifi._xml_escape('a&b<c>"d"')

    assert escaped == "a&amp;b&lt;c&gt;&quot;d&quot;"
