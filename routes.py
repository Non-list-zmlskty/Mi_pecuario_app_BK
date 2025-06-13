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

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuración de JWT
JWT_SECRET_KEY = "tu_clave_secreta_muy_segura"  # En producción, usa una variable de entorno
JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)

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