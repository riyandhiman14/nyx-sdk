"""Centralized binary path resolution for Nyx Browser."""

from __future__ import annotations

import os
from pathlib import Path

def _get_version() -> str:
    from nyx import __version__
    return __version__


NYX_HOME = Path(os.environ.get("NYX_HOME", Path.home() / ".nyx"))
BROWSERS_DIR = NYX_HOME / "browsers"


def get_browser_app(version: str) -> Path:
    """Returns path to NyxBrowser.app for given version."""
    return BROWSERS_DIR / version / "NyxBrowser.app"


def get_browser_executable(version: str) -> Path:
    """Returns path to the actual binary inside the .app bundle."""
    return get_browser_app(version) / "Contents" / "MacOS" / "NyxBrowser"


def get_aegis_path(version: str) -> Path:
    """Returns path to the aegis CLI binary for given version."""
    return BROWSERS_DIR / version / "aegis"


def get_installed_versions() -> list[str]:
    """List all installed browser versions."""
    if not BROWSERS_DIR.exists():
        return []
    versions = []
    for d in sorted(BROWSERS_DIR.iterdir()):
        if d.is_dir() and (d / "NyxBrowser.app").exists():
            versions.append(d.name)
    return versions


def current_sdk_version() -> str:
    """Return the current SDK version string."""
    return _get_version()


def resolve_browser_executable(version: str | None = None) -> Path:
    """Resolve the browser executable, respecting env var overrides.

    Priority:
    1. NYX_BROWSER_EXECUTABLE env var
    2. Installed version at ~/.nyx/browsers/{version}/
    3. Raises FileNotFoundError
    """
    env_exe = os.environ.get("NYX_BROWSER_EXECUTABLE")
    if env_exe:
        return Path(env_exe)

    ver = version or current_sdk_version()
    exe = get_browser_executable(ver)
    if exe.exists():
        return exe

    raise FileNotFoundError(
        f"Nyx Browser {ver} not found. Run 'nyx install' to download it."
    )
