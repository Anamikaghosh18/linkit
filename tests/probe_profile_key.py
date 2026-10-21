"""Live check: create a profile with connect-wireless and read the key back.

Verifies that the scope chosen by ``wifi.create_profile`` keeps the pre-shared
key readable, which is what allows connect-wireless to reuse the key for other
campus SSIDs. The temporary profile is always removed again.
"""

import subprocess
import sys

sys.path.insert(0, ".")

from linkit import wifi  # noqa: E402

PROFILE = "Connect Wireless Live Check"
KEY = "connectwireless123"


def netsh(*args):
    result = subprocess.run(["netsh", *args], capture_output=True, text=True)
    return (result.stdout + result.stderr).strip()


def main():
    netsh("wlan", "delete", "profile", f"name={PROFILE}")

    try:
        ok, message = wifi.create_profile(PROFILE, KEY, "WPA3-Personal")
        print("create ->", ok, "|", message)

        listing = netsh("wlan", "show", "profiles")
        for line in listing.splitlines():
            if PROFILE in line:
                print("listed ->", line.strip())

        show = netsh("wlan", "show", "profile", f"name={PROFILE}", "key=clear")
        print("key readable ->", KEY in show)
        print("auth ->", wifi.profile_authentication(PROFILE))
        print("ssid ->", wifi.profile_ssid(PROFILE))
        print("parsed key ->", wifi.profile_key(PROFILE))
    finally:
        print("cleanup ->", netsh("wlan", "delete", "profile", f"name={PROFILE}"))


if __name__ == "__main__":
    sys.exit(main())
