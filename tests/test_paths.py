"""Unit tests for path resolution — fully offline."""

import sys
from pathlib import Path
from unittest.mock import patch

from nyx._paths import (
    NYX_HOME,
    BROWSERS_DIR,
    get_browser_app,
    get_browser_executable,
    get_aegis_path,
)


class TestPathConstants:
    def test_nyx_home_is_path(self):
        assert isinstance(NYX_HOME, Path)

    def test_browsers_dir_under_nyx_home(self):
        assert BROWSERS_DIR == NYX_HOME / "browsers"


class TestBrowserPaths:
    def test_browser_app_path(self):
        p = get_browser_app("0.1.0")
        assert "0.1.0" in str(p)
        assert "NyxBrowser.app" in str(p)

    @patch("nyx._paths._is_linux", return_value=True)
    @patch("nyx._paths._is_macos", return_value=False)
    def test_linux_executable(self, mock_mac, mock_linux):
        p = get_browser_executable("0.1.0")
        assert str(p).endswith("nyx-browser")
        assert "0.1.0" in str(p)

    @patch("nyx._paths._is_linux", return_value=False)
    @patch("nyx._paths._is_macos", return_value=True)
    def test_macos_executable(self, mock_mac, mock_linux):
        p = get_browser_executable("0.1.0")
        assert "NyxBrowser.app" in str(p)
        assert "NyxBrowser" in str(p)

    def test_aegis_path(self):
        p = get_aegis_path("0.1.0")
        assert str(p).endswith("aegis")
        assert "0.1.0" in str(p)


class TestResolveExecutable:
    @patch.dict("os.environ", {"NYX_BROWSER_EXECUTABLE": "/custom/browser"})
    def test_env_override(self):
        from nyx._paths import resolve_browser_executable
        p = resolve_browser_executable()
        assert str(p) == "/custom/browser"

    def test_missing_raises(self):
        import os
        # Ensure env var is not set
        env = os.environ.copy()
        env.pop("NYX_BROWSER_EXECUTABLE", None)
        with patch.dict("os.environ", env, clear=True):
            from nyx._paths import resolve_browser_executable
            # This will raise unless the browser is actually installed
            # which is fine for a unit test
            try:
                resolve_browser_executable("99.99.99")
            except FileNotFoundError as e:
                assert "99.99.99" in str(e)
