"""Nyx — stealth HTTP client + browser automation for Python, powered by Aegis."""

from nyx.client import Nyx
from nyx.browser import Browser
from nyx.response import Response
from nyx.errors import (
    NyxError, NyxTimeout, NyxConnectionError, NyxNotFound,
    NyxInstallError, NyxLaunchError, NyxBrowserCrashed,
)

__version__ = "0.1.0"
__all__ = [
    "Nyx", "Browser", "Response",
    "NyxError", "NyxTimeout", "NyxConnectionError", "NyxNotFound",
    "NyxInstallError", "NyxLaunchError", "NyxBrowserCrashed",
]
