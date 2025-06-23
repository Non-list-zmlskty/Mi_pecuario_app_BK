from flask import Blueprint, request, jsonify
from db.session import SessionLocal
from models.models import Lote, Animal, Grupo
from utils.jwt_utils import token_required
from sqlalchemy import text
import random
from datetime import datetime

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
        # Crear un nuevo lote (grupo de animales)
        nuevo_lote = Lote(
            nombre=f"Lote {data['proposito']} {random.randint(1000,9999)}",
            usuario_id=current_user.usuario_id,
            grupo_id=None,
            cantidad=data['cantidad']  # <-- GUARDAR CANTIDAD
        )
        db.add(nuevo_lote)
        db.flush()
        animal = Animal(
            sexo=data['genero'],
            raza=data['raza'],
            lote_id=nuevo_lote.lote_id
        )
        db.add(animal)
        db.commit()
        return jsonify({
            "message": f"Ficha registrada exitosamente. {data['cantidad']} animales guardados en el grupo.",
            "lote_id": nuevo_lote.lote_id,
            "animal_id": animal.animal_id,
            "cantidad": data['cantidad']
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
            # Obtener el peso más reciente del lote
            sql = text("""
                SELECT peso, fecha FROM PesoLote 
                WHERE lote_id = :lote_id 
                ORDER BY fecha DESC LIMIT 1
            """)
            peso_row = db.execute(sql, {"lote_id": lote.lote_id}).fetchone()
            peso_general = float(peso_row[0]) if peso_row and peso_row[0] is not None else 0
            fecha_actualizacion = peso_row[1].isoformat() if peso_row and peso_row[1] else None
            cantidad = lote.cantidad if lote.cantidad else 1
            peso_individual_estimado = round(peso_general / cantidad, 2) if cantidad > 0 else 0
            ficha = {
                "id": lote.lote_id,
                "nombre_lote": lote.nombre,
                "cantidad_animales": cantidad,
                "fecha_creacion": None,  # Si tienes campo en BD, cámbialo aquí
                "estado": "activo",     # Si tienes campo en BD, cámbialo aquí
                "descripcion": None,     # Si tienes campo en BD, cámbialo aquí
                "peso_general_lote": peso_general,
                "peso_individual_estimado": peso_individual_estimado,
                "fecha_actualizacion": fecha_actualizacion
            }
            fichas.append(ficha)
        return jsonify({"fichas": fichas}), 200
    except Exception as e:
        return jsonify({"error": f"Error al obtener las fichas: {str(e)}"}), 500
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
        cantidad = lote.cantidad if lote.cantidad else 1  # <-- USAR CANTIDAD DEL LOTE
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
        peso_total = peso_individual * int(cantidad)
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

@animal_bp.route('/lote/<int:lote_id>/pesos', methods=['GET'])
@token_required
def obtener_pesos_lote(current_user, lote_id):
    db = SessionLocal()
    try:
        lote = db.query(Lote).filter_by(lote_id=lote_id, usuario_id=current_user.usuario_id).first()
        if not lote:
            return jsonify({"error": "Lote no encontrado o no pertenece al usuario"}), 404
        sql = text("""
            SELECT peso, fecha FROM PesoLote 
            WHERE lote_id = :lote_id 
            ORDER BY fecha DESC LIMIT 1
        """)
        peso_row = db.execute(sql, {"lote_id": lote_id}).fetchone()
        cantidad = lote.cantidad if lote.cantidad else 1

        if peso_row and peso_row[0] is not None:
            peso_general = float(peso_row[0])
            fecha_actualizacion = peso_row[1].isoformat() if peso_row[1] else None
            peso_individual_estimado = round(peso_general / cantidad, 2) if cantidad > 0 else 0
        else:
            # Si no hay peso registrado, usar referencia por género y propósito
            animales = db.query(Animal).filter(Animal.lote_id == lote_id).all()
            genero = animales[0].sexo if animales and hasattr(animales[0], 'sexo') else None
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
            peso_individual_estimado = pesos_referencia.get((genero, proposito), 500)
            peso_general = peso_individual_estimado * int(cantidad)
            fecha_actualizacion = None

        return jsonify({
            "peso_general_lote": peso_general,
            "peso_individual_estimado": peso_individual_estimado,
            "fecha_actualizacion": fecha_actualizacion
        }), 200
    except Exception as e:
        return jsonify({"error": f"Error al obtener los pesos: {str(e)}"}), 500
    finally:
        db.close()

@animal_bp.route('/mis-fichas', methods=['GET'])
@token_required
def mis_fichas(current_user):
    db = SessionLocal()
    try:
        lotes = db.query(Lote).filter_by(usuario_id=current_user.usuario_id).all()
        resultado = []
        for lote in lotes:
            animales = db.query(Animal).filter(Animal.lote_id == lote.lote_id).all()
            cantidad_animales = len(animales)
            peso_total = sum([a.peso for a in animales if hasattr(a, 'peso') and a.peso is not None])
            sexo = animales[0].sexo if animales and hasattr(animales[0], 'sexo') else "No especificado"
            especie = animales[0].especie if animales and hasattr(animales[0], 'especie') else "No especificada"
            resultado.append({
                "lote_id": lote.lote_id,
                "nombre_lote": lote.nombre,
                "cantidad_animales": cantidad_animales,
                "peso_total": peso_total,
                "sexo": sexo,
                "especie": especie,
                # Puedes agregar más campos aquí si el frontend los necesita
            })
        return jsonify({"fichas": resultado}), 200
    except Exception as e:
        return jsonify({"error": f"Error al obtener las fichas: {str(e)}"}), 500
    finally:
        db.close()
        db.close()
