"""The palette validator, run against the committed tokens in both modes and the dark card.

Three tests, as for every gate: the committed system passes, a palette with a planted
failure fails, and a config with no modes refuses to report a pass.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "web" / "src" / "theme" / "palette.json"
NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(NODE is None, reason="node is not installed")


def run(config: Path) -> subprocess.CompletedProcess[str]:
    assert NODE is not None
    return subprocess.run(
        [NODE, str(ROOT / "scripts" / "validate_palette.js"), "--config", str(config)],
        capture_output=True,
        text=True,
        check=False,
    )


def test_committed_palette_passes_both_modes_and_the_card() -> None:
    result = run(CONFIG)
    assert result.returncode == 0, result.stdout + result.stderr
    summary = json.loads(result.stdout)
    assert summary["failures"] == 0
    assert set(summary["modes"]) == {"light", "dark"}
    for mode in ("light", "dark"):
        assert summary["modes"][mode]["worstCardContrast"] >= 3.0
        assert summary["modes"][mode]["firstThreeAllPairsCvd"] >= 8.0


def test_planted_failure_fails(tmp_path: Path) -> None:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    # The brief's original dark slot two sits at the same lightness and chroma as slot one.
    config["dark"]["categorical"][1] = "#5B8DEF"
    bad = tmp_path / "palette.json"
    bad.write_text(json.dumps(config), encoding="utf-8")
    result = run(bad)
    assert result.returncode != 0
    assert "#DC6C2C to #5B8DEF" in result.stdout


def test_empty_config_refuses_to_pass(tmp_path: Path) -> None:
    empty = tmp_path / "palette.json"
    empty.write_text("{}", encoding="utf-8")
    result = run(empty)
    assert result.returncode != 0
