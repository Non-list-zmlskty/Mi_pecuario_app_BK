import jwt
from flask import request, jsonify
from functools import wraps
from datetime import datetime, timedelta

JWT_SECRET_KEY = "tu_clave_secreta_muy_segura"
JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)

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
            return f(payload, *args, **kwargs)
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
