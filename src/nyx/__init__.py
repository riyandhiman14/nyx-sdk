"""Nyx — stealth browser automation for Python, powered by Aegis."""

from nyx.client import Nyx
from nyx.snapshot import Snapshot
from nyx.browser import Browser
from nyx.page import Page
from nyx.locator import Locator
from nyx.agent import AgentBrowser
from nyx.response import Response
from nyx.errors import (
    NyxError, NyxTimeout, NyxConnectionError, NyxNotFound,
    NyxInstallError, NyxLaunchError, NyxBrowserCrashed,
)

__version__ = "0.3.0b2"
__all__ = [
    "Nyx", "Browser", "Snapshot", "Page", "Locator", "AgentBrowser", "Response",
    "NyxError", "NyxTimeout", "NyxConnectionError", "NyxNotFound",
    "NyxInstallError", "NyxLaunchError", "NyxBrowserCrashed",
]
