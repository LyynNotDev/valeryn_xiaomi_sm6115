#!/usr/bin/env python3
"""Guard the isolated BakaSU + SUSFS + NoMount spike for chime 4.19."""

from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = Path("/home/agentuser/kernel-refs/bakasu-upstream")
EXPECTED_COMMIT = "57b2db6076f439cfd489f14576444e8f0f2f0a25"
EXPECTED_VERSION = "35285"
LOCAL_BUILD_FILES = {
    Path("Kbuild"),
    Path("tools/code_generation/preinit_runner/preinit_runner.mk"),
}
UPSTREAM_NON_RUNTIME_FILES = {Path(".clangd.example")}
UPSTREAM_NON_RUNTIME_DIRS = {".vscode"}
SUSFS_FEATURES = (
    "SUS_PATH", "SUS_MOUNT", "SUS_KSTAT", "SPOOF_UNAME", "ENABLE_LOG",
    "HIDE_KSU_SUSFS_SYMBOLS", "SPOOF_CMDLINE_OR_BOOTCONFIG",
    "OPEN_REDIRECT", "SUS_MAP", "PRIORITY_UID_FILTER",
)


class BakaSUSpikeTest(unittest.TestCase):
    def test_reference_is_pinned_main(self) -> None:
        self.assertEqual(
            EXPECTED_COMMIT,
            subprocess.check_output(
                ["git", "-C", str(REFERENCE), "rev-parse", "HEAD"], text=True
            ).strip(),
        )
        self.assertEqual(
            "main",
            subprocess.check_output(
                ["git", "-C", str(REFERENCE), "branch", "--show-current"], text=True
            ).strip(),
        )

    def test_vendored_driver_matches_upstream_except_version_pinning(self) -> None:
        mismatches = []
        for source in (REFERENCE / "kernel").rglob("*"):
            if not source.is_file():
                continue
            relative = source.relative_to(REFERENCE / "kernel")
            if relative in LOCAL_BUILD_FILES or relative in UPSTREAM_NON_RUNTIME_FILES:
                continue
            if relative.parts and relative.parts[0] in UPSTREAM_NON_RUNTIME_DIRS:
                continue
            actual = ROOT / "KernelSU" / relative
            if not actual.is_file() or actual.read_bytes() != source.read_bytes():
                mismatches.append(str(relative))
        self.assertEqual([], mismatches)

    def test_vendored_uapi_matches_upstream(self) -> None:
        mismatches = []
        for source in (REFERENCE / "uapi").rglob("*"):
            if not source.is_file():
                continue
            relative = source.relative_to(REFERENCE / "uapi")
            actual = ROOT / "KernelSU/uapi" / relative
            if not actual.is_file() or actual.read_bytes() != source.read_bytes():
                mismatches.append(str(relative))
        self.assertEqual([], mismatches)
        self.assertIn(
            "KERNEL_SU_UAPI_VERSION",
            (ROOT / "KernelSU/uapi/supercall.h").read_text(),
        )

    def test_driver_version_is_pinned_not_inherited_from_chime_git(self) -> None:
        kbuild = (ROOT / "KernelSU/Kbuild").read_text()
        self.assertIn(f"KSU_VERSION := {EXPECTED_VERSION}", kbuild)
        self.assertIn("KSU_COMMIT_SHA := 57b2db60", kbuild)
        self.assertIn("KSU_TAG_NAME := v4.2.0-rc3", kbuild)
        upstream = (ROOT / "KernelSU/UPSTREAM").read_text()
        self.assertIn(EXPECTED_COMMIT, upstream)

    def test_preinit_runner_include_covers_vendored_uapi(self) -> None:
        makefile = (
            ROOT / "KernelSU/tools/code_generation/preinit_runner/preinit_runner.mk"
        ).read_text()
        self.assertIn("-I$(KSU_RUNNER_SRC)/nolibc -I$(KSU_SRC)", makefile)
        self.assertTrue((ROOT / "KernelSU/uapi/supercall.h").is_file())

    def test_full_config_preserves_chime_susfs_and_nomount_preferences(self) -> None:
        config = (
            ROOT / "arch/arm64/configs/vendor/xiaomi/chime.config"
        ).read_text().splitlines()
        self.assertIn("CONFIG_KSU=y", config)
        self.assertIn("CONFIG_KSU_SUSFS=y", config)
        self.assertIn("CONFIG_KSU_MULTI_MANAGER_SUPPORT=y", config)
        self.assertIn("CONFIG_NOMOUNT=y", config)
        for feature in SUSFS_FEATURES:
            with self.subTest(feature=feature):
                self.assertIn(f"CONFIG_KSU_SUSFS_{feature}=y", config)
        self.assertNotIn("CONFIG_KSU_MANUAL_HOOK=y", config)
        self.assertNotIn("CONFIG_KSU_TAMPER_SYSCALL_TABLE=y", config)

    def test_build_script_checks_full_feature_options(self) -> None:
        script = (ROOT / "build-chime.sh").read_text()
        self.assertIn("CONFIG_KSU_SUSFS=y", script)
        self.assertIn("CONFIG_KSU_MULTI_MANAGER_SUPPORT=y", script)
        self.assertIn("CONFIG_KSU_SUSFS_SUS_PATH=y", script)
        self.assertIn("CONFIG_KSU_SUSFS_PRIORITY_UID_FILTER=y", script)
        self.assertIn("CONFIG_NOMOUNT=y", script)
        self.assertNotIn("CONFIG_KSU_TAMPER_SYSCALL_TABLE=y", script)

    def test_ksu_domain_bridge_has_exactly_one_owner(self) -> None:
        definition = "bool susfs_is_current_ksu_domain(void)\n{"
        susfs = (ROOT / "fs/susfs.c").read_text()
        bakasu = (ROOT / "KernelSU/selinux/selinux.c").read_text()
        self.assertEqual(1, susfs.count(definition) + bakasu.count(definition))
        self.assertNotIn("SUSFS root-domain bridge for backslashxx", susfs)
        self.assertIn(definition, bakasu)

    def test_execve_sucompat_else_belongs_to_decryption_check(self) -> None:
        source = (ROOT / "fs/exec.c").read_text()
        expected = """\tif (static_branch_likely(&ksu_su_compat_enabled)) {
\t\tif (static_branch_unlikely(&susfs_is_sdcard_android_data_not_decrypted)) {
\t\t\tis_su_session = !ksu_handle_execveat(&fd, &filename, &argv, &envp, &flags);
\t\t} else {
\t\t\tis_su_session = !ksu_handle_execveat_sucompat(&fd, &filename, &argv, &envp, &flags);
\t\t}
\t}"""
        self.assertTrue(expected in source, "decrypted-state else must call sucompat inside the enabled branch")
        wrong_outer_else = """\t\t\tis_su_session = !ksu_handle_execveat(&fd, &filename, &argv, &envp, &flags);
\t} else {
\t\tis_su_session = !ksu_handle_execveat_sucompat"""
        self.assertNotIn(wrong_outer_else, source, "sucompat must not be attached to the disabled outer branch")

    def test_required_susfs_inline_hooks_are_wired(self) -> None:
        required = {
            "fs/exec.c": ("is_su_session", "ksu_handle_execveat_sucompat"),
            "fs/open.c": ("ksu_handle_faccessat(&dfd, &fname, &mode, NULL)",),
            "fs/read_write.c": ("ksu_handle_sys_read(fd, &buf, &count)",),
            "fs/stat.c": (
                "ksu_handle_stat(&dfd, &fname, &flags)",
                "ksu_handle_vfs_fstat(fd, &stat->size)",
            ),
            "drivers/input/input.c": (
                "ksu_handle_input_handle_event(&type, &code, &value)",
            ),
            "kernel/sys.c": ("ksu_handle_setresuid(ruid, euid, suid)",),
            "kernel/reboot.c": ("system_state == SYSTEM_RUNNING",),
        }
        for name, snippets in required.items():
            text = (ROOT / name).read_text()
            self.assertIn("CONFIG_KSU_SUSFS", text, name)
            for snippet in snippets:
                with self.subTest(file=name, snippet=snippet):
                    self.assertIn(snippet, text)


if __name__ == "__main__":
    unittest.main()
