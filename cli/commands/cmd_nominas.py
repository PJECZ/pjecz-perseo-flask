"""
CLI Nominas

Columnas a entregar

- Centro de trabajo
- RFC
- Nombre completo
- Banco administrador, su clave
- Nombre del banco
- Numero de cuenta
- Monto a depositar, columna (IMPTE)
- Numero de empleado
- Quincena
- Modelo
- No de cheque (Clave del banco + secuencia) deben ser 9 digitos

"""
import click


@click.group()
def cli():
    """Nominas"""


@click.command()
@click.argument("quincena", type=str)
def alimentar(quincena: str):
    """Alimentar nominas"""


cli.add_command(alimentar)
