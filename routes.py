# routes.py

from flask import Blueprint, request, jsonify
from Base_De_Datos_cam import SessionLocal
from forms_DB_CAM import Usuario
from esquemas import hash_password, pwd_context, UsuarioCreate, UsuarioResponse
from sqlalchemy.exc import SQLAlchemyError
import logging
import jwt
from datetime import datetime, timedelta
import os
from functools import wraps
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
import smtplib
from email.mime.text import MIMEText
from email.header import Header
import random

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuración de JWT
JWT_SECRET_KEY = "tu_clave_secreta_muy_segura"  # En producción, usa una variable de entorno
JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)

# Configuración para tokens de reseteo de contraseña
token_serializer = URLSafeTimedSerializer(JWT_SECRET_KEY)

# Configuración SMTP (ajusta estos valores a tu proveedor)
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
SMTP_USER = os.getenv('SMTP_USER', 'tu_email@gmail.com')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', 'tu_contraseña')

RESET_PASSWORD_URL = os.getenv('RESET_PASSWORD_URL', 'http://localhost:3000/reset-password')  # URL del frontend

api = Blueprint('api', __name__)

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(" ")[1]
            except IndexError:
                return jsonify({"error": "Token inválido"}), 401

        if not token:
            return jsonify({"error": "Token no proporcionado"}), 401

        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=['HS256'])
            current_user = SessionLocal().query(Usuario).filter_by(usuario_id=payload['user_id']).first()
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expirado"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Token inválido"}), 401
        except Exception as e:
            return jsonify({"error": str(e)}), 401

        return f(current_user, *args, **kwargs)
    return decorated

def generate_tokens(user_id):
    # Generar access token
    access_token = jwt.encode(
        {
            'user_id': user_id,
            'exp': datetime.utcnow() + JWT_ACCESS_TOKEN_EXPIRES
        },
        JWT_SECRET_KEY,
        algorithm='HS256'
    )
    
    # Generar refresh token
    refresh_token = jwt.encode(
        {
            'user_id': user_id,
            'exp': datetime.utcnow() + JWT_REFRESH_TOKEN_EXPIRES
        },
        JWT_SECRET_KEY,
        algorithm='HS256'
    )
    
    return access_token, refresh_token

# Función para enviar email
def send_reset_email(email, token):
    reset_link = f"{RESET_PASSWORD_URL}?token={token}"
    subject = str(Header("Restablece tu contraseña", "utf-8"))
    body = f"Hola,\n\nPara restablecer tu contraseña, haz clic en el siguiente enlace:\n{reset_link}\n\nSi no solicitaste este cambio, ignora este correo."
    msg = MIMEText(body, "plain", "utf-8")
    msg['Subject'] = subject
    msg['From'] = SMTP_USER
    msg['To'] = email
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, [email], msg.as_string())
        print(f"Correo de reseteo enviado a {email}")
    except Exception as e:
        print(f"Error enviando correo: {str(e)}")

def send_reset_code_email(email, code):
    subject = str(Header("Código de recuperación de contraseña", "utf-8"))
    body = f"Hola,\n\nTu código de recuperación es: {code}\n\nEste código es válido por 10 minutos. Si no solicitaste este código, ignora este correo."
    msg = MIMEText(body, "plain", "utf-8")
    msg['Subject'] = subject
    msg['From'] = SMTP_USER
    msg['To'] = email
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, [email], msg.as_string())
        logger.info(f"Código de recuperación enviado a {email}")
    except Exception as e:
        logger.error(f"Error enviando código: {str(e)}")

@api.route('/test', methods=['GET'])
def test_api():
    return jsonify({
        "status": "success",
        "message": "API is working correctly",
        "timestamp": datetime.utcnow().isoformat()
    }), 200

@api.route('/usuarionuevo', methods=['POST'])
def crear_usuario():
    data = request.get_json()
    try:
        user_data = UsuarioCreate(**data)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    db = SessionLocal()
    try:
        # Verificar si el usuario ya existe
        if db.query(Usuario).filter_by(email=user_data.email).first():
            return jsonify({"error": "El correo ya está registrado"}), 400
        
        nuevo_usuario = Usuario(
            nombre=user_data.nombre,
            email=user_data.email,
            hashed_password=hash_password(user_data.password)
        )
        db.add(nuevo_usuario)
        db.commit()
        db.refresh(nuevo_usuario)
        
        # Generar tokens para el nuevo usuario
        access_token, refresh_token = generate_tokens(nuevo_usuario.usuario_id)
        
        logger.info(f"Usuario {nuevo_usuario.nombre} creado exitosamente")
        return jsonify({
            "token": access_token,
            "refreshToken": refresh_token,
            "usuario": {
                "id": str(nuevo_usuario.usuario_id),
                "nombre": nuevo_usuario.nombre,
                "email": nuevo_usuario.email
            }
        }), 201
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error al crear usuario: {str(e)}")
        return jsonify({"error": "Error al crear el usuario"}), 500
    finally:
        db.close()

@api.route('/auth/login', methods=['POST'])
def auth_login():
    data = request.get_json()
    if not all(k in data for k in ['email', 'password']):
        return jsonify({"error": "Faltan campos requeridos"}), 400

    email = data['email']
    password = data['password']
    
    db = SessionLocal()
    try:
        usuario = db.query(Usuario).filter_by(email=email).first()
        if not usuario:
            return jsonify({"error": "Credenciales incorrectas"}), 401

        try:
            if pwd_context.verify(password, str(usuario.hashed_password)):
                access_token, refresh_token = generate_tokens(usuario.usuario_id)
                
                logger.info(f"Login exitoso para usuario: {usuario.nombre}")
                return jsonify({
                    "token": access_token,
                    "refreshToken": refresh_token,
                    "user": {
                        "id": str(usuario.usuario_id),
                        "name": usuario.nombre,
                        "email": usuario.email
                    }
                }), 200
        except Exception as e:
            if str(usuario.hashed_password) == password:
                db.query(Usuario).filter_by(usuario_id=usuario.usuario_id).update(
                    {"hashed_password": hash_password(password)}
                )
                db.commit()
                
                access_token, refresh_token = generate_tokens(usuario.usuario_id)
                
                logger.info(f"Login exitoso y contraseña actualizada para usuario: {usuario.nombre}")
                return jsonify({
                    "token": access_token,
                    "refreshToken": refresh_token,
                    "user": {
                        "id": str(usuario.usuario_id),
                        "name": usuario.nombre,
                        "email": usuario.email
                    }
                }), 200

        logger.warning(f"Intento de login fallido para correo: {email}")
        return jsonify({"error": "Credenciales incorrectas"}), 401
    except SQLAlchemyError as e:
        logger.error(f"Error en login: {str(e)}")
        return jsonify({"error": "Error al procesar el login"}), 500
    finally:
        db.close()

@api.route('/auth/refresh', methods=['POST'])
def refresh_token():
    data = request.get_json()
    if not data or 'refreshToken' not in data:
        return jsonify({"error": "Refresh token no proporcionado"}), 400

    try:
        # Decodificar el refresh token
        payload = jwt.decode(data['refreshToken'], JWT_SECRET_KEY, algorithms=['HS256'])
        user_id = payload['user_id']
        
        # Generar nuevos tokens
        access_token, refresh_token = generate_tokens(user_id)
        
        return jsonify({
            "token": access_token,
            "refreshToken": refresh_token
        }), 200
    except jwt.ExpiredSignatureError:
        return jsonify({"error": "Refresh token expirado"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"error": "Refresh token inválido"}), 401

# Ejemplo de ruta protegida
@api.route('/ruta-protegida', methods=['GET'])
@token_required
def ruta_protegida(current_user):
    return jsonify({
        "message": "Ruta protegida accesible",
        "usuario": {
            "id": str(current_user.usuario_id),
            "nombre": current_user.nombre,
            "email": current_user.email
        }
    }), 200

@api.route('/user/profile', methods=['GET'])
@token_required
def user_profile(current_user):
    try:
        # Adaptar la respuesta al formato que espera el frontend
        return jsonify({
            "id": str(current_user.usuario_id),
            "nombre": current_user.nombre,
            "email": current_user.email
        }), 200
    except Exception as e:
        logger.error(f"Error al obtener perfil: {str(e)}")
        return jsonify({"error": "Error al obtener el perfil"}), 500

@api.route('/auth/request-reset-code', methods=['POST'])
def request_reset_code():
    data = request.get_json()
    if not data or 'email' not in data:
        return jsonify({"error": "Email requerido"}), 400
    email = data['email']
    db = SessionLocal()
    try:
        usuario = db.query(Usuario).filter_by(email=email).first()
        if not usuario:
            return jsonify({"error": "Usuario no encontrado"}), 404
        # Generar código de 6 dígitos
        code = f"{random.randint(0, 999999):06d}"
        expiry = datetime.utcnow() + timedelta(minutes=10)
        usuario.reset_code = code
        usuario.reset_code_expiry = expiry
        db.commit()
        send_reset_code_email(email, code)
        return jsonify({"message": "Código de recuperación enviado"}), 200
    except Exception as e:
        db.rollback()
        logger.error(f"Error en request-reset-code: {str(e)}")
        return jsonify({"error": "Error enviando código"}), 500
    finally:
        db.close()

@api.route('/auth/verify-reset-code', methods=['POST'])
def verify_reset_code():
    data = request.get_json()
    if not data or 'email' not in data or 'code' not in data:
        return jsonify({"error": "Email y código requeridos"}), 400
    email = data['email']
    code = data['code']
    db = SessionLocal()
    try:
        usuario = db.query(Usuario).filter_by(email=email).first()
        if not usuario or not usuario.reset_code or not usuario.reset_code_expiry:
            return jsonify({"error": "Código no solicitado"}), 400
        if usuario.reset_code != code:
            return jsonify({"error": "Código incorrecto"}), 400
        if datetime.utcnow() > usuario.reset_code_expiry:
            return jsonify({"error": "Código expirado"}), 400
        return jsonify({"message": "Código válido"}), 200
    except Exception as e:
        logger.error(f"Error en verify-reset-code: {str(e)}")
        return jsonify({"error": "Error verificando código"}), 500
    finally:
        db.close()

@api.route('/auth/reset-password-with-code', methods=['POST'])
def reset_password_with_code():
    data = request.get_json()
    if not data or 'email' not in data or 'code' not in data or 'new_password' not in data:
        return jsonify({"error": "Email, código y nueva contraseña requeridos"}), 400
    email = data['email']
    code = data['code']
    new_password = data['new_password']
    db = SessionLocal()
    try:
        usuario = db.query(Usuario).filter_by(email=email).first()
        if not usuario or not usuario.reset_code or not usuario.reset_code_expiry:
            return jsonify({"error": "Código no solicitado"}), 400
        if usuario.reset_code != code:
            return jsonify({"error": "Código incorrecto"}), 400
        if datetime.utcnow() > usuario.reset_code_expiry:
            return jsonify({"error": "Código expirado"}), 400
        usuario.hashed_password = hash_password(new_password)
        usuario.reset_code = None
        usuario.reset_code_expiry = None
        db.commit()
        logger.info(f"Contraseña restablecida por código para usuario: {usuario.nombre}")
        return jsonify({"message": "Contraseña restablecida exitosamente"}), 200
    except Exception as e:
        db.rollback()
        logger.error(f"Error en reset-password-with-code: {str(e)}")
        return jsonify({"error": "Error al restablecer la contraseña"}), 500
    finally:
        db.close()

# --- FLUJO ANTERIOR POR ENLACE (OBSOLETO, REEMPLAZADO POR CÓDIGO DE 6 DÍGITOS) ---
# @api.route('/auth/request-reset-password', methods=['POST'])
# def request_reset_password():
#     ...
# @api.route('/auth/confirm-reset-password', methods=['POST'])
# def confirm_reset_password():
#     ...
# -------------------------------------------------------------------------------