#!/usr/bin/env python3
"""Guard the citrus/Lunaris panic-capture diagnostic configuration."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class PstoreDiagnosticTest(unittest.TestCase):
    def test_ramoops_console_capture_is_enabled(self) -> None:
        config = (ROOT / "arch/arm64/configs/vendor/xiaomi/chime.config").read_text()
        for option in (
            "CONFIG_PSTORE=y",
            "CONFIG_PSTORE_CONSOLE=y",
            "CONFIG_PSTORE_PMSG=y",
            "CONFIG_PSTORE_RAM=y",
        ):
            self.assertIn(option, config.splitlines(), option)

    def test_bengal_has_reserved_ramoops_buffer(self) -> None:
        dts = (ROOT / "arch/arm64/boot/dts/vendor/qcom/bengal.dtsi").read_text()
        match = re.search(
            r"pstore:\s*ramoops@[0-9a-fA-F]+\s*\{(?P<body>.*?)\n\s*\};",
            dts,
            re.DOTALL,
        )
        self.assertIsNotNone(match, "bengal ramoops reserved-memory node missing")
        body = match.group("body")
        self.assertIn('compatible = "ramoops";', body)
        self.assertIn("console-size", body)
        self.assertIn("record-size", body)
        self.assertIn("pmsg-size", body)


if __name__ == "__main__":
    unittest.main()
