import unittest
from vin_decoder import decode_vin

class TestVinDecoder(unittest.TestCase):
    def test_valid_vin(self):
        vin = "1HGCM82633A123456"
        data = decode_vin(vin)
        self.assertTrue(data['valid'])
        self.assertEqual(data['manufacturer'], 'Honda')
        self.assertEqual(data['country'], 'USA')
        self.assertEqual(data['year'], '2003')
        self.assertEqual(data['plant'], '3')
        self.assertEqual(data['serial'], 'A123456')

    def test_invalid_length(self):
        vin = "1HGCM82633A12345"  # 16 chars
        data = decode_vin(vin)
        self.assertFalse(data['valid'])
        self.assertIn('17 caracteres', data['error'])

    def test_invalid_checksum(self):
        vin = "1HGCM82633A123457"  # checksum incorrecto
        data = decode_vin(vin)
        self.assertFalse(data['valid'])
        self.assertIn('Checksum', data['error'])

if __name__ == "__main__":
    unittest.main()
