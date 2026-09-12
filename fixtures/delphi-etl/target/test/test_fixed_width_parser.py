"""Unit tests for fixed_width_parser.parse_sales_line.

These tests are derived from the legacy Delphi unit
legacy/FixedWidthParser.pas (function ParseSalesLine). Expected values were
obtained by actually compiling and running the legacy Pascal logic with the
Free Pascal Compiler (fpc 3.2.2), not by reading the source and guessing.
See the accompanying behavior notes for exactly which observations back
which assertions, and which edge cases were deliberately left untested or
resolved via a conservative assumption because Delphi's real (dcc32/dcc64)
runtime was not available to verify against.

Column layout (1-based in Pascal, converted to 0-based Python slices per
RULEBOOK#1: Copy(s, start, len) -> s[start-1 : start-1+len]):
    1-10   CustomerId  -> line[0:10]   (space padded, trimmed)
    11-14  Year         -> line[10:14]
    15-16  Month         -> line[14:16]
    17-18  Day           -> line[16:18]
    19-28  AmountCents  -> line[18:28] (zero-padded integer cents)
    29-30  CurrencyCode -> line[28:30] (raw, not normalized/trimmed)
"""

import os
import sys
import unittest

_SRC_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "src")
)
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from fixed_width_parser import parse_sales_line  # noqa: E402


class ParseSalesLineTests(unittest.TestCase):
    def test_normal_line_is_parsed_field_by_field(self):
        # fpc output:
        #   CustomerId=[CUST0001] SaleDate=[2024-01-15]
        #   AmountCents=1234567890 CurrencyCode=[US]
        line = "CUST0001  202401151234567890US"
        result = parse_sales_line(line)
        self.assertEqual(
            result,
            {
                "customer_id": "CUST0001",
                "sale_date": "2024-01-15",
                "amount_cents": 1234567890,
                "currency_code": "US",
            },
        )

    def test_short_customer_id_is_right_padded_and_trimmed(self):
        # fpc output:
        #   CustomerId=[ABC] SaleDate=[2023-12-31]
        #   AmountCents=12345 CurrencyCode=[JP]
        line = "ABC       202312310000012345JP"
        result = parse_sales_line(line)
        self.assertEqual(
            result,
            {
                "customer_id": "ABC",
                "sale_date": "2023-12-31",
                "amount_cents": 12345,
                "currency_code": "JP",
            },
        )

    def test_all_blank_customer_id_becomes_empty_string(self):
        # fpc output: CustomerId=[] SaleDate=[2024-01-01]
        #             AmountCents=0 CurrencyCode=[ZZ]
        line = "          202401010000000000ZZ"
        result = parse_sales_line(line)
        self.assertEqual(
            result,
            {
                "customer_id": "",
                "sale_date": "2024-01-01",
                "amount_cents": 0,
                "currency_code": "ZZ",
            },
        )

    def test_customer_id_trim_only_strips_outer_whitespace(self):
        # Trim() only removes leading/trailing whitespace, internal spaces
        # inside the 10-char field are preserved.
        # fpc output: CustomerId=[LEAD  TR] SaleDate=[2024-01-15]
        #             AmountCents=12345 CurrencyCode=[US]
        line = "  LEAD  TR202401150000012345US"
        result = parse_sales_line(line)
        self.assertEqual(
            result,
            {
                "customer_id": "LEAD  TR",
                "sale_date": "2024-01-15",
                "amount_cents": 12345,
                "currency_code": "US",
            },
        )

    def test_amount_field_with_leading_space_still_parses(self):
        # StrToInt (and Python's int()) tolerate a leading space in the
        # numeric text.
        # fpc output: AmountCents=12345 CurrencyCode=[US]
        line = "CUST0001  20240115 000012345US"
        result = parse_sales_line(line)
        self.assertEqual(result["amount_cents"], 12345)
        self.assertEqual(result["currency_code"], "US")

    def test_currency_code_is_not_normalized_or_trimmed(self):
        # ParseSalesLine copies the raw 2 chars verbatim; case/region
        # normalization happens elsewhere (CurrencyRules unit), not here.
        # fpc output: CurrencyCode=[us]
        line = "CUST0001  202401150000012345us"
        result = parse_sales_line(line)
        self.assertEqual(result["currency_code"], "us")

    def test_line_shorter_than_currency_column_yields_empty_currency_code(self):
        # Copy() on an out-of-range slice does not raise; it returns
        # whatever is available (here: nothing for columns 29-30).
        # fpc output: CustomerId=[CUST0001] SaleDate=[2024-01-15]
        #             AmountCents=12345 CurrencyCode=[]
        line = "CUST0001  202401150000012345"  # 28 chars, no currency cols
        result = parse_sales_line(line)
        self.assertEqual(
            result,
            {
                "customer_id": "CUST0001",
                "sale_date": "2024-01-15",
                "amount_cents": 12345,
                "currency_code": "",
            },
        )

    def test_trailing_characters_past_column_30_are_ignored(self):
        # Copy() only ever takes the requested width; extra trailing text
        # in the source line beyond column 30 has no effect.
        # fpc output: CurrencyCode=[US] (the trailing "EXTRA" is dropped)
        line = "CUST0001  202401150000012345USEXTRA"
        result = parse_sales_line(line)
        self.assertEqual(result["currency_code"], "US")

    def test_non_numeric_amount_field_raises(self):
        # fpc output: EXCEPTION: EConvertError: "ABCDEFGHIJ" is an invalid
        # integer. RULEBOOK#3: StrToInt -> int(), both must raise on
        # failure, not be caught/defaulted.
        line = "CUST0002  20240115ABCDEFGHIJUS"
        with self.assertRaises(ValueError):
            parse_sales_line(line)

    def test_line_too_short_to_contain_amount_raises(self):
        # fpc output: EXCEPTION: EConvertError: "" is an invalid integer
        # (Copy returns an empty string for the missing amount columns,
        # and StrToInt('') fails rather than defaulting to 0).
        line = "X101"
        with self.assertRaises(ValueError):
            parse_sales_line(line)

    def test_empty_line_raises(self):
        # fpc output: EXCEPTION: EConvertError: "" is an invalid integer
        line = ""
        with self.assertRaises(ValueError):
            parse_sales_line(line)

    def test_large_amount_value_is_not_truncated(self):
        # ASSUMPTION (see behavior notes): real Delphi (dcc32/dcc64) was
        # not available to verify 32-bit Integer overflow semantics for
        # StrToInt. FPC 3.2.2 silently wraps this 10-digit value to
        # 1410065407 (32-bit two's-complement overflow), but RULEBOOK#3/#4
        # give no instruction to reproduce integer-width truncation, and
        # Python's int() is arbitrary precision. We conservatively assert
        # the direct, non-overflowing parse of the digit string, matching
        # a straightforward int() translation rather than the
        # compiler-specific FPC wraparound artifact.
        line = "CUST0003  202401159999999999US"
        result = parse_sales_line(line)
        self.assertEqual(result["amount_cents"], 9999999999)


if __name__ == "__main__":
    unittest.main()
