import jwt
from flask import request, jsonify
from functools import wraps
from datetime import datetime, timedelta
from db.session import SessionLocal
from models.models import Usuario
import os

# Usa la clave secreta y expiraciones desde el entorno
JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "clave_por_defecto")
JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=12)  # 12 horas de duración
JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)  # 30 días de duración

jwt_blocklist = set()

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
            if token in jwt_blocklist:
                return jsonify({"error": "Token revocado"}), 401
            user_id = payload.get('user_id')
            if not user_id:
                return jsonify({"error": "Token sin user_id"}), 401
            db = SessionLocal()
            try:
                usuario = db.query(Usuario).filter_by(usuario_id=user_id).first()
                if not usuario:
                    return jsonify({"error": "Usuario no encontrado"}), 401
                return f(usuario, *args, **kwargs)
            finally:
                db.close()
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expirado"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Token inválido"}), 401
        except Exception as e:
            return jsonify({"error": str(e)}), 401
    return decorated

def generate_tokens(user_id):
    access_token = jwt.encode(
        {
            'user_id': user_id,
            'exp': datetime.utcnow() + JWT_ACCESS_TOKEN_EXPIRES
        },
        JWT_SECRET_KEY,
        algorithm='HS256'
    )
    refresh_token = jwt.encode(
        {
            'user_id': user_id,
            'exp': datetime.utcnow() + JWT_REFRESH_TOKEN_EXPIRES
        },
        JWT_SECRET_KEY,
        algorithm='HS256'
    )
    return access_token, refresh_token
