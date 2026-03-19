"""Import hygiene guardrail for retired legacy module paths."""

from __future__ import annotations

import subprocess


def test_no_legacy_imports() -> None:
    result = subprocess.run(
        [
            "grep",
            "-r",
            r"from gad\.models import\|from gad\.io import",
            "--include=*.py",
            ".",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    offenders = [
        line
        for line in result.stdout.splitlines()
        if "_legacy" not in line and not line.strip().startswith("#")
    ]

    assert offenders == [], (
        "Legacy imports found outside _legacy files:\n" + "\n".join(offenders)
    )
