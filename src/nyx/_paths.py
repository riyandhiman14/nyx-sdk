"""Centralized binary path resolution for Nyx Browser."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _get_version() -> str:
    from nyx import __version__
    return __version__


NYX_HOME = Path(os.environ.get("NYX_HOME", Path.home() / ".nyx"))
BROWSERS_DIR = NYX_HOME / "browsers"


def _is_linux() -> bool:
    return sys.platform == "linux"


def _is_macos() -> bool:
    return sys.platform == "darwin"


def get_browser_app(version: str) -> Path:
    """Returns path to NyxBrowser.app for given version (macOS only)."""
    return BROWSERS_DIR / version / "NyxBrowser.app"


def get_browser_executable(version: str) -> Path:
    """Returns path to the actual binary, platform-conditional."""
    if _is_linux():
        return BROWSERS_DIR / version / "nyx-browser"
    # macOS
    return get_browser_app(version) / "Contents" / "MacOS" / "NyxBrowser"


def get_aegis_path(version: str) -> Path:
    """Returns path to the aegis CLI binary for given version."""
    return BROWSERS_DIR / version / "aegis"


def _browser_exists(version_dir: Path) -> bool:
    """Check if a browser installation exists in the version directory."""
    if _is_linux():
        return (version_dir / "nyx-browser").exists()
    return (version_dir / "NyxBrowser.app").exists()


def get_installed_versions() -> list[str]:
    """List all installed browser versions."""
    if not BROWSERS_DIR.exists():
        return []
    versions = []
    for d in sorted(BROWSERS_DIR.iterdir()):
        if d.is_dir() and (_browser_exists(d) or (d / "aegis").exists()):
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

    # Fall back to latest installed version
    if version is None:
        installed = get_installed_versions()
        if installed:
            exe = get_browser_executable(installed[-1])
            if exe.exists():
                return exe

    raise FileNotFoundError(
        f"Nyx Browser {ver} not found. Run 'nyx install' to download it."
    )
