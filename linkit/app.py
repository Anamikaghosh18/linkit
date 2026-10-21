from __future__ import annotations
import argparse
import time
import sys
from .config import load_config, save_config, APP_DIR, CONFIG_PATH, PORTAL_URL
from .credentials import prompt_and_save, get_credentials, clear_credentials
from .wifi import current_ssid, visible_ssids, is_visible, connect_using_saved_profile
from .portal import open_portal, authenticate
from .startup import install_startup, uninstall_startup

def setup() -> None:
    cfg = load_config()
    print("LinkWireless first-time setup")
    print("-----------------------------")
    ssid = input("Exact LPU Wi-Fi SSID (as shown by Windows): ").strip()
    if not ssid:
        raise ValueError("SSID cannot be empty.")
    cfg["ssid"] = ssid
    cfg["portal_url"] = input(f"Portal URL [{PORTAL_URL}]: ").strip() or PORTAL_URL
    save_config(cfg)
    prompt_and_save()
    print("\nSetup complete. Test with: python -m linkwireless run")

def reset() -> None:
    clear_credentials()
    cfg = load_config()
    cfg["ssid"] = ""
    save_config(cfg)
    print("Saved credentials removed and SSID cleared.")
    print("Run 'python -m linkwireless setup' to configure again.")

def status() -> None:
    cfg = load_config()
    print(f"Config: {CONFIG_PATH}")
    print(f"SSID configured: {'yes' if cfg.get('ssid') else 'no'}")
    print(f"Portal: {cfg.get('portal_url', PORTAL_URL)}")
    try:
        print(f"Current SSID: {current_ssid() or 'not connected / unavailable'}")
        target = cfg.get("ssid", "")
        if target:
            print(f"Target visible: {'yes' if is_visible(target) else 'no'}")
    except Exception as exc:
        print(f"Wi-Fi status error: {exc}")
    try:
        user, password = get_credentials()
        print(f"Credentials configured: {'yes' if user and password else 'no'}")
    except Exception as exc:
        print(f"Credential store error: {exc}")

def run_loop() -> None:
    cfg = load_config()
    ssid = cfg.get("ssid", "").strip()
    if not ssid:
        print("LinkWireless is not configured. Run 'python -m linkwireless setup'.")
        return
    username, password = get_credentials()
    if not username or not password:
        print("Credentials are missing. Run 'python -m linkwireless setup'.")
        return

    print(f"LinkWireless running. Target SSID: {ssid}. Press Ctrl+C to stop.")
    last_portal_open = 0.0
    while True:
        try:
            current = current_ssid()
            if current and current.casefold() == ssid.casefold():
                # Do not submit credentials until the portal flow is verified.
                ok, message = authenticate(username, password, cfg.get("portal_url", PORTAL_URL))
                if not ok:
                    now = time.time()
                    if cfg.get("open_portal_on_detect", True) and now - last_portal_open > 300:
                        print(message)
                        open_portal(cfg.get("portal_url", PORTAL_URL))
                        last_portal_open = now
                else:
                    print("Portal authentication reported successful.")
            elif cfg.get("auto_connect", True) and is_visible(ssid):
                ok, message = connect_using_saved_profile(ssid)
                print("Connection request sent." if ok else f"Connection request may have failed: {message}")
            time.sleep(max(10, int(cfg.get("poll_seconds", 20))))
        except KeyboardInterrupt:
            print("LinkWireless stopped.")
            return
        except Exception as exc:
            print(f"Temporary error: {exc}")
            time.sleep(30)

def main() -> None:
    parser = argparse.ArgumentParser(prog="LinkWireless", description="Lightweight LPU Wi-Fi helper")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("setup", help="first-time configuration")
    sub.add_parser("reset", help="remove saved credentials and settings")
    sub.add_parser("status", help="show configuration and network status")
    sub.add_parser("run", help="run background monitoring in this console")
    sub.add_parser("install-startup", help="start LinkWireless when you sign in to Windows")
    sub.add_parser("uninstall", help="remove Windows startup registration")
    args = parser.parse_args()
    try:
        if args.command == "setup":
            setup()
        elif args.command == "reset":
            reset()
        elif args.command == "status":
            status()
        elif args.command == "run":
            run_loop()
        elif args.command == "install-startup":
            install_startup()
            print("LinkWireless registered for startup.")
        elif args.command == "uninstall":
            uninstall_startup()
            print("LinkWireless startup registration removed.")
        else:
            parser.print_help()
    except Exception as exc:
        print(f"Error: {exc}")
        sys.exit(1)
