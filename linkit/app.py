from __future__ import annotations
import argparse
import time
import sys
from .config import load_config, save_config, APP_DIR, CONFIG_PATH, PORTAL_URL
from .credentials import prompt_and_save, get_credentials, clear_credentials
from .wifi import current_ssid
from .campus import connect_to_campus, discover_campus_networks, is_campus_ssid
from .portal import open_portal, authenticate
from .startup import install_startup, uninstall_startup

CLI_COMMANDS = ("setup", "reset", "status", "run", "install-startup", "uninstall")


def setup() -> None:
    cfg = load_config()
    print("connect-wireless first-time setup")
    print("------------------------------------")
    print("Only your university portal login is needed.")
    print("Campus Wi-Fi networks are detected and joined automatically.")
    cfg["portal_url"] = input(f"Portal URL [{PORTAL_URL}]: ").strip() or PORTAL_URL
    save_config(cfg)
    prompt_and_save()
    print("\nSetup complete. Test with: connect-wireless.exe run")

def reset() -> None:
    clear_credentials()
    print("Saved credentials removed.")
    print("Run 'connect-wireless.exe setup' to configure again.")

def status() -> None:
    cfg = load_config()
    print(f"Config: {CONFIG_PATH}")
    print(f"Portal: {cfg.get('portal_url', PORTAL_URL)}")
    try:
        print(f"Current SSID: {current_ssid() or 'not connected / unavailable'}")
        networks = discover_campus_networks()
        if networks:
            print("Campus networks in range:")
            for network in networks:
                signal = network.get("signal")
                strength = f"{signal}%" if signal is not None else "signal unknown"
                print(f"  - {network['ssid']} ({strength}, {network.get('auth') or 'auth unknown'})")
        else:
            print("Campus networks in range: none detected")
    except Exception as exc:
        print(f"Wi-Fi status error: {exc}")
    try:
        user, password = get_credentials()
        print(f"Credentials configured: {'yes' if user and password else 'no'}")
    except Exception as exc:
        print(f"Credential store error: {exc}")

def run_loop() -> None:
    cfg = load_config()
    username, password = get_credentials()
    if not username or not password:
        print("Credentials are missing. Run 'connect-wireless.exe setup'.")
        return

    print("connect-wireless running. Campus Wi-Fi is detected and joined automatically.")
    print("Press Ctrl+C to stop.")
    last_portal_open = 0.0
    while True:
        try:
            current = current_ssid()
            if current and is_campus_ssid(current):
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
            elif cfg.get("auto_connect", True):
                ok, message = connect_to_campus()
                print(message if ok else f"No campus connection made: {message}")
            time.sleep(max(10, int(cfg.get("poll_seconds", 20))))
        except KeyboardInterrupt:
            print("connect-wireless stopped.")
            return
        except Exception as exc:
            print(f"Temporary error: {exc}")
            time.sleep(30)

def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="connect-wireless", description="Lightweight campus Wi-Fi helper"
    )
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("setup", help="first-time configuration")
    sub.add_parser("reset", help="remove saved credentials and settings")
    sub.add_parser("status", help="show configuration and network status")
    sub.add_parser("run", help="run background monitoring in this console")
    sub.add_parser("install-startup", help="start connect-wireless when you sign in to Windows")
    sub.add_parser("uninstall", help="remove Windows startup registration")
    args = parser.parse_args(argv)
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
            print("connect-wireless registered for startup.")
        elif args.command == "uninstall":
            uninstall_startup()
            print("connect-wireless startup registration removed.")
        else:
            parser.print_help()
    except Exception as exc:
        print(f"Error: {exc}")
        sys.exit(1)
