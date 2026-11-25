#!/usr/bin/env python3
"""Pin the vendored NoMount sources to the requested upstream dev revision."""
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = Path('/home/agentuser/kernel-refs/nomount-dev')
EXPECTED_COMMIT = 'ba8e1dba7bcb49cd7b78ee2aaa8f21fa14e89b07'
BASE_RELEASE = 'v2.3.1'
VENDORED_FILES = ('Kconfig', 'Makefile', 'nomount.c', 'nomount.h')


class NoMountUpstreamRegression(unittest.TestCase):
    def test_reference_is_requested_dev_revision(self):
        commit = subprocess.check_output(
            ['git', '-C', str(REFERENCE), 'rev-parse', 'HEAD'], text=True
        ).strip()
        self.assertEqual(EXPECTED_COMMIT, commit)
        self.assertEqual('dev', subprocess.check_output(
            ['git', '-C', str(REFERENCE), 'branch', '--show-current'], text=True
        ).strip())
        self.assertEqual(BASE_RELEASE, subprocess.check_output(
            ['git', '-C', str(REFERENCE), 'describe', '--tags', '--abbrev=0', 'HEAD'],
            text=True,
        ).strip())

    def test_vendored_files_match_requested_dev(self):
        mismatches = []
        for name in VENDORED_FILES:
            expected = (REFERENCE / 'kernel/src' / name).read_bytes()
            actual = (ROOT / 'fs/nomount' / name).read_bytes()
            if actual != expected:
                mismatches.append(name)
        self.assertEqual([], mismatches, 'Outdated or locally divergent NoMount files')

    def test_provenance_records_dev_and_base_release(self):
        lines = (ROOT / 'fs/nomount/UPSTREAM').read_text().splitlines()
        fields = dict(line.split(': ', 1) for line in lines if ': ' in line)
        self.assertEqual('https://github.com/maxsteeel/nomount', fields['Upstream'])
        self.assertEqual('dev', fields.get('Branch'))
        self.assertEqual(EXPECTED_COMMIT, fields.get('Commit'))
        self.assertEqual(BASE_RELEASE, fields.get('Base release'))

    def test_kernel_tree_integration_remains_wired(self):
        self.assertIn('source "fs/nomount/Kconfig"', (ROOT / 'fs/Kconfig').read_text())
        self.assertIn('obj-$(CONFIG_NOMOUNT) += nomount/', (ROOT / 'fs/Makefile').read_text())
        self.assertIn(
            'CONFIG_NOMOUNT=y',
            (ROOT / 'arch/arm64/configs/vendor/xiaomi/chime.config').read_text(),
        )
        self.assertIn('select KEYS', (ROOT / 'fs/nomount/Kconfig').read_text())


if __name__ == '__main__':
    unittest.main(verbosity=2)
