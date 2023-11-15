"""
Prueba quinquenio
    Para hacer la prueba ejecute el comando `pytest` en la raíz del proyecto
"""
import unittest
from datetime import date

from lib.fechas import quinquenio_count


class TestQuinquenio(unittest.TestCase):
    """Pruebas de la función quinqenio_count"""

    def test_quinquenio(self):
        """Quinquenios"""
        self.assertEqual(quinquenio_count(date(2022, 5, 30), date(2023, 11, 12)), 0, "No llega a cumplir un quinquenio")
        self.assertEqual(quinquenio_count(date(2023, 11, 1), date(2018, 7, 28)), 1, "Fechas invertidas")
        self.assertEqual(quinquenio_count(date(2023, 1, 1), date(2023, 1, 1)), 0, "Fechas iguales")
        self.assertEqual(quinquenio_count(date(2013, 1, 1), date(2023, 2, 28)), 2, "Cumple dos quinquenios")
        self.assertEqual(quinquenio_count(date(2013, 1, 2), date(2023, 1, 1)), 1, "Al borde de cumplir 2 quinquenios")
        self.assertEqual(quinquenio_count(date(1983, 1, 1), date(2023, 5, 5)), 6, "Máximo de 6 quinquenios")


if __name__ == "__main__":
    unittest.main()
