"""
Permisos, formularios
"""
from flask_wtf import FlaskForm
from wtforms import SelectField, StringField, SubmitField
from wtforms.validators import DataRequired

from perseo.blueprints.conceptos.models import Concepto
from perseo.blueprints.productos.models import Producto


class ConceptoProductoNewWithConceptoForm(FlaskForm):
    """Formulario para agregar Permiso con el modulo como parametro"""

    concepto_clave = StringField("Concepto clave")  # Solo lectura
    concepto_descripcion = StringField("Concepto descripción")  # Solo lectura
    producto = SelectField("Producto", coerce=int, validators=[DataRequired()])
    guardar = SubmitField("Guardar")

    def __init__(self, *args, **kwargs):
        """Inicializar y cargar opciones para rol"""
        super().__init__(*args, **kwargs)
        self.producto.choices = [
            (p.id, f"{p.clave} - {p.descripcion}") for p in Producto.query.filter_by(estatus="A").order_by(Producto.clave).all()
        ]


class ConceptoProductoNewWithProductoForm(FlaskForm):
    """Formulario para agregar Permiso con el rol como parametro"""

    concepto = SelectField("Concepto", coerce=int, validators=[DataRequired()])
    producto_clave = StringField("Producto clave")  # Solo lectura
    producto_descripcion = StringField("Producto descripción")  # Solo lectura
    guardar = SubmitField("Guardar")

    def __init__(self, *args, **kwargs):
        """Inicializar y cargar opciones para modulo"""
        super().__init__(*args, **kwargs)
        self.concepto.choices = [
            (c.id, f"{c.clave} - {c.descripcion}") for c in Concepto.query.filter_by(estatus="A").order_by(Concepto.clave).all()
        ]
