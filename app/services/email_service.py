"""Servicio de envío de email por SMTP (Gmail por defecto).

Configuración por variables de entorno (NUNCA hardcodear credenciales):
  SMTP_HOST     (default: smtp.gmail.com)
  SMTP_PORT     (default: 587, STARTTLS)
  SMTP_USER     dirección de Gmail emisora (ej. tucuenta@gmail.com)
  SMTP_PASSWORD contraseña de aplicación de Gmail (16 caracteres, requiere 2FA)
  SMTP_FROM     remitente mostrado (default: SMTP_USER)

Si no hay credenciales configuradas, send_email devuelve un resultado con
status 'not_configured' en lugar de fallar, para que el resto de la app siga
funcionando y la UI pueda avisar al usuario.
"""
import os
import smtplib
import ssl
from email.message import EmailMessage


def is_configured():
    """True si hay credenciales SMTP mínimas configuradas."""
    return bool(os.environ.get('SMTP_USER') and os.environ.get('SMTP_PASSWORD'))


def _config():
    return {
        'host': os.environ.get('SMTP_HOST', 'smtp.gmail.com'),
        'port': int(os.environ.get('SMTP_PORT', '587')),
        'user': os.environ.get('SMTP_USER', ''),
        'password': os.environ.get('SMTP_PASSWORD', ''),
        'from': os.environ.get('SMTP_FROM') or os.environ.get('SMTP_USER', ''),
    }


def send_email(to_address, subject, html_body, text_body=None):
    """Envía un email HTML.

    Returns:
        dict con 'status': 'sent' | 'not_configured' | 'error' y detalle.
    """
    if not is_configured():
        return {
            'status': 'not_configured',
            'message': (
                'El envío de email no está configurado. Define SMTP_USER y '
                'SMTP_PASSWORD (contraseña de aplicación de Gmail) en las '
                'variables de entorno.'
            ),
        }

    if not to_address:
        return {'status': 'error', 'message': 'Falta la dirección de destino'}

    cfg = _config()
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = cfg['from']
    msg['To'] = to_address
    # Cuerpo de texto alternativo + HTML
    msg.set_content(text_body or 'Tu cliente de correo no soporta HTML.')
    msg.add_alternative(html_body, subtype='html')

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(cfg['host'], cfg['port'], timeout=20) as server:
            server.starttls(context=context)
            server.login(cfg['user'], cfg['password'])
            server.send_message(msg)
        return {'status': 'sent', 'to': to_address}
    except smtplib.SMTPAuthenticationError:
        return {
            'status': 'error',
            'message': (
                'Autenticación SMTP fallida. Verifica SMTP_USER y que '
                'SMTP_PASSWORD sea una contraseña de aplicación válida de Gmail.'
            ),
        }
    except Exception as e:  # noqa: BLE001 - reportar cualquier fallo de envío
        return {'status': 'error', 'message': f'Error al enviar email: {e}'}
