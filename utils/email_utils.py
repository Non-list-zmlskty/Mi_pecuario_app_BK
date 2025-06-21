import os
import smtplib
from email.mime.text import MIMEText
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage

def send_reset_email(email, token):
    # ...lógica de envío de email de reseteo...
    pass

def send_reset_code_email(email, code):
    SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
    SMTP_USER = os.getenv('SMTP_USER')
    SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')
    subject = str(Header("Peticion de codigo de recuperacion M.P.A", "utf-8"))
    # Ruta local del banner
    banner_path = r"c:\Users\Nslksss\Pictures\IMG_MPA_EMAIL\Banner 1 Pecuario App.png"
    body = f"""
    <div style='font-family: Arial, sans-serif; background: #faf6e7; padding: 24px;'>
        <div style='text-align:center; margin-bottom:24px;'>
            <img src='cid:bannerpecuario' alt='MiPecuarioApp' style='max-width:400px; border-radius:8px;'>
        </div>
        <h2 style='color:#333;'>Código de verificación MiPecuarioApp: {code}</h2>
        <p>Estimado/a: <b>{email}</b></p>
        <p>Esperamos se encuentre bien. Hemos recibido una solicitud para el cambio de tu contraseña.</p>
        <p><b>Código de verificación:</b></p>
        <p style='font-size:2em; color:#27ae60; font-weight:bold;'>{code}</p>
        <p>Ingresa el código en la aplicación para demostrar que eres tú.</p>
        <p style='color:#888;'>Si no solicitaste este código, ignora este correo.</p>
        <br>
        <p>Atentamente,<br>El equipo de programación M.P.A.</p>
    </div>
    """
    msg = MIMEMultipart()
    msg['Subject'] = subject
    msg['From'] = SMTP_USER
    msg['To'] = email
    msg.attach(MIMEText(body, "html", "utf-8"))
    # Adjuntar imagen como Content-ID
    try:
        with open(banner_path, 'rb') as img:
            mime_img = MIMEImage(img.read())
            mime_img.add_header('Content-ID', '<bannerpecuario>')
            msg.attach(mime_img)
    except Exception as e:
        print(f"No se pudo adjuntar el banner: {str(e)}")
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, [email], msg.as_string())
        print(f"Correo de recuperación enviado a {email}")
    except Exception as e:
        print(f"Error enviando correo: {str(e)}")
