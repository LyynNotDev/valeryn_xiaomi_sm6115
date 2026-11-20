#!/usr/bin/env python3
"""Host-only regression checks for mamboSU manager compatibility.

This verifies the exact identity published by mamboSU's documented xxksu
integration branch while preserving all existing manager identities.
It is not an on-device manager functionality test.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = Path('/home/agentuser/kernel-refs/mambosu-xxksu')
EXPECTED = {
    'KSU_PACKAGE_NAME': 'com.rapli.mambosu',
    'KSU_EXPECTED_SIZE': '0x384',
    'KSU_EXPECTED_HASH': 'a9462b8b98ea1ca7901b0cbdcebfaa35f0aa95e51b01d66e6b6d2c81b97746d8',
}
REFERENCE_COMMIT = '95d8c89e37fbf7b80a961d22b7830afade5ce94d'


class MamboManagerRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.signer = (ROOT / 'KernelSU/manager/apk_sign.c').read_text()
        cls.tracker = (ROOT / 'KernelSU/manager/throne_tracker.c').read_text()
        cls.makefile = (ROOT / 'KernelSU/Makefile').read_text()
        reference_makefile = (REFERENCE / 'kernel/Makefile').read_text()
        cls.reference = {}
        for key, value in EXPECTED.items():
            match = re.search(rf'^{key}\s*:?=\s*(\S+)', reference_makefile, re.M)
            assert match, f'{key} missing from the real mamboSU reference'
            cls.reference[key] = match.group(1)

    def test_pinned_reference_data(self):
        self.assertEqual(EXPECTED, self.reference,
                         'Reference identity changed; verify a newer signed manager first')

    def test_mambo_manager_apk_identity(self):
        expected = re.compile(
            rf'check_v2_signature\(path,\s*{EXPECTED["KSU_EXPECTED_SIZE"]},\s*"{EXPECTED["KSU_EXPECTED_HASH"]}"\)')
        self.assertIsNotNone(expected.search(self.signer),
                             'The exact mamboSU signer is missing from backslashxx')
        # The original 1024-byte allocation already accommodates this smaller cert.
        self.assertLess(int(EXPECTED['KSU_EXPECTED_SIZE'], 16), 1024)
        match = re.search(r'#define CERT_MAX_LENGTH (\d+)', self.signer)
        self.assertIsNotNone(match)
        self.assertGreaterEqual(int(match.group(1)), int(EXPECTED['KSU_EXPECTED_SIZE'], 16))

    def test_mambo_namespace_is_candidate(self):
        self.assertIn('is_mambosu_apk(tgt)', self.tracker)
        self.assertIn('extra_manager_apk(tgt, "com.rapli.mambosu")', self.tracker)

    def test_existing_managers_and_default_priority_survive(self):
        self.assertIn('is_kowsu_apk(tgt)', self.tracker)
        self.assertIn('is_midorisu_apk(tgt)', self.tracker)
        for value in (
            '484fcba6e6c43b1fb09700633bf2fb4758f13cb0b2f4457b80d075084b26c588',
            'b9ee6759de4794f954883458b722b97ae6527cb7709a051db9a2348c0eea1e42',
            'KSU_PACKAGE_NAME := me.weishu.kernelsu',
        ):
            self.assertTrue(value in self.signer or value in self.makefile)

    def test_scoped_uapi_five_negotiation(self):
        dispatch = (ROOT / 'KernelSU/supercall/dispatch.c').read_text()
        self.assertIn('if (ksu_is_mambosu_compat_manager())', dispatch)
        self.assertIn('cmd.uapi_version = 5;', dispatch)
        self.assertIn('ksu_is_mambosu_compat_manager(void)',
                      (ROOT / 'KernelSU/manager/throne_tracker.h').read_text())
        # The privilege-crowned caller must be the same UID that requests compat.
        self.assertIn('ksu_mambosu_compat_appid == current_uid().val % KSU_PER_USER_RANGE',
                      self.tracker)
        # Other managers retain the real driver protocol, not a global downgrade.
        default_assignment = dispatch.index('cmd.uapi_version = KERNEL_SU_UAPI_VERSION;')
        compat_assignment = dispatch.index('if (ksu_is_mambosu_compat_manager())')
        self.assertLess(default_assignment, compat_assignment,
                        'UAPI 6 must be assigned before the scoped UAPI 5 override')

    def test_crown_binds_verified_apk_to_its_own_uid(self):
        self.assertIn('get_pkg_from_apk_dir_path(pkg, apk)', self.tracker)
        self.assertIn('strncmp(np->package, pkg, KSU_MAX_PACKAGE_NAME) == 0', self.tracker)
        self.assertIn('ksu_mambosu_compat_appid = np->uid % KSU_PER_USER_RANGE',
                      self.tracker)

    def test_uninstalled_mambo_loses_legacy_version_negotiation(self):
        self.assertIn('!is_uid_exist(ksu_mambosu_compat_appid, "com.rapli.mambosu", &uid_list)',
                      self.tracker)
        self.assertIn('ksu_mambosu_compat_appid = KSU_INVALID_APPID', self.tracker)

    def test_only_backslash_protocol_scope_preserved(self):
        relevant = '\n'.join(p.read_text(errors='replace') for p in
                             [ROOT / 'KernelSU/Makefile', ROOT / 'KernelSU/Kconfig'])
        self.assertEqual('me.weishu.kernelsu',
                         re.search(r'KSU_PACKAGE_NAME := (\S+)', relevant).group(1))
        self.assertNotIn('CONFIG_KPM', relevant)


if __name__ == '__main__':
    unittest.main(verbosity=2)
