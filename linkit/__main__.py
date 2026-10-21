"""Entry point for ``python -m linkit`` (and for ``connect-wireless.exe``).

With no arguments the desktop application (tray icon + setup wizard) starts.
With a command such as ``status`` or ``setup`` the console CLI is used
instead, so ``python -m linkit status`` does not open a window.
"""

import sys

from .app import CLI_COMMANDS, main as cli_main


def main() -> None:
    args = sys.argv[1:]
    if args and (args[0] in CLI_COMMANDS or args[0] in {"-h", "--help"}):
        cli_main(args)
        return
    # Imported lazily so the console CLI keeps working without GUI extras.
    from .gui import main as gui_main

    gui_main()


if __name__ == "__main__":
    main()
