"""
Prueba quincena_count
"""

import unittest
from datetime import date

from lib.fechas import quincena_count


class TestQuincenaCount(unittest.TestCase):
    """Pruebas para la función quincena_count"""

    def test_fecha(self):
        """Pruebas exitosas"""
        self.assertEqual(quincena_count(date(2023, 2, 28), date(2023, 2, 1)), 1)
        self.assertEqual(quincena_count(date(2021, 2, 14), date(2023, 4, 30)), 53)


if __name__ == "__main__":
    unittest.main()
