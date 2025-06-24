from flask import Blueprint, request, jsonify
from db.session import SessionLocal
from models.models import Lote, Animal, Grupo, PesoLote  # <-- Asegúrate de incluir PesoLote
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
    peso = data.get('peso')  # <-- Nuevo: obtener peso del frontend
    nombre_animal = data.get('nombre_animal') or f"Animal {random.randint(1000,9999)}"  # <-- Nuevo: nombre por defecto
    db = SessionLocal()
    try:
        # Buscar grupo por propósito
        grupo = db.query(Grupo).filter_by(proposito=data['proposito']).first()
        if not grupo:
            return jsonify({"error": f"No existe un grupo para el propósito '{data['proposito']}'"}), 400

        # Crear un nuevo lote (grupo de animales)
        nuevo_lote = Lote()
        nuevo_lote.nombre = f"Lote {data['proposito']} {random.randint(1000,9999)}"
        nuevo_lote.usuario_id = current_user.usuario_id
        nuevo_lote.grupo_id = grupo.grupo_id  # Asignar grupo_id según propósito
        nuevo_lote.cantidad = data['cantidad']
        db.add(nuevo_lote)
        db.flush()
        animal = Animal()
        animal.nombre = nombre_animal  # <-- Asigna nombre
        animal.sexo = data['genero']
        animal.raza = data['raza']
        animal.lote_id = nuevo_lote.lote_id
        db.add(animal)
        # Nuevo: guardar peso inicial si se envió
        if peso:
            peso_lote = PesoLote(
                lote_id=nuevo_lote.lote_id,
                peso=peso,
                fecha=datetime.utcnow().date()
            )
            db.add(peso_lote)
        db.commit()
        return jsonify({
            "message": f"Ficha registrada exitosamente. {data['cantidad']} animales guardados en el grupo.",
            "lote_id": nuevo_lote.lote_id,
            "animal_id": animal.animal_id,
            "cantidad": data['cantidad']
        }), 201
    except Exception as e:
        db.rollback()
        return jsonify({"error": "Error al registrar la ficha", "detalle": str(e)}), 500
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
            fecha_actualizacion = None
            if peso_row and peso_row[1] is not None:
                try:
                    fecha_actualizacion = peso_row[1].isoformat()
                except Exception:
                    fecha_actualizacion = str(peso_row[1])
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
        # Solo usar la clave si ambos valores no son None
        if genero is not None and proposito is not None:
            peso_individual = pesos_referencia.get((genero, proposito), 500)
        else:
            peso_individual = 500
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
            fecha_actualizacion = None
            if peso_row[1] is not None:
                try:
                    fecha_actualizacion = peso_row[1].isoformat()
                except Exception:
                    fecha_actualizacion = str(peso_row[1])
            peso_individual_estimado = round(peso_general / cantidad, 2) if cantidad > 0 else 0
        else:
            animales = db.query(Animal).filter(Animal.lote_id == lote_id).all()
            genero = animales[0].sexo if animales and hasattr(animales[0], 'sexo') else None
            proposito = None
            if hasattr(lote, 'grupo_id') and lote.grupo_id:
                grupo = db.query(Grupo).filter_by(grupo_id=lote.grupo_id).first()
                proposito = grupo.proposito if grupo else None
            # Solo usar la clave si ambos valores no son None
            if genero is not None and proposito is not None:
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
            else:
                peso_individual_estimado = 500
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

@animal_bp.route('/lote/<int:lote_id>/dieta', methods=['GET'])
@token_required
def obtener_dieta_personalizada(current_user, lote_id):
    """
    Devuelve la dieta recomendada para el lote, considerando género, propósito, cantidad, peso promedio y total.
    Usa la función almacenada y la tabla NutriAlimento para calcular cantidades y recomendaciones.
    """
    db = SessionLocal()
    try:
        # 1. Obtener lote y grupo
        lote = db.query(Lote).filter_by(lote_id=lote_id, usuario_id=current_user.usuario_id).first()
        if not lote:
            return jsonify({"error": "Lote no encontrado"}), 404
        cantidad = lote.cantidad if lote.cantidad else 1
        grupo = db.query(Grupo).filter_by(grupo_id=lote.grupo_id).first()
        proposito = grupo.proposito if grupo else None

        # 2. Obtener peso promedio individual del lote
        sql_peso = text("""
            SELECT peso FROM PesoLote 
            WHERE lote_id = :lote_id 
            ORDER BY fecha DESC LIMIT 1
        """)
        peso_row = db.execute(sql_peso, {"lote_id": lote_id}).fetchone()
        peso_promedio = float(peso_row[0]) if peso_row and peso_row[0] is not None else 500
        peso_promedio_unidad = "kg"
        # 3. Determinar rango de peso y mensaje
        if peso_promedio < 400:
            rango = "bajo"
            mensaje = "El peso promedio está por debajo del recomendado. Se recomienda una dieta para aumentar peso."
        elif peso_promedio > 700:
            rango = "alto"
            mensaje = "El peso promedio está por encima del rango recomendado. Se recomienda una dieta reguladora."
        else:
            rango = "medio"
            mensaje = "El peso promedio es adecuado. Se recomienda una dieta de mantenimiento."

        # 4. Calcular cantidad recomendada de materia seca usando la función almacenada
        sql_func = text("SELECT CalcularCantidadRecomendadaGramos(:peso, :proposito) AS gramos")
        gramos_por_bovino = db.execute(sql_func, {"peso": peso_promedio, "proposito": proposito}).scalar()
        gramos_total_lote = gramos_por_bovino * cantidad
        gramos_unidad = "g"
        # 5. Obtener alimentos recomendados para el grupo y propósito
        sql_alimentos = text("""
            SELECT A.nombre, N.cantidad_recomendada, N.frecuencia
            FROM NutriAlimento N
            JOIN Alimento A ON N.alimento_id = A.alimento_id
            WHERE N.grupo_id = :grupo_id AND N.proposito = :proposito
        """)
        alimentos = db.execute(sql_alimentos, {"grupo_id": lote.grupo_id, "proposito": proposito}).fetchall()

        dieta = []
        for alimento in alimentos:
            dieta.append({
                "alimento": alimento[0],
                "cantidad_recomendada_por_bovino": float(alimento[1]),
                "cantidad_recomendada_por_bovino_unidad": "g",
                "cantidad_recomendada_total": round(float(alimento[1]) * cantidad, 2),
                "cantidad_recomendada_total_unidad": "g",
                "frecuencia": alimento[2]
            })
        return jsonify({
            "lote_id": lote.lote_id,
            "nombre_lote": lote.nombre,
            "proposito": proposito,
            "cantidad_animales": cantidad,
            "peso_promedio_individual": peso_promedio,
            "peso_promedio_individual_unidad": peso_promedio_unidad,
            "peso_total_lote": peso_promedio * cantidad,
            "peso_total_lote_unidad": peso_promedio_unidad,
            "rango": rango,
            "mensaje": mensaje,
            "materia_seca_recomendada_por_bovino": gramos_por_bovino,
            "materia_seca_recomendada_por_bovino_unidad": gramos_unidad,
            "materia_seca_recomendada_total": gramos_total_lote,
            "materia_seca_recomendada_total_unidad": gramos_unidad,
            "dieta": dieta
        }), 200
    except Exception as e:
        return jsonify({"error": f"Error al obtener la dieta: {str(e)}"}), 500
    finally:
        db.close()

@animal_bp.route('/lote/<int:lote_id>/peso', methods=['POST'])
@token_required
def registrar_peso_lote(current_user, lote_id):
    data = request.get_json()
    peso = data.get('peso')
    fecha = data.get('fecha', datetime.utcnow().date())
    if not peso:
        return jsonify({"error": "Peso requerido"}), 400
    db = SessionLocal()
    try:
        lote = db.query(Lote).filter_by(lote_id=lote_id, usuario_id=current_user.usuario_id).first()
        if not lote:
            return jsonify({"error": "Lote no encontrado"}), 404
        sql = text("INSERT INTO PesoLote (lote_id, fecha, peso) VALUES (:lote_id, :fecha, :peso)")
        db.execute(sql, {"lote_id": lote_id, "fecha": fecha, "peso": peso})
        db.commit()
        return jsonify({"message": "Peso registrado exitosamente"}), 201
    except Exception as e:
        db.rollback()
        return jsonify({"error": f"Error al registrar el peso: {str(e)}"}), 500
    finally:
        db.close()
