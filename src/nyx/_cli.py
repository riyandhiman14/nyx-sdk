"""CLI entry point for the `nyx` command."""

from __future__ import annotations

import argparse
import platform
import shutil
import sys

from nyx import __version__


def cmd_install(args: argparse.Namespace) -> None:
    from nyx._installer import install_sync
    try:
        install_sync(version=args.version, force=args.force)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_uninstall(args: argparse.Namespace) -> None:
    from nyx._installer import uninstall
    if not args.version:
        print("Error: specify a version to uninstall.", file=sys.stderr)
        sys.exit(1)
    uninstall(args.version)


def cmd_list(args: argparse.Namespace) -> None:
    from nyx._installer import list_installed
    versions = list_installed()
    if not versions:
        print("No browsers installed. Run 'nyx install' to get started.")
        return
    for v in versions:
        status = []
        if v.get("has_browser"):
            status.append("browser")
        if v.get("has_aegis"):
            status.append("aegis")
        components = ", ".join(status) if status else "incomplete"
        print(f"  {v['version']}  ({components})  {v.get('path', '')}")


def cmd_doctor(args: argparse.Namespace) -> None:
    from nyx._paths import (
        NYX_HOME, BROWSERS_DIR, get_browser_executable,
        get_aegis_path, get_installed_versions,
    )

    print(f"Nyx SDK version: {__version__}")
    print(f"Platform: {sys.platform} {platform.machine()}")
    print(f"Python: {sys.version}")
    print(f"NYX_HOME: {NYX_HOME}")
    print()

    versions = get_installed_versions()
    if not versions:
        print("No browsers installed.")
        print("  Run: nyx install")
        return

    for ver in versions:
        print(f"Browser {ver}:")
        exe = get_browser_executable(ver)
        aegis = get_aegis_path(ver)

        if exe.exists():
            print(f"  Browser executable: OK ({exe})")
        else:
            print(f"  Browser executable: MISSING ({exe})")

        if aegis.exists():
            print(f"  Aegis CLI: OK ({aegis})")
        else:
            print(f"  Aegis CLI: MISSING ({aegis})")

    # Check if aegis is also on PATH
    which_aegis = shutil.which("aegis")
    if which_aegis:
        print(f"\nAegis on PATH: {which_aegis}")
    else:
        print("\nAegis on PATH: not found (will use bundled version)")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="nyx",
        description="Nyx Browser management CLI",
    )
    parser.add_argument("--version", action="version", version=f"nyx {__version__}")
    sub = parser.add_subparsers(dest="command")

    # install
    p_install = sub.add_parser("install", help="Download browser binary")
    p_install.add_argument("--version", dest="version", default=None,
                           help="Version to install (default: SDK version)")
    p_install.add_argument("--force", action="store_true",
                           help="Force reinstall")
    p_install.set_defaults(func=cmd_install)

    # uninstall
    p_uninstall = sub.add_parser("uninstall", help="Remove a browser version")
    p_uninstall.add_argument("version", nargs="?", default=None,
                             help="Version to uninstall")
    p_uninstall.set_defaults(func=cmd_uninstall)

    # list
    p_list = sub.add_parser("list", help="Show installed versions")
    p_list.set_defaults(func=cmd_list)

    # doctor
    p_doctor = sub.add_parser("doctor", help="Check installation health")
    p_doctor.set_defaults(func=cmd_doctor)

    args = parser.parse_args()
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
