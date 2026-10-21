"""Tests for the campus connection flow: profile reuse, creation and fallback."""

import pytest

from linkit import campus, wifi


@pytest.fixture(autouse=True)
def _clear_cache():
    campus.invalidate_cache()
    yield
    campus.invalidate_cache()


def _network(ssid, signal=70, auth="WPA3-Personal"):
    return {"ssid": ssid, "signal": signal, "auth": auth, "channel": 6}


def test_ensure_profile_reuses_an_existing_profile(monkeypatch):
    monkeypatch.setattr(wifi, "saved_profiles", lambda: ["LPU Wireless"])
    monkeypatch.setattr(wifi, "profile_ssid", lambda name: "LPU Wireless")

    ok, message = campus.ensure_profile("LPU Wireless")

    assert ok
    assert "LPU Wireless" in message


def test_ensure_profile_fails_without_a_key(monkeypatch):
    monkeypatch.setattr(wifi, "saved_profiles", lambda: [])
    monkeypatch.setattr(wifi, "profile_ssid", lambda name: None)

    ok, message = campus.ensure_profile("LPU Block-99")

    assert not ok
    assert "no campus key" in message.lower()


def test_ensure_profile_creates_a_missing_profile(monkeypatch):
    created = {}

    monkeypatch.setattr(wifi, "saved_profiles", lambda: [])
    monkeypatch.setattr(wifi, "profile_ssid", lambda name: None)

    def fake_create(ssid, key, authentication="WPA2PSK"):
        created["args"] = (ssid, key, authentication)
        return True, "Profile added"

    monkeypatch.setattr(wifi, "create_profile", fake_create)

    ok, message = campus.ensure_profile("LPU Block-99", "123456789a", "WPA3-Personal")

    assert ok
    assert created["args"] == ("LPU Block-99", "123456789a", "WPA3-Personal")


def test_connect_to_campus_reports_when_nothing_is_in_range(monkeypatch):
    monkeypatch.setattr(wifi, "visible_networks", lambda: [_network("Connect_2.4")])

    ok, message = campus.connect_to_campus()

    assert not ok
    assert "no campus wi-fi network" in message.lower()


def test_connect_to_campus_uses_a_saved_profile(monkeypatch):
    monkeypatch.setattr(
        wifi,
        "visible_networks",
        lambda: [_network("LPU Wireless", signal=80)],
    )
    monkeypatch.setattr(wifi, "saved_profiles", lambda: ["LPU Wireless"])
    monkeypatch.setattr(wifi, "profile_ssid", lambda name: "LPU Wireless")
    monkeypatch.setattr(wifi, "profile_key", lambda name: "123456789a")

    calls = {}

    def fake_connect(profile, ssid=None):
        calls["profile"] = profile
        calls["ssid"] = ssid
        return True, "Request completed successfully."

    monkeypatch.setattr(wifi, "connect_using_saved_profile", fake_connect)

    ok, message = campus.connect_to_campus()

    assert ok
    assert calls["profile"] == "LPU Wireless"
    assert "LPU Wireless" in message


def test_connect_to_campus_creates_a_profile_when_the_key_is_known(monkeypatch):
    monkeypatch.setattr(
        wifi,
        "visible_networks",
        lambda: [_network("LPU Block-99", signal=80)],
    )
    monkeypatch.setattr(wifi, "saved_profiles", lambda: ["LPU Wireless"])
    monkeypatch.setattr(wifi, "profile_ssid", lambda name: name)
    monkeypatch.setattr(wifi, "profile_key", lambda name: "123456789a")

    created = {}

    def fake_create(ssid, key, authentication="WPA2PSK"):
        created["ssid"] = ssid
        created["key"] = key
        created["auth"] = authentication
        return True, "Profile added"

    monkeypatch.setattr(wifi, "create_profile", fake_create)
    monkeypatch.setattr(
        wifi, "connect_using_saved_profile", lambda profile, ssid=None: (True, "ok")
    )

    ok, message = campus.connect_to_campus()

    assert ok
    assert created["ssid"] == "LPU Block-99"
    assert created["key"] == "123456789a"
    assert created["auth"] == "WPA3-Personal"


def test_connect_to_campus_skips_networks_it_cannot_secure(monkeypatch):
    monkeypatch.setattr(
        wifi,
        "visible_networks",
        lambda: [_network("LPU Enterprise", auth="WPA2-Enterprise")],
    )
    monkeypatch.setattr(wifi, "saved_profiles", lambda: [])
    monkeypatch.setattr(wifi, "profile_ssid", lambda name: None)

    ok, message = campus.connect_to_campus()

    assert not ok
    assert "could be joined" in message.lower()


def test_connect_to_campus_joins_open_networks_without_a_profile(monkeypatch):
    monkeypatch.setattr(
        wifi,
        "visible_networks",
        lambda: [_network("Campus Guest", auth="Open", signal=60)],
    )
    monkeypatch.setattr(wifi, "saved_profiles", lambda: [])
    monkeypatch.setattr(wifi, "profile_ssid", lambda name: None)

    calls = {}

    def fake_connect_ssid(ssid):
        calls["ssid"] = ssid
        return True, "Request completed successfully."

    monkeypatch.setattr(wifi, "connect_to_ssid", fake_connect_ssid)

    ok, message = campus.connect_to_campus()

    assert ok
    assert calls["ssid"] == "Campus Guest"
    assert "open network" in message.lower()


def test_connect_to_campus_tries_the_next_network_when_one_fails(monkeypatch):
    monkeypatch.setattr(
        wifi,
        "visible_networks",
        lambda: [
            _network("LPU Block-34", signal=90),
            _network("LPU Wireless", signal=70),
        ],
    )
    monkeypatch.setattr(wifi, "saved_profiles", lambda: ["LPU Block-34", "LPU Wireless"])
    monkeypatch.setattr(wifi, "profile_ssid", lambda name: name)
    monkeypatch.setattr(wifi, "profile_key", lambda name: "123456789a")

    attempted = []

    def fake_connect(profile, ssid=None):
        attempted.append(profile)
        if profile == "LPU Block-34":
            return False, "The network profile is not valid for this network."
        return True, "Request completed successfully."

    monkeypatch.setattr(wifi, "connect_using_saved_profile", fake_connect)

    ok, message = campus.connect_to_campus()

    assert ok
    assert attempted == ["LPU Block-34", "LPU Wireless"]
    assert "LPU Wireless" in message
