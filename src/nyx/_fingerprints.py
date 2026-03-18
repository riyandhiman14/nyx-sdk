"""Built-in browser fingerprint profiles for max stealth.

Each profile is a complete fingerprint that matches real browser traffic.
No external dependencies needed — these are curated from real-world data.

Usage:
    from nyx._fingerprints import resolve_fingerprint
    fp = resolve_fingerprint("chrome131")   # specific profile
    fp = resolve_fingerprint("random")      # random pick
    fp = resolve_fingerprint("windows")     # random Windows profile
"""

from __future__ import annotations

import random
from typing import Any


# ── Curated profiles ──────────────────────────────────────────────────────────
# Each mimics a real browser session from real-world traffic captures.
# Fields match the __nyx_fp schema consumed by the renderer's stealth script.

PROFILES: dict[str, dict[str, Any]] = {
    "chrome131_win": {
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "platform": "Win32",
        "vendor": "Google Inc.",
        "hardware_concurrency": 8,
        "device_memory": 8,
        "max_touch_points": 0,
        "language": "en-US",
        "languages": ["en-US", "en"],
        "webgl_vendor": "Google Inc. (Intel)",
        "webgl_renderer": "ANGLE (Intel, Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "screen_width": 1920,
        "screen_height": 1080,
        "avail_width": 1920,
        "avail_height": 1040,
        "color_depth": 24,
        "pixel_depth": 24,
        "device_pixel_ratio": 1,
        "ua_brands": [["Not A(Brand", "99"], ["Chromium", "131"], ["Google Chrome", "131"]],
        "ua_platform": "Windows",
        "ua_mobile": False,
        "ua_platform_version": "15.0.0",
        "ua_architecture": "x86",
        "ua_bitness": "64",
        "ua_full_version": "131.0.6778.109",
    },
    "chrome132_mac": {
        "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
        "platform": "MacIntel",
        "vendor": "Google Inc.",
        "hardware_concurrency": 10,
        "device_memory": 8,
        "max_touch_points": 0,
        "language": "en-US",
        "languages": ["en-US", "en"],
        "webgl_vendor": "Google Inc. (Apple)",
        "webgl_renderer": "ANGLE (Apple, ANGLE Metal Renderer: Apple M2 Pro, Unspecified Version)",
        "screen_width": 1512,
        "screen_height": 982,
        "avail_width": 1512,
        "avail_height": 944,
        "color_depth": 30,
        "pixel_depth": 30,
        "device_pixel_ratio": 2,
        "ua_brands": [["Not A(Brand", "99"], ["Chromium", "132"], ["Google Chrome", "132"]],
        "ua_platform": "macOS",
        "ua_mobile": False,
        "ua_platform_version": "14.5.0",
        "ua_architecture": "arm",
        "ua_bitness": "64",
        "ua_full_version": "132.0.6834.83",
    },
    "chrome130_linux": {
        "user_agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
        "platform": "Linux x86_64",
        "vendor": "Google Inc.",
        "hardware_concurrency": 4,
        "device_memory": 8,
        "max_touch_points": 0,
        "language": "en-US",
        "languages": ["en-US", "en"],
        "webgl_vendor": "Google Inc. (NVIDIA)",
        "webgl_renderer": "ANGLE (NVIDIA, NVIDIA GeForce GTX 1060 6GB/PCIe/SSE2, OpenGL 4.5)",
        "screen_width": 1920,
        "screen_height": 1080,
        "avail_width": 1920,
        "avail_height": 1053,
        "color_depth": 24,
        "pixel_depth": 24,
        "device_pixel_ratio": 1,
        "ua_brands": [["Not A(Brand", "99"], ["Chromium", "130"], ["Google Chrome", "130"]],
        "ua_platform": "Linux",
        "ua_mobile": False,
        "ua_platform_version": "6.5.0",
        "ua_architecture": "x86",
        "ua_bitness": "64",
        "ua_full_version": "130.0.6723.91",
    },
    "chrome131_win_nvidia": {
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "platform": "Win32",
        "vendor": "Google Inc.",
        "hardware_concurrency": 16,
        "device_memory": 8,
        "max_touch_points": 0,
        "language": "en-US",
        "languages": ["en-US", "en"],
        "webgl_vendor": "Google Inc. (NVIDIA)",
        "webgl_renderer": "ANGLE (NVIDIA, NVIDIA GeForce RTX 3070 Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "screen_width": 2560,
        "screen_height": 1440,
        "avail_width": 2560,
        "avail_height": 1400,
        "color_depth": 24,
        "pixel_depth": 24,
        "device_pixel_ratio": 1,
        "ua_brands": [["Not A(Brand", "99"], ["Chromium", "131"], ["Google Chrome", "131"]],
        "ua_platform": "Windows",
        "ua_mobile": False,
        "ua_platform_version": "15.0.0",
        "ua_architecture": "x86",
        "ua_bitness": "64",
        "ua_full_version": "131.0.6778.140",
    },
    "chrome132_win_amd": {
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
        "platform": "Win32",
        "vendor": "Google Inc.",
        "hardware_concurrency": 12,
        "device_memory": 8,
        "max_touch_points": 0,
        "language": "en-US",
        "languages": ["en-US", "en"],
        "webgl_vendor": "Google Inc. (AMD)",
        "webgl_renderer": "ANGLE (AMD, AMD Radeon RX 6700 XT Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "screen_width": 1920,
        "screen_height": 1080,
        "avail_width": 1920,
        "avail_height": 1040,
        "color_depth": 24,
        "pixel_depth": 24,
        "device_pixel_ratio": 1,
        "ua_brands": [["Not A(Brand", "99"], ["Chromium", "132"], ["Google Chrome", "132"]],
        "ua_platform": "Windows",
        "ua_mobile": False,
        "ua_platform_version": "15.0.0",
        "ua_architecture": "x86",
        "ua_bitness": "64",
        "ua_full_version": "132.0.6834.110",
    },
}

# ── Aliases ───────────────────────────────────────────────────────────────────

ALIASES: dict[str, list[str]] = {
    # Specific versions
    "chrome130": ["chrome130_linux"],
    "chrome131": ["chrome131_win", "chrome131_win_nvidia"],
    "chrome132": ["chrome132_mac", "chrome132_win_amd"],

    # OS-based
    "windows": ["chrome131_win", "chrome131_win_nvidia", "chrome132_win_amd"],
    "macos": ["chrome132_mac"],
    "mac": ["chrome132_mac"],
    "linux": ["chrome130_linux"],

    # Generic
    "chrome": list(PROFILES.keys()),
    "random": list(PROFILES.keys()),
}


def resolve_fingerprint(profile: str | dict | None) -> dict[str, Any] | None:
    """Resolve a profile name or dict to a full fingerprint JSON dict.

    Args:
        profile: Profile name ("chrome131", "random", "windows"), raw dict, or None.

    Returns:
        Fingerprint dict ready for --fingerprint CLI arg, or None.
    """
    if profile is None:
        return None

    if isinstance(profile, dict):
        return profile

    name = profile.lower().strip()

    # Direct profile name match
    if name in PROFILES:
        return dict(PROFILES[name])

    # Alias match
    if name in ALIASES:
        candidates = ALIASES[name]
        chosen = random.choice(candidates)
        return dict(PROFILES[chosen])

    # Fuzzy: "chrome131" should match any profile starting with "chrome131"
    matches = [k for k in PROFILES if k.startswith(name)]
    if matches:
        chosen = random.choice(matches)
        return dict(PROFILES[chosen])

    # Nothing matched — return None, caller can decide what to do
    return None


def list_profiles() -> list[str]:
    """Return all available profile names and aliases."""
    return sorted(set(list(PROFILES.keys()) + list(ALIASES.keys())))
