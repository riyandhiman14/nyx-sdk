"""Download and verify Nyx Browser binaries from GitHub Releases."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path
from urllib.request import Request, urlopen

from nyx._paths import BROWSERS_DIR, get_browser_app, get_browser_executable, get_aegis_path, current_sdk_version
from nyx.errors import NyxInstallError


GITHUB_REPO = "NyxBrowser/aegis-browser"
ASSET_NAME = "nyx-browser-macos-arm64.tar.gz"
SHASUMS_NAME = "SHASUMS256.txt"


def _download_url(version: str, filename: str) -> str:
    return f"https://github.com/{GITHUB_REPO}/releases/download/v{version}/{filename}"


def _download_with_progress(url: str, dest: Path) -> None:
    """Download a file with progress output to stderr."""
    req = Request(url, headers={"User-Agent": "nyx-installer"})
    resp = urlopen(req, timeout=120)

    total = resp.headers.get("Content-Length")
    total = int(total) if total else None

    downloaded = 0
    chunk_size = 1024 * 64

    with open(dest, "wb") as f:
        while True:
            chunk = resp.read(chunk_size)
            if not chunk:
                break
            f.write(chunk)
            downloaded += len(chunk)
            if total:
                pct = downloaded * 100 // total
                mb = downloaded / (1024 * 1024)
                total_mb = total / (1024 * 1024)
                sys.stderr.write(f"\r  Downloading... {mb:.1f}/{total_mb:.1f} MB ({pct}%)")
            else:
                mb = downloaded / (1024 * 1024)
                sys.stderr.write(f"\r  Downloading... {mb:.1f} MB")
            sys.stderr.flush()

    sys.stderr.write("\n")


def _verify_sha256(archive_path: Path, expected_hash: str) -> None:
    """Verify SHA256 checksum of downloaded archive."""
    sha = hashlib.sha256()
    with open(archive_path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 64), b""):
            sha.update(chunk)
    actual = sha.hexdigest()
    if actual != expected_hash:
        raise NyxInstallError(
            f"SHA256 mismatch: expected {expected_hash}, got {actual}"
        )


def _fetch_shasums(version: str) -> dict[str, str]:
    """Download SHASUMS256.txt and return {filename: hash} dict."""
    url = _download_url(version, SHASUMS_NAME)
    req = Request(url, headers={"User-Agent": "nyx-installer"})
    try:
        resp = urlopen(req, timeout=30)
        text = resp.read().decode()
    except Exception:
        return {}

    sums: dict[str, str] = {}
    for line in text.strip().splitlines():
        parts = line.split(None, 1)
        if len(parts) == 2:
            sums[parts[1].strip()] = parts[0].strip()
    return sums


async def install(version: str | None = None, force: bool = False) -> Path:
    """Download and extract browser binary to ~/.nyx/browsers/{version}/.

    Returns the installation directory.
    """
    return await asyncio.to_thread(install_sync, version=version, force=force)


def install_sync(version: str | None = None, force: bool = False) -> Path:
    """Synchronous install — download, verify, extract browser binary."""
    ver = version or current_sdk_version()
    dest_dir = BROWSERS_DIR / ver

    if dest_dir.exists() and not force:
        exe = get_browser_executable(ver)
        if exe.exists():
            sys.stderr.write(f"Nyx Browser {ver} is already installed.\n")
            sys.stderr.write(f"Use --force to reinstall.\n")
            return dest_dir

    if platform.machine() != "arm64":
        sys.stderr.write(
            f"Warning: pre-built binaries are for macOS arm64, "
            f"but this machine is {platform.machine()}.\n"
        )

    sys.stderr.write(f"Installing Nyx Browser {ver}...\n")

    # Fetch checksums
    sys.stderr.write("  Fetching checksums...\n")
    shasums = _fetch_shasums(ver)

    # Download archive
    archive_url = _download_url(ver, ASSET_NAME)
    with tempfile.TemporaryDirectory() as tmp:
        archive_path = Path(tmp) / ASSET_NAME

        try:
            _download_with_progress(archive_url, archive_path)
        except Exception as e:
            raise NyxInstallError(f"Download failed: {e}") from e

        # Verify checksum
        expected_hash = shasums.get(ASSET_NAME)
        if expected_hash:
            sys.stderr.write("  Verifying checksum...\n")
            _verify_sha256(archive_path, expected_hash)
        else:
            sys.stderr.write("  Warning: no checksum available, skipping verification.\n")

        # Extract
        sys.stderr.write("  Extracting...\n")
        if dest_dir.exists():
            shutil.rmtree(dest_dir)
        dest_dir.mkdir(parents=True, exist_ok=True)

        with tarfile.open(archive_path, "r:gz") as tar:
            tar.extractall(dest_dir)

    # Remove macOS quarantine
    app_path = get_browser_app(ver)
    if app_path.exists():
        subprocess.run(
            ["xattr", "-rd", "com.apple.quarantine", str(app_path)],
            capture_output=True,
        )

    # Make aegis executable
    aegis = get_aegis_path(ver)
    if aegis.exists():
        aegis.chmod(0o755)

    # Make browser executable
    exe = get_browser_executable(ver)
    if exe.exists():
        exe.chmod(0o755)

    # Write metadata
    metadata = {
        "version": ver,
        "platform": f"{sys.platform}-{platform.machine()}",
        "installed_by": f"nyx-sdk/{ver}",
    }
    meta_path = dest_dir / ".metadata.json"
    meta_path.write_text(json.dumps(metadata, indent=2))

    sys.stderr.write(f"  Nyx Browser {ver} installed to {dest_dir}\n")
    return dest_dir


def uninstall(version: str) -> None:
    """Remove an installed browser version."""
    dest_dir = BROWSERS_DIR / version
    if not dest_dir.exists():
        sys.stderr.write(f"Nyx Browser {version} is not installed.\n")
        return
    shutil.rmtree(dest_dir)
    sys.stderr.write(f"Nyx Browser {version} uninstalled.\n")


def list_installed() -> list[dict]:
    """List installed browser versions with metadata."""
    results = []
    if not BROWSERS_DIR.exists():
        return results
    for d in sorted(BROWSERS_DIR.iterdir()):
        if not d.is_dir():
            continue
        meta_path = d / ".metadata.json"
        if meta_path.exists():
            meta = json.loads(meta_path.read_text())
        else:
            meta = {"version": d.name}
        meta["path"] = str(d)
        meta["has_browser"] = get_browser_executable(d.name).exists()
        meta["has_aegis"] = get_aegis_path(d.name).exists()
        results.append(meta)
    return results
