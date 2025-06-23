from flask import Blueprint, request, jsonify
from db.session import SessionLocal
from models.models import Usuario
from utils.jwt_utils import token_required, generate_tokens, jwt_blocklist
from utils.email_utils import send_reset_email, send_reset_code_email
from sqlalchemy.exc import SQLAlchemyError
from passlib.context import CryptContext
from datetime import datetime, timedelta
import jwt
import random
from config import JWT_SECRET_KEY
import os

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

@auth_bp.route('/login', methods=['POST'])
def login():
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
        if pwd_context.verify(password, str(usuario.hashed_password)):
            access_token, refresh_token = generate_tokens(usuario.usuario_id)
            return jsonify({
                "token": access_token,
                "refreshToken": refresh_token,
                "user": {
                    "id": str(usuario.usuario_id),
                    "name": usuario.nombre,
                    "email": usuario.email
                }
            }), 200
        return jsonify({"error": "Credenciales incorrectas"}), 401
    except SQLAlchemyError:
        return jsonify({"error": "Error al procesar el login"}), 500
    finally:
        db.close()

@auth_bp.route('/logout', methods=['POST'])
@token_required
def logout(current_user):
    auth_header = request.headers.get('Authorization', None)
    if not auth_header:
        return jsonify({"error": "Token no proporcionado"}), 401
    try:
        token = auth_header.split(" ")[1]
        jwt_blocklist.add(token)
        return jsonify({"message": "Successfully logged out"}), 200
    except Exception:
        return jsonify({"error": "Token inválido"}), 401

@auth_bp.route('/refresh', methods=['POST'])
@auth_bp.route('/refresh-token', methods=['POST'])  # Compatibilidad con frontend
def refresh_token():
    data = request.get_json()
    if not data or 'refreshToken' not in data:
        return jsonify({"error": "Refresh token no proporcionado"}), 400
    try:
        jwt_secret = os.environ.get("JWT_SECRET_KEY")
        payload = jwt.decode(data['refreshToken'], jwt_secret, algorithms=['HS256'])
        user_id = payload['user_id']
        access_token, refresh_token = generate_tokens(user_id)
        return jsonify({
            "token": access_token,
            "refreshToken": refresh_token
        }), 200
    except jwt.ExpiredSignatureError:
        return jsonify({"error": "Refresh token expirado"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"error": "Refresh token inválido"}), 401

@auth_bp.route('/request-reset-code', methods=['POST'])
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
        code = f"{random.randint(0, 999999):06d}"
        expiry = datetime.utcnow() + timedelta(minutes=10)
        usuario.reset_code = code
        usuario.reset_code_expiry = expiry
        db.commit()
        send_reset_code_email(email, code)
        return jsonify({"message": "Código de recuperación enviado"}), 200
    except Exception:
        db.rollback()
        return jsonify({"error": "Error enviando código"}), 500
    finally:
        db.close()

@auth_bp.route('/verify-reset-code', methods=['POST'])
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
    except Exception:
        return jsonify({"error": "Error verificando código"}), 500
    finally:
        db.close()

@auth_bp.route('/reset-password-with-code', methods=['POST'])
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
        usuario.hashed_password = pwd_context.hash(new_password)
        usuario.reset_code = None
        usuario.reset_code_expiry = None
        db.commit()
        return jsonify({"message": "Contraseña restablecida exitosamente"}), 200
    except Exception:
        db.rollback()
        return jsonify({"error": "Error al restablecer la contraseña"}), 500
    finally:
        db.close()

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data or 'email' not in data or 'password' not in data or 'name' not in data:
        return jsonify({"error": "Nombre, email y contraseña requeridos"}), 400
    email = data['email']
    password = data['password']
    name = data['name']
    db = SessionLocal()
    try:
        if db.query(Usuario).filter_by(email=email).first():
            return jsonify({"error": "El usuario ya existe"}), 409
        hashed_password = pwd_context.hash(password)
        usuario = Usuario(nombre=name, email=email, hashed_password=hashed_password)
        db.add(usuario)
        db.commit()
        return jsonify({"message": "Usuario creado exitosamente"}), 201
    except Exception:
        db.rollback()
        return jsonify({"error": "Error al crear usuario"}), 500
    finally:
        db.close()

# Compatibilidad legacy para rutas de recuperación de contraseña (sin /auth en el prefix)
from flask import current_app

# Solo registrar si no existen ya (evita duplicados si se importa varias veces)
def register_legacy_routes(bp):
    bp.add_url_rule('/login/auth', view_func=login, methods=['POST'])
    bp.add_url_rule('/logout/auth', view_func=logout, methods=['POST'])
    bp.add_url_rule('/register/auth', view_func=register, methods=['POST'])
    bp.add_url_rule('/refresh/auth', view_func=refresh_token, methods=['POST'])
    bp.add_url_rule('/refresh-token/auth', view_func=refresh_token, methods=['POST'])
    bp.add_url_rule('/request-reset-code/auth', view_func=request_reset_code, methods=['POST'])
    bp.add_url_rule('/verify-reset-code/auth', view_func=verify_reset_code, methods=['POST'])
    bp.add_url_rule('/reset-password-with-code/auth', view_func=reset_password_with_code, methods=['POST'])

# Rutas legacy fuera del prefijo /api/auth (ej: /api/request-reset-code/auth)
def register_global_legacy_routes(app):
    app.add_url_rule('/api/login/auth', view_func=login, methods=['POST'])
    app.add_url_rule('/api/logout/auth', view_func=logout, methods=['POST'])
    app.add_url_rule('/api/register/auth', view_func=register, methods=['POST'])
    app.add_url_rule('/api/refresh/auth', view_func=refresh_token, methods=['POST'])
    app.add_url_rule('/api/refresh-token/auth', view_func=refresh_token, methods=['POST'])
    app.add_url_rule('/api/request-reset-code/auth', view_func=request_reset_code, methods=['POST'])
    app.add_url_rule('/api/verify-reset-code/auth', view_func=verify_reset_code, methods=['POST'])
    app.add_url_rule('/api/reset-password-with-code/auth', view_func=reset_password_with_code, methods=['POST'])

# Registrar rutas legacy en el blueprint
register_legacy_routes(auth_bp)

# Para registrar las rutas globales, llama a register_global_legacy_routes(app) desde app.py después de registrar los blueprints.
# Ejemplo en app.py:
# from routes.auth_routes import register_global_legacy_routes
# ...
# app.register_blueprint(auth_bp)
# register_global_legacy_routes(app)
