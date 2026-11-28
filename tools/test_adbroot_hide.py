#!/usr/bin/env python3
"""Keep the adbroot DirtySepolicy mask narrow and inside selinux_hide."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "KernelSU/feature/selinux_hide/selinux_hide_auto.c"
REFERENCE = "Mohithash/kernel_xiaomi_sm8635@4f00f1dc16f67fc60bedcfa95ee8d5b36d1078b9"


class AdbrootHideTest(unittest.TestCase):
    def test_only_adbd_adbroot_binder_call_is_masked(self) -> None:
        text = SOURCE.read_text()
        missing = [token for token in (
            "ksu_mask_adbroot_access",
            'strcmp(scon, "u:r:adbd:s0")',
            'strcmp(tcon, "u:r:adbroot:s0")',
            "tclass != SECCLASS_BINDER",
            "avd->allowed &= ~BINDER__CALL",
        ) if token not in text]
        self.assertEqual([], missing)
        self.assertNotIn("avd.allowed = 0; /* deny adbd->adbroot", text)

    def test_mask_runs_after_backup_query_and_before_response(self) -> None:
        text = SOURCE.read_text()
        call = "ksu_mask_adbroot_access(scon, tcon, tclass, &avd);"
        self.assertIn(call, text)
        self.assertLess(text.index("#endif", text.index("ksu_security_compute_av_user")), text.index(call))
        self.assertLess(text.index(call), text.index("avd.seqno = 1;", text.index(call)))
        self.assertLess(text.index(call), text.index("length = scnprintf", text.index(call)))

    def test_reference_is_recorded(self) -> None:
        upstream = (ROOT / "KernelSU/UPSTREAM").read_text()
        self.assertIn(REFERENCE, upstream)


if __name__ == "__main__":
    unittest.main()
