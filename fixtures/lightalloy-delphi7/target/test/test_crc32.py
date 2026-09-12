"""Tests for CRC32 (ported from legacy/CRC32.pas TCRC32).

Ground truth tier: snapshot (see migration/ground-truth-strategy.md).
All expected values come from
migration/behavior-snapshots/CRC32.md, which were derived from Python's
built-in `zlib.crc32` used as a language-independent external authority for
the standard CRC-32 / IEEE 802.3 algorithm (verified against the public
check value 0xCBF43926 for b"123456789"). No legacy Pascal code was
executed to produce these values -- see the snapshot file for the full
justification.

None of the assertions in this file are INFERRED; all are snapshot-derived.
"""
import io
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from crc32 import CRC32


class TestCRC32(unittest.TestCase):
    # --- Snapshot cases 1-8: table of (input bytes, expected result) ---

    def test_case1_empty_input(self):
        c = CRC32()
        c.update(b"")
        self.assertEqual(c.result(), 0x00000000)

    def test_case2_check_value_123456789(self):
        # Public CRC-32/ISO-HDLC check value for b"123456789".
        c = CRC32()
        c.update(b"123456789")
        self.assertEqual(c.result(), 0xCBF43926)

    def test_case3_single_byte_0x00(self):
        c = CRC32()
        c.update(b"\x00")
        self.assertEqual(c.result(), 0xD202EF8D)

    def test_case4_single_byte_0xff(self):
        c = CRC32()
        c.update(b"\xff")
        self.assertEqual(c.result(), 0xFF000000)

    def test_case5_all_256_byte_values(self):
        c = CRC32()
        c.update(bytes(range(256)))
        self.assertEqual(c.result(), 0x29058C73)

    def test_case6_light_alloy_string(self):
        c = CRC32()
        c.update(b"Light Alloy")
        self.assertEqual(c.result(), 0x20B206E5)

    def test_case7_lowercase_alphabet(self):
        c = CRC32()
        c.update(b"abcdefghijklmnopqrstuvwxyz")
        self.assertEqual(c.result(), 0x4C2750BD)

    def test_case8_quick_brown_fox(self):
        c = CRC32()
        c.update(b"The quick brown fox jumps over the lazy dog")
        self.assertEqual(c.result(), 0x414FA339)

    # --- Case 9: accumulation semantics across multiple update() calls ---

    def test_case9_update_accumulates_across_calls(self):
        # UpdateWithBuffer does not reset Sum between calls, so splitting
        # the input across multiple update() calls must equal a single
        # update() call with the concatenated input (same expected value
        # as case 6, b"Light Alloy" == b"Light " + b"Alloy").
        c = CRC32()
        c.update(b"Light ")
        c.update(b"Alloy")
        self.assertEqual(c.result(), 0x20B206E5)

    # --- Case 10: UpdateWithStream semantics ---

    def test_case10_update_stream_equivalent_to_update(self):
        # UpdateWithStream seeks to 0 and reads the whole stream in chunks,
        # which is equivalent to update() on the full stream contents.
        c = CRC32()
        stream = io.BytesIO(b"Light Alloy")
        c.update_stream(stream)
        self.assertEqual(c.result(), 0x20B206E5)

    # --- Case 11: reset() semantics ---

    def test_case11_reset_clears_accumulated_state(self):
        # After update() + reset(), a subsequent update() must reflect only
        # the data fed after reset(), with no leftover state from before.
        c = CRC32()
        c.update(b"garbage")
        c.reset()
        c.update(b"123456789")
        self.assertEqual(c.result(), 0xCBF43926)


if __name__ == "__main__":
    unittest.main()
