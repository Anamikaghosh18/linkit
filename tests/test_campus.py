"""Tests for campus network detection and key fallback."""

import pytest

from linkit import campus, wifi


@pytest.fixture(autouse=True)
def _clear_cache():
    campus.invalidate_cache()
    yield
    campus.invalidate_cache()


def _network(ssid, signal=70, auth="WPA3-Personal"):
    return {"ssid": ssid, "signal": signal, "auth": auth, "channel": 6}


def test_is_campus_ssid_matches_default_patterns():
    assert campus.is_campus_ssid("LPU Wireless")
    assert campus.is_campus_ssid("LPU Block-34")
    assert campus.is_campus_ssid("lpu library")
    assert campus.is_campus_ssid("Hostel Campus WiFi")


def test_is_campus_ssid_rejects_unrelated_networks():
    assert not campus.is_campus_ssid("Connect_2.4")
    assert not campus.is_campus_ssid("AirFiber-4T7Fq3")
    assert not campus.is_campus_ssid("")


def test_is_campus_ssid_accepts_extra_configured_patterns():
    assert campus.is_campus_ssid("HostelNet", [r"^Hostel"])
    assert not campus.is_campus_ssid("Connect_2.4", [r"^Hostel"])


def test_is_campus_ssid_ignores_invalid_regular_expressions():
    assert campus.is_campus_ssid("LPU Wireless", ["[unclosed"])
    assert not campus.is_campus_ssid("Connect_2.4", ["[unclosed"])


def test_discover_campus_networks_filters_and_sorts_by_signal(monkeypatch):
    monkeypatch.setattr(
        wifi,
        "visible_networks",
        lambda: [
            _network("Connect_2.4", signal=99),
            _network("LPU Block-26", signal=40),
            _network("LPU Wireless", signal=88),
        ],
    )

    discovered = campus.discover_campus_networks()

    assert [network["ssid"] for network in discovered] == ["LPU Wireless", "LPU Block-26"]


def test_needs_psk_only_matches_personal_networks():
    assert campus.needs_psk(_network("LPU Wireless", auth="WPA3-Personal"))
    assert campus.needs_psk(_network("LPU Wireless", auth="WPA2-Personal"))
    assert not campus.needs_psk(_network("Guest", auth="Open"))
    assert not campus.needs_psk(_network("Corp", auth="WPA2-Enterprise"))
    assert not campus.needs_psk(_network("Unknown", auth=""))


def test_is_open_detects_open_networks():
    assert campus.is_open(_network("Guest", auth="Open"))
    assert not campus.is_open(_network("LPU Wireless", auth="WPA3-Personal"))


def test_profile_index_maps_profile_names_to_ssids(monkeypatch):
    monkeypatch.setattr(wifi, "saved_profiles", lambda: ["LPU Wireless", "HomeNet"])
    monkeypatch.setattr(
        wifi,
        "profile_ssid",
        lambda name: {"LPU Wireless": "LPU Wireless", "HomeNet": "HomeNet"}[name],
    )

    assert campus.profile_index() == {
        "LPU Wireless": "LPU Wireless",
        "HomeNet": "HomeNet",
    }


def test_profile_index_falls_back_to_profile_name(monkeypatch):
    monkeypatch.setattr(wifi, "saved_profiles", lambda: ["LPU Wireless"])
    monkeypatch.setattr(wifi, "profile_ssid", lambda name: None)

    assert campus.profile_index() == {"LPU Wireless": "LPU Wireless"}


def test_saved_campus_profiles_only_returns_campus_entries(monkeypatch):
    monkeypatch.setattr(wifi, "saved_profiles", lambda: ["LPU Wireless", "HomeNet"])
    monkeypatch.setattr(wifi, "profile_ssid", lambda name: name)

    assert campus.saved_campus_profiles() == ["LPU Wireless"]


def test_find_campus_key_prefers_the_most_shared_key(monkeypatch):
    monkeypatch.setattr(wifi, "saved_profiles", lambda: ["A", "B", "C", "D"])
    monkeypatch.setattr(wifi, "profile_ssid", lambda name: f"LPU {name}")
    keys = {"A": "11111111", "B": "11111111", "C": "22222222", "D": "11111111"}
    monkeypatch.setattr(wifi, "profile_key", lambda name: keys[name])

    key, source = campus.find_campus_key()

    assert key == "11111111"
    assert source in {"A", "B", "D"}


def test_find_campus_key_prefers_visible_networks_on_a_tie(monkeypatch):
    monkeypatch.setattr(wifi, "saved_profiles", lambda: ["Old", "New"])
    monkeypatch.setattr(
        wifi,
        "profile_ssid",
        lambda name: {"Old": "LPU Old", "New": "LPU New"}[name],
    )
    keys = {"Old": "aaaa1111", "New": "bbbb2222"}
    monkeypatch.setattr(wifi, "profile_key", lambda name: keys[name])

    key, source = campus.find_campus_key(["LPU New"])

    assert key == "bbbb2222"
    assert source == "New"


def test_find_campus_key_returns_none_without_campus_profiles(monkeypatch):
    monkeypatch.setattr(wifi, "saved_profiles", lambda: ["HomeNet"])
    monkeypatch.setattr(wifi, "profile_ssid", lambda name: name)

    assert campus.find_campus_key() == (None, None)


def test_profile_for_matches_case_insensitively(monkeypatch):
    monkeypatch.setattr(wifi, "saved_profiles", lambda: ["LPU Wireless"])
    monkeypatch.setattr(wifi, "profile_ssid", lambda name: "LPU Wireless")

    assert campus.profile_for("lpu wireless") == "LPU Wireless"
    assert campus.profile_for("Other") is None

