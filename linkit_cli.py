"""PyInstaller entry point for the connect-wireless desktop application.

This module is the script passed to PyInstaller, so it must use absolute
imports (``from linkit...``). Relative imports fail with
"attempted relative import with no known parent package" when the file is
executed as a standalone script.

Running ``connect-wireless.exe`` with no arguments starts the desktop
application (setup wizard + system tray icon). Passing a command such as
``status`` or ``setup`` runs the console CLI instead.
"""

from linkit.__main__ import main

if __name__ == "__main__":
    main()
