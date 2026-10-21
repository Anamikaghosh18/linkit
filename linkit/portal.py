from __future__ import annotations
import webbrowser

def open_portal(url: str) -> bool:
    """Open the official portal for manual authentication when required.

    The live LPU portal form/request flow has not been verified. Do not replace this
    with guessed HTTP parameters: inspect the actual login form and network flow first.
    """
    return bool(webbrowser.open(url, new=0, autoraise=False))

def authenticate(username: str, password: str, url: str) -> tuple[bool, str]:
    """Portal adapter placeholder.

    Returns failure explicitly instead of pretending a login succeeded.
    Implement only after confirming the official portal's current form, CSRF/session
    requirements, redirects, and acceptable authentication method.
    """
    return False, (
        "Automatic portal submission is not enabled yet because LPU's current login "
        "flow has not been verified. Open the portal and sign in manually."
    )
