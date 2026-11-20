"""Minimal source/model regression for dedup release accounting.

This validates the real kernel source's API/call-site guard plus one duplicate
entry's reference-count sequence. It is not an on-device performance benchmark.
Run: python3 tools/test_zram_dedup_accounting.py
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
DRIVER = ROOT / "drivers/block/zram/zram_drv.c"
HEADER = ROOT / "drivers/block/zram/zram_drv.h"


def function_body(source, name):
    # Skip a prototype before finding the definition. zram_free_page() has a
    # forward declaration; a simple "first brace after name" extract can
    # otherwise incorrectly return some unrelated helper's body.
    for match in re.finditer(r"(?:void|bool)\s+" + re.escape(name) + r"\s*\(", source):
        brace = source.find("{", match.end())
        semicolon = source.find(";", match.end())
        if semicolon != -1 and (brace == -1 or semicolon < brace):
            continue
        if brace < 0:
            continue
        depth = 0
        for pos in range(brace, len(source)):
            if source[pos] == "{":
                depth += 1
            elif source[pos] == "}":
                depth -= 1
                if depth == 0:
                    return source[brace + 1:pos]
    raise AssertionError("function definition not found: " + name)


def normalized(text):
    return " ".join(text.split())


class ZramDedupAccountingTest(unittest.TestCase):
    def setUp(self):
        self.driver = DRIVER.read_text()
        self.free_body = normalized(function_body(self.driver, "zram_entry_free"))
        self.page_body = normalized(function_body(self.driver, "zram_free_page"))

    def test_free_propagates_retained_entry(self):
        self.assertTrue(self.driver.lstrip().find("void zram_entry_free(") < 0,
                        "zram_entry_free must return whether it released the allocation")
        self.assertTrue(re.search(r"\bbool\s+zram_entry_free\s*\(", self.driver))
        self.assertIn("if (!zram_dedup_put_entry(zram, entry)) return false;",
                      self.free_body)

    def test_free_reports_actual_allocation_release(self):
        self.assertIn("zs_free(zram->mem_pool, zram_entry_handle(zram, entry));",
                      self.free_body)
        self.assertTrue(self.free_body.rstrip().endswith("return true;"),
                        "all actual physical-release exits need true; retained refcount needs false")

    def test_free_page_subtracts_only_for_last_reference(self):
        self.assertIn(
            "if (zram_entry_free(zram, entry)) "
            "atomic64_sub(zram_get_obj_size(zram, index), "
            "&zram->stats.compr_data_size);",
            self.page_body)

    def test_internal_declaration_matches(self):
        header = HEADER.read_text()
        self.assertIsNotNone(re.search(r"\bbool\s+zram_entry_free\s*\(", header),
                             "zram_dedup.c includes this declaration; void/bool mismatch is ABI-unsafe")

    def test_observed_counter_is_a_genuine_unsigned_underflow(self):
        # The actual mm_stat sample supplied by the device owner (second column).
        observed = 18446744073090614562
        signed = observed - (1 << 64) if observed >= (1 << 63) else observed
        self.assertLess(signed, 0)
        self.assertEqual(signed, -618937054)

    def test_duplicate_release_sequence_has_one_compression_subtraction(self):
        # Creation of a unique compressed entry adds len once. A duplicate
        # reference doesn't allocate/add compr_data_size again.
        original_compressed = 80
        compr = original_compressed
        refs = 1
        freed = []
        refs += 1  # zram_dedup_find() pins a second logical page.
        for _ in range(2):  # release first and then second logical page
            refs -= 1
            freed.append(refs == 0)
            if refs == 0:  # the only valid subtraction point
                compr -= original_compressed
        self.assertEqual(freed, [False, True])
        self.assertEqual(compr, 0)
        # Two logical reference releases, with only one physical free/subtraction.
        self.assertEqual(len(freed), 2)


if __name__ == "__main__":
    unittest.main()
