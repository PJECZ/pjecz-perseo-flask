"""
Bitácoras, tareas en el fondo
"""

import os
from datetime import datetime, timedelta

import pytz
from dotenv import load_dotenv
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Content, Email, Mail

from .models import Bitacora

# Cargar las variables de entorno
load_dotenv()
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "")
SENDGRID_FROM_EMAIL = os.getenv("SENDGRID_FROM_EMAIL", "")
TZ = os.getenv("TZ", "America/Mexico_City")


def enviar_reporte_por_email(email: str, horas: int = 24) -> str:
    """Lanzar tarea para enviar reporte por email"""

    # Definir el tiempo de inicio como el tiempo actual menos las horas indicadas
    creado_inicio = datetime.now(tz=pytz.timezone(TZ)) - timedelta(hours=horas)

    # Consultar las bitácoras con estatus "A"
    bitacoras = Bitacora.query.filter(Bitacora.creado >= creado_inicio).filter(Bitacora.estatus == "A").all()

    # Si no hay bitácoras, salir
    if not bitacoras:
        return "No hay bitácoras activas para reportar."

    # Elaborar el asunto
    asunto_str = "Reporte de Bitácoras"

    # Elaborar el contenido del mensaje
    fecha_envio = datetime.now(tz=pytz.timezone(TZ)).strftime("%d/%b/%Y %H:%M")
    contenidos = []
    contenidos.append(f"<h2>{asunto_str}</h2>")
    contenidos.append(f"<p>Enviado el {fecha_envio}</p>")
    contenidos.append("<ul>")
    for bitacora in bitacoras:
        contenidos.append(f"<li>{bitacora.usuario.nombre} - {bitacora.descripcion}</li>")
    contenidos.append("</ul>")
    contenidos.append("<p>")
    contenidos.append("Para lograr la meta <em>CERO PAPEL</em> por favor <em>NO IMPRIMA ESTE MENSAJE ni el Oficio.</em><br>")
    contenidos.append("Este mensaje fue enviado por un programa. <em>NO RESPONDA ESTE MENSAJE.</em>")
    contenidos.append("</p>")
    contenido_html = "\n".join(contenidos)

    # Enviar el e-mail
    remitente_email = Email(SENDGRID_FROM_EMAIL)
    contenido = Content("text/html", contenido_html)
    mensaje = Mail(
        from_email=remitente_email,
        to_emails=[email],
        subject=asunto_str,
        html_content=contenido,
    )

    # Enviar mensaje de correo electrónico
    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        respuesta = sg.send(mensaje)
    except Exception as error:
        return f"Error al enviar el mensaje por Sendgrid: {str(error)}"

    # Mensaje de término
    respuesta_str = f"Status code: {respuesta.status_code}, body: {respuesta.body}, headers: {respuesta.headers}"
    return f"Se ha enviado el reporte de usuarios al correo electrónico proporcionado.\n{respuesta_str}"
