#!/usr/bin/env python3
"""Tests for the shared citrus/lime build entry points."""

import os
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


def build_plan(script: str, device: str) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env.update({"DEVICE": device, "PRINT_PLAN": "1"})
    return subprocess.run(
        [str(ROOT / script)],
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=5,
    )


class ChimeBuildPlanTest(unittest.TestCase):
    def assert_plan(self, script: str, device: str, title: str) -> None:
        result = build_plan(script, device)
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = dict(
            line.split("=", 1)
            for line in result.stdout.splitlines()
            if "=" in line
        )
        self.assertEqual(lines["DEVICE"], device)
        self.assertTrue(lines["OUT"].endswith(f"/out/{device}"), lines["OUT"])
        self.assertEqual(
            lines["FRAGMENTS"],
            "chime.config:" + f"{device}.config",
        )
        self.assertEqual(
            lines["APPENDED_IMAGE_NAME"],
            f"Valeryn-{title}-Image.gz-dtb",
        )

    def test_supported_boards_have_isolated_outputs_and_shared_config(self) -> None:
        self.assert_plan("build-chime.sh", "citrus", "Citrus")
        self.assert_plan("build-chime.sh", "lime", "Lime")

    def test_legacy_citrus_entry_point_delegates_to_shared_builder(self) -> None:
        wrapper = (ROOT / "build-citrus.sh").read_text()
        self.assertIn("DEVICE=citrus", wrapper)
        self.assertIn("build-chime.sh", wrapper)
        self.assertNotIn("make -C", wrapper)

    def test_unknown_board_is_rejected_before_building(self) -> None:
        result = build_plan("build-chime.sh", "citrus;false")
        self.assertEqual(result.returncode, 2)
        self.assertIn("Unsupported DEVICE", result.stderr)

    def test_shared_config_keeps_the_same_nfc_driver_on_both_boards(self) -> None:
        config_dir = ROOT / "arch/arm64/configs/vendor/xiaomi"
        self.assertIn(
            "CONFIG_NFC_ST21NFC=y",
            (config_dir / "chime.config").read_text().splitlines(),
        )
        for board in ("citrus", "lime"):
            self.assertNotIn(
                "CONFIG_NFC_ST21NFC=y",
                (config_dir / f"{board}.config").read_text().splitlines(),
            )


if __name__ == "__main__":
    unittest.main()
