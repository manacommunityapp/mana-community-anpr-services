"""
tests/unit/test_plate_validator.py — Unit tests for Indian plate regex validation.
"""
import unittest
from app.core.plate_validator import validate_plate


class TestPlateValidator(unittest.TestCase):

    def test_standard_plate_maharashtra(self):
        result = validate_plate("MH12AB1234")
        self.assertTrue(result.is_valid)
        self.assertEqual(result.plate_format, "STANDARD")
        self.assertEqual(result.state_code, "MH")
        self.assertEqual(result.normalised, "MH12AB1234")

    def test_standard_plate_delhi(self):
        result = validate_plate("DL01CX5678")
        self.assertTrue(result.is_valid)
        self.assertEqual(result.state_code, "DL")

    def test_standard_plate_with_spaces(self):
        result = validate_plate("MH 12 AB 1234")
        self.assertTrue(result.is_valid)
        self.assertEqual(result.normalised, "MH12AB1234")

    def test_bh_series_plate(self):
        result = validate_plate("24BH1234A")
        self.assertTrue(result.is_valid)
        self.assertEqual(result.plate_format, "BH_SERIES")
        self.assertEqual(result.state_code, "BH")

    def test_invalid_state_code(self):
        result = validate_plate("XX12AB1234")
        self.assertFalse(result.is_valid)
        self.assertEqual(result.plate_format, "STANDARD")

    def test_garbage_text(self):
        result = validate_plate("HELLO WORLD")
        self.assertFalse(result.is_valid)
        self.assertEqual(result.plate_format, "UNKNOWN")

    def test_empty_string(self):
        result = validate_plate("")
        self.assertFalse(result.is_valid)

    def test_karnataka_plate(self):
        result = validate_plate("KA01MN9999")
        self.assertTrue(result.is_valid)
        self.assertEqual(result.state_code, "KA")

    def test_telangana_plate(self):
        result = validate_plate("TS09EA1234")
        self.assertTrue(result.is_valid)
        self.assertEqual(result.state_code, "TS")


if __name__ == "__main__":
    unittest.main()
