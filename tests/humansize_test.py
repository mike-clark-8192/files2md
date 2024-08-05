import unittest
import files2md.cli.humansize

humansize_to_size = files2md.cli.humansize.humansize_to_size


class TestBinaryPrefix(unittest.TestCase):
    def test_generate_binaryprefix_to_size_dict(self):
        expected = {
            "": 1,
            "K": 1000,
            "M": 1000000,
            "G": 1000000000,
            "T": 1000000000000,
            "P": 1000000000000000,
            "E": 1000000000000000000,
            "Ki": 1024,
            "Mi": 1048576,
            "Gi": 1073741824,
            "Ti": 1099511627776,
            "Pi": 1125899906842624,
            "Ei": 1152921504606846976,
        }
        actual = files2md.cli.humansize.generate_binaryprefix_to_size_dict()
        for expected_key, expected_value in expected.items():
            self.assertEqual(expected_value, actual[expected_key])

    def test_humansize_to_size(self):
        # Test valid inputs (no unit)
        self.assertEqual(humansize_to_size("1"), 1)
        self.assertEqual(humansize_to_size("1K"), 1000)
        self.assertEqual(humansize_to_size("1Ki"), 1024)
        self.assertEqual(humansize_to_size("1M"), 1000000)
        self.assertEqual(humansize_to_size("1Mi"), 1048576)
        self.assertEqual(humansize_to_size("1G"), 1000000000)
        self.assertEqual(humansize_to_size("1Gi"), 1073741824)
        self.assertEqual(humansize_to_size("1T"), 1000000000000)
        self.assertEqual(humansize_to_size("1Ti"), 1099511627776)
        self.assertEqual(humansize_to_size("1P"), 1000000000000000)
        self.assertEqual(humansize_to_size("1Pi"), 1125899906842624)
        self.assertEqual(humansize_to_size("1E"), 1000000000000000000)
        self.assertEqual(humansize_to_size("1Ei"), 1152921504606846976)

        # Test valid inputs (valid unti)
        self.assertEqual(humansize_to_size("1"), 1)
        self.assertEqual(humansize_to_size("1KB"), 1000)
        self.assertEqual(humansize_to_size("1KiB"), 1024)
        self.assertEqual(humansize_to_size("1MB"), 1000000)
        self.assertEqual(humansize_to_size("1MiB"), 1048576)
        self.assertEqual(humansize_to_size("1GB"), 1000000000)
        self.assertEqual(humansize_to_size("1GiB"), 1073741824)
        self.assertEqual(humansize_to_size("1TB"), 1000000000000)
        self.assertEqual(humansize_to_size("1TiB"), 1099511627776)
        self.assertEqual(humansize_to_size("1PB"), 1000000000000000)
        self.assertEqual(humansize_to_size("1PiB"), 1125899906842624)
        self.assertEqual(humansize_to_size("1EB"), 1000000000000000000)
        self.assertEqual(humansize_to_size("1EiB"), 1152921504606846976)

        # Test case-insensitivity
        self.assertEqual(humansize_to_size("1k"), 1000)
        self.assertEqual(humansize_to_size("1ki"), 1024)
        self.assertEqual(humansize_to_size("1m"), 1000000)
        self.assertEqual(humansize_to_size("1mi"), 1048576)
        self.assertEqual(humansize_to_size("1g"), 1000000000)
        self.assertEqual(humansize_to_size("1gi"), 1073741824)
        self.assertEqual(humansize_to_size("1t"), 1000000000000)
        self.assertEqual(humansize_to_size("1ti"), 1099511627776)
        self.assertEqual(humansize_to_size("1p"), 1000000000000000)
        self.assertEqual(humansize_to_size("1pi"), 1125899906842624)
        self.assertEqual(humansize_to_size("1e"), 1000000000000000000)
        self.assertEqual(humansize_to_size("1ei"), 1152921504606846976)

        # Test unusual case variations
        self.assertEqual(humansize_to_size("1kI"), 1024)
        self.assertEqual(humansize_to_size("1KI"), 1024)
        self.assertEqual(humansize_to_size("1mI"), 1048576)
        self.assertEqual(humansize_to_size("1MI"), 1048576)
        self.assertEqual(humansize_to_size("1gI"), 1073741824)
        self.assertEqual(humansize_to_size("1GI"), 1073741824)

        def _assertRaises(humansize: str, expected_size: int):
            with self.assertRaises(ValueError):
                humansize_to_size(humansize)

        # function currently will reject 'b' as a unit
        _assertRaises(("1b"), 1)
        _assertRaises(("1Kb"), 1000)
        _assertRaises(("1Kib"), 1024)
        _assertRaises(("1Mb"), 1000000)
        _assertRaises(("1Mib"), 1048576)
        _assertRaises(("1Gb"), 1000000000)
        _assertRaises(("1Gib"), 1073741824)
        _assertRaises(("1Tb"), 1000000000000)
        _assertRaises(("1Tib"), 1099511627776)
        _assertRaises(("1Pb"), 1000000000000000)
        _assertRaises(("1Pib"), 1125899906842624)
        _assertRaises(("1Eb"), 1000000000000000000)
        _assertRaises(("1Eib"), 1152921504606846976)

        # Test invalid inputs
        with self.assertRaises(ValueError):
            humansize_to_size("1kb")  # Ambiguous unit
        with self.assertRaises(ValueError):
            humansize_to_size("1X")  # Unknown binary prefix
        with self.assertRaises(ValueError):
            humansize_to_size("1Xb")
        with self.assertRaises(ValueError):
            humansize_to_size("1Xib")
        with self.assertRaises(ValueError):
            humansize_to_size("KB")  # No number


if __name__ == "__main__":
    unittest.main()
