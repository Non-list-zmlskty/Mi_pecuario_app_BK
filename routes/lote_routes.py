from flask import Blueprint, request, jsonify
from db.session import SessionLocal
from models.models import Lote, Animal, PesoLote
from utils.jwt_utils import token_required

lote_bp = Blueprint('lote', __name__, url_prefix='/api/lote')

@lote_bp.route('/registrar', methods=['POST'])
@token_required
def registrar_lote(current_user):
    data = request.get_json()
    if not data or 'nombre' not in data or 'grupo_id' not in data:
        return jsonify({"error": "Faltan campos requeridos"}), 400
    db = SessionLocal()
    try:
        nuevo_lote = Lote(
            nombre=data['nombre'],
            usuario_id=current_user.usuario_id,
            grupo_id=data['grupo_id']
        )
        db.add(nuevo_lote)
        db.commit()
        db.refresh(nuevo_lote)
        return jsonify({
            "message": "Lote registrado exitosamente",
            "lote": {
                "id": nuevo_lote.lote_id,
                "nombre": nuevo_lote.nombre,
                "grupo_id": nuevo_lote.grupo_id
            }
        }), 201
    except Exception as e:
        db.rollback()
        return jsonify({"error": "Error al registrar el lote"}), 500
    finally:
        db.close()

@lote_bp.route('/mis-lotes', methods=['GET'])
@token_required
def obtener_lotes_usuario(current_user):
    db = SessionLocal()
    try:
        lotes = db.query(Lote).filter_by(usuario_id=current_user.usuario_id).all()
        lotes_data = [
            {
                "id": lote.lote_id,
                "nombre": lote.nombre,
                "grupo_id": lote.grupo_id
            }
            for lote in lotes
        ]
        return jsonify({"lotes": lotes_data}), 200
    except Exception as e:
        return jsonify({"error": "Error al obtener los lotes"}), 500
    finally:
        db.close()

@lote_bp.route('/<int:lote_id>', methods=['DELETE'])
@token_required
def eliminar_lote(current_user, lote_id):
    db = SessionLocal()
    try:
        # Verifica que el lote pertenezca al usuario
        lote = db.query(Lote).filter_by(lote_id=lote_id, usuario_id=current_user.usuario_id).first()
        if not lote:
            return jsonify({'error': 'Lote no encontrado'}), 404
        # Elimina animales relacionados
        db.query(Animal).filter_by(lote_id=lote_id).delete()
        # Elimina pesos relacionados
        db.query(PesoLote).filter_by(lote_id=lote_id).delete()
        # Elimina el lote
        db.delete(lote)
        db.commit()
        return jsonify({'message': 'Lote eliminado correctamente'}), 200
    except Exception as e:
        db.rollback()
        return jsonify({'error': f'Error al eliminar el lote: {str(e)}'}), 500
    finally:
        db.close()
