"""
Prueba quincena_to_fecha
    Para hacer la prueba ejecute el comando `pytest` en la raíz del proyecto
"""

import unittest
from datetime import date

from lib.fechas import quincena_to_fecha


class TestQuincena(unittest.TestCase):
    """Pruebas de la función quincena_to_fecha"""

    def test_quincena_mal_formada(self):
        """Quincena mal formada"""
        self.assertRaises(ValueError, quincena_to_fecha, "AAXXYY03")

    def test_quincena_anio_fuera_rango(self):
        """Año fuera del rango permitido"""
        self.assertRaises(ValueError, quincena_to_fecha, "203002")
        self.assertRaises(ValueError, quincena_to_fecha, "180105")

    def test_quincena_quincena_fuera_rango(self):
        """Número de quincena fuera del rango permitido"""
        self.assertRaises(ValueError, quincena_to_fecha, "202200")
        self.assertRaises(ValueError, quincena_to_fecha, "202325")
        self.assertRaises(ValueError, quincena_to_fecha, "202327")

    def test_quincena_correcta_dia_primero(self):
        """Quincenas correctas con fecha de día primero"""
        self.assertEqual(quincena_to_fecha("202303"), date(2023, 2, 1))
        self.assertEqual(quincena_to_fecha("202324"), date(2023, 12, 16))

    def test_quincena_correcta_dia_ultimo(self):
        """Quincenas correctas con fecha de día último"""
        self.assertEqual(quincena_to_fecha("202304", dame_ultimo_dia=True), date(2023, 2, 28))
        self.assertEqual(quincena_to_fecha("202306", dame_ultimo_dia=True), date(2023, 3, 31))
        self.assertEqual(quincena_to_fecha("202323", dame_ultimo_dia=True), date(2023, 12, 15))


if __name__ == "__main__":
    unittest.main()
