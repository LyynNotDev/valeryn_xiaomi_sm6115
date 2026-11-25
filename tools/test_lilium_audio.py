#!/usr/bin/env python3
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
WSA = ROOT / "techpack/audio/asoc/codecs/bolero/wsa-macro.c"
PROVENANCE = ROOT / "LILIUM_AUDIO_UPSTREAM"


class LiliumAudioRegression(unittest.TestCase):
    def test_wsa_compander_defaults_match_pinned_lilium(self) -> None:
        text = WSA.read_text()
        expected_by_section = {
            "wsa_macro_spkr_default": (
                "\t{BOLERO_CDC_WSA_COMPANDER0_CTL7, 0x01, 0x01},\n"
                "\t{BOLERO_CDC_WSA_COMPANDER1_CTL7, 0x01, 0x01},",
            ),
            "wsa_macro_spkr_mode1": (
                "\t{BOLERO_CDC_WSA_COMPANDER0_CTL7, 0x01, 0x00},\n"
                "\t{BOLERO_CDC_WSA_COMPANDER1_CTL7, 0x01, 0x00},",
            ),
            "wsa_macro_reg_init": (
                "\t{BOLERO_CDC_WSA_COMPANDER0_CTL7, 0x1E, 0x18},",
                "\t{BOLERO_CDC_WSA_COMPANDER1_CTL7, 0x1E, 0x18},",
                "\t{BOLERO_CDC_WSA_COMPANDER0_CTL3, 0x80, 0x80},\n"
                "\t{BOLERO_CDC_WSA_COMPANDER1_CTL3, 0x80, 0x80},",
            ),
        }
        for section, snippets in expected_by_section.items():
            start = text.index(f"{section}[] = {{")
            body = text[start:text.index("};", start)]
            for snippet in snippets:
                self.assertTrue(snippet in body, f"Missing {snippet!r} in {section}")
        self.assertIn("e6050e513aff7380ba3e44ee2f1878e2a8941c41", PROVENANCE.read_text())


if __name__ == "__main__":
    unittest.main()
