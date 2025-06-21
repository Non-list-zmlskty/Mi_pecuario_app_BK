from flask import Blueprint, request, jsonify
from db.session import SessionLocal
from models.models import Lote, Animal, Grupo
from utils.jwt_utils import token_required
import random

animal_bp = Blueprint('animal', __name__, url_prefix='/api/animal')

@animal_bp.route('/registrar', methods=['POST'])
@token_required
def registrar_ficha_grupo_animales(current_user):
    data = request.get_json()
    required_fields = ['genero', 'proposito', 'raza', 'cantidad']
    if not data or not all(field in data for field in required_fields):
        return jsonify({"error": "Faltan campos requeridos"}), 400
    db = SessionLocal()
    try:
        nuevo_lote = Lote(
            nombre=f"Lote {data['proposito']} {random.randint(1000,9999)}",
            usuario_id=current_user.usuario_id,
            grupo_id=None
        )
        db.add(nuevo_lote)
        db.flush()
        animales_creados = []
        for i in range(data['cantidad']):
            animal = Animal(
                sexo=data['genero'],
                raza=data['raza'],
                lote_id=nuevo_lote.lote_id
            )
            db.add(animal)
            animales_creados.append({
                "id": None,
                "genero": data['genero'],
                "raza": data['raza'],
                "lote_id": nuevo_lote.lote_id
            })
        db.commit()
        for idx, animal in enumerate(db.query(Animal).filter(Animal.lote_id == nuevo_lote.lote_id).order_by(Animal.animal_id).all()):
            animales_creados[idx]["id"] = animal.animal_id
        return jsonify({
            "message": f"Ficha registrada exitosamente. {data['cantidad']} animales guardados.",
            "lote_id": nuevo_lote.lote_id,
            "animales": animales_creados
        }), 201
    except Exception as e:
        db.rollback()
        return jsonify({"error": "Error al registrar la ficha"}), 500
    finally:
        db.close()

@animal_bp.route('/mis-fichas', methods=['GET'])
@token_required
def obtener_fichas_usuario(current_user):
    db = SessionLocal()
    try:
        lotes_usuario = db.query(Lote).filter_by(usuario_id=current_user.usuario_id).all()
        fichas = []
        for lote in lotes_usuario:
            animales = db.query(Animal).filter(Animal.lote_id == lote.lote_id).all()
            if not animales:
                continue
            genero = animales[0].sexo
            raza = animales[0].raza
            cantidad = len(animales)
            ficha = {
                "lote_id": lote.lote_id,
                "nombre_lote": lote.nombre,
                "genero": genero,
                "raza": raza,
                "cantidad": cantidad
            }
            fichas.append(ficha)
        return jsonify({"fichas": fichas}), 200
    except Exception as e:
        return jsonify({"error": "Error al obtener las fichas"}), 500
    finally:
        db.close()

@animal_bp.route('/ficha/<int:lote_id>', methods=['GET'])
@token_required
def obtener_ficha_detalle(current_user, lote_id):
    db = SessionLocal()
    try:
        lote = db.query(Lote).filter_by(lote_id=lote_id, usuario_id=current_user.usuario_id).first()
        if not lote:
            return jsonify({"error": "Lote no encontrado o no pertenece al usuario"}), 404
        animales = db.query(Animal).filter(Animal.lote_id == lote_id).all()
        if not animales:
            return jsonify({"error": "No hay animales en este lote"}), 404
        genero = animales[0].sexo
        raza = animales[0].raza
        cantidad = len(animales)
        proposito = None
        if hasattr(lote, 'grupo_id') and lote.grupo_id:
            grupo = db.query(Grupo).filter_by(grupo_id=lote.grupo_id).first()
            proposito = grupo.proposito if grupo else None
        pesos_referencia = {
            ('Hembra', 'Lechera'): 550,
            ('Hembra', 'Cría'): 450,
            ('Hembra', 'Ceba'): 500,
            ('Hembra', 'Levante'): 400,
            ('Macho', 'Lechera'): 600,
            ('Macho', 'Cría'): 480,
            ('Macho', 'Ceba'): 650,
            ('Macho', 'Levante'): 420,
        }
        peso_individual = pesos_referencia.get((genero, proposito), 500)
        peso_total = peso_individual * cantidad
        return jsonify({
            "lote_id": lote.lote_id,
            "nombre_lote": lote.nombre,
            "genero": genero,
            "proposito": proposito,
            "raza": raza,
            "cantidad": cantidad,
            "peso_promedio_individual": peso_individual,
            "peso_total_lote": peso_total
        }), 200
    except Exception as e:
        return jsonify({"error": f"Error al obtener la ficha: {str(e)}"}), 500
    finally:
        db.close()
