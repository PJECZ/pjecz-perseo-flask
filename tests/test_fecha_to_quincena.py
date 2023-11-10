"""
Prueba fecha_to_quincena
"""

import unittest
from datetime import date

from lib.fechas import fecha_to_quincena


class TestFechaToQuincena(unittest.TestCase):
    """Pruebas para la función fecha_to_quincena"""

    def test_fecha(self):
        """Pruebas exitosas"""
        self.assertEqual(fecha_to_quincena(date(2023, 2, 28)), "202304")
        self.assertEqual(fecha_to_quincena(date(2023, 11, 10)), "202321")
        self.assertEqual(fecha_to_quincena(date(2023, 1, 15)), "202301")
        self.assertEqual(fecha_to_quincena(date(2023, 3, 16)), "202306")


if __name__ == "__main__":
    unittest.main()
