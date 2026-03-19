"""
GAD version at compute time — for independent verifiability of reports.
Every BasisRiskReport must carry the exact engine version that produced it.
"""

from __future__ import annotations

import subprocess


def get_gad_version() -> str:
    """
    Returns the GAD version string to stamp on reports.
    Prefer git commit (short); fall back to package version if git unavailable
    (e.g. Docker build without git history).
    """
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=2,
        )
        return out.strip() or _fallback_version()
    except Exception:
        return _fallback_version()


def _fallback_version() -> str:
    try:
        import importlib.metadata
        return importlib.metadata.version("gad")
    except Exception:
        return "0.1.0"
