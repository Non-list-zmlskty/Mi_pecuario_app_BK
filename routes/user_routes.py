from flask import Blueprint, request, jsonify
from db.session import SessionLocal
from models.models import Usuario
from utils.jwt_utils import token_required

user_bp = Blueprint('user', __name__, url_prefix='/api/user')

@user_bp.route('/profile', methods=['GET'])
@token_required
def user_profile(current_user):
    try:
        return jsonify({
            "id": str(current_user.usuario_id),
            "nombre": current_user.nombre,
            "email": current_user.email
        }), 200
    except Exception as e:
        return jsonify({"error": "Error al obtener el perfil"}), 500
