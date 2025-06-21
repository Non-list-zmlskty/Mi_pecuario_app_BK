# routes.py

from flask import Blueprint, request, jsonify
from Base_De_Datos_cam import SessionLocal
from forms_DB_CAM import Usuario, Lote, Grupo, Animal  # Asegúrate de importar Lote
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
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
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

# Blocklist en memoria para tokens JWT revocados
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
            # Usar el token completo como identificador en la blocklist
            if token in jwt_blocklist:
                return jsonify({"error": "Token revocado"}), 401
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
    import mimetypes
    subject = str(Header(f"Código de verificación MiPecuarioApp: {code}", "utf-8"))
    cid = "bannerimage"
    body = f"""
    <html>
      <body>
        <img src='cid:{cid}' alt='Mi Pecuario App' style='width:100%;max-width:600px;'><br><br>
        <h2>Código de verificación MiPecuarioApp: {code}</h2>
        <p>Estimado/a: {email}</p>
        <p>Esperamos se encuentre bien. Hemos recibido una solicitud para el cambio de tu contraseña.</p>
        <p><b>Código de verificación:</b></p>
        <h1 style='color:#2e7d32;'>{code}</h1>
        <p>Ingresa el código en la aplicación para demostrar que eres tú.</p>
        <p>Si no solicitaste este código, ignora este correo.</p>
        <br>
        <p>Atentamente,<br>El equipo de programación M.P.A.</p>
      </body>
    </html>
    """
    msg = MIMEMultipart()
    msg['Subject'] = subject
    msg['From'] = SMTP_USER
    msg['To'] = email
    msg.attach(MIMEText(body, "html", "utf-8"))
    # Ruta de la imagen con extensión
    image_path = r"C:\\Users\\Nslksss\\Pictures\\IMG_MPA_EMAIL\\Banner 1 Pecuario App.png"
    try:
        ctype, encoding = mimetypes.guess_type(image_path)
        if ctype is None or not ctype.startswith('image/'):
            raise ValueError('No se pudo determinar el tipo de imagen o no es una imagen válida')
        maintype, subtype = ctype.split('/', 1)
        with open(image_path, 'rb') as img_file:
            img = MIMEImage(img_file.read(), _subtype=subtype)
            img.add_header('Content-ID', '<bannerimage>')
            img.add_header('Content-Disposition', 'inline', filename=os.path.basename(image_path))
            msg.attach(img)
    except Exception as e:
        logger.error(f"No se pudo adjuntar la imagen: {str(e)}")
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

# 1. Registro de usuario
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

# 2. Login de usuario
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
                
                # --- Nueva lógica: verificar si tiene fichas (animales) ---
                lotes_usuario = db.query(Lote.lote_id).filter_by(usuario_id=usuario.usuario_id).all()
                lote_ids = [l.lote_id for l in lotes_usuario]
                fichas = []
                tiene_fichas = False
                if lote_ids:
                    animales = db.query(Animal).filter(Animal.lote_id.in_(lote_ids)).all()
                    fichas = [
                        {
                            "id": animal.animal_id,
                            "sexo": animal.sexo,
                            "raza": animal.raza,
                            "lote_id": animal.lote_id
                        }
                        for animal in animales
                    ]
                    tiene_fichas = len(fichas) > 0

                logger.info(f"Login exitoso para usuario: {usuario.nombre}")
                return jsonify({
                    "token": access_token,
                    "refreshToken": refresh_token,
                    "user": {
                        "id": str(usuario.usuario_id),
                        "name": usuario.nombre,
                        "email": usuario.email
                    },
                    "tiene_fichas": tiene_fichas,
                    "fichas": fichas  # El frontend puede usar esto para decidir qué mostrar
                }), 200
        except Exception as e:
            if str(usuario.hashed_password) == password:
                db.query(Usuario).filter_by(usuario_id=usuario.usuario_id).update(
                    {"hashed_password": hash_password(password)}
                )
                db.commit()
                
                access_token, refresh_token = generate_tokens(usuario.usuario_id)
                
                # --- Nueva lógica: verificar si tiene fichas (animales) ---
                lotes_usuario = db.query(Lote.lote_id).filter_by(usuario_id=usuario.usuario_id).all()
                lote_ids = [l.lote_id for l in lotes_usuario]
                fichas = []
                tiene_fichas = False
                if lote_ids:
                    animales = db.query(Animal).filter(Animal.lote_id.in_(lote_ids)).all()
                    fichas = [
                        {
                            "id": animal.animal_id,
                            "sexo": animal.sexo,
                            "raza": animal.raza,
                            "lote_id": animal.lote_id
                        }
                        for animal in animales
                    ]
                    tiene_fichas = len(fichas) > 0

                logger.info(f"Login exitoso y contraseña actualizada para usuario: {usuario.nombre}")
                return jsonify({
                    "token": access_token,
                    "refreshToken": refresh_token,
                    "user": {
                        "id": str(usuario.usuario_id),
                        "name": usuario.nombre,
                        "email": usuario.email
                    },
                    "tiene_fichas": tiene_fichas,
                    "fichas": fichas
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

# 1. Registrar un lote (si el usuario no tiene lotes)
@api.route('/lote/registrar', methods=['POST'])
@token_required
def registrar_lote(current_user):
    """
    Registra un nuevo lote de ganado para el usuario autenticado.
    Espera: { "nombre": str, "grupo_id": int }
    """
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
        logger.error(f"Error al registrar lote: {str(e)}")
        return jsonify({"error": "Error al registrar el lote"}), 500
    finally:
        db.close()

# 2. Consultar lotes del usuario (para obtener el lote_id)
@api.route('/lote/mis-lotes', methods=['GET'])
@token_required
def obtener_lotes_usuario(current_user):
    """
    Devuelve todos los lotes registrados por el usuario autenticado.
    """
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
        logger.error(f"Error al obtener lotes: {str(e)}")
        return jsonify({"error": "Error al obtener los lotes"}), 500
    finally:
        db.close()

# 3. Registrar ficha/grupo de animales (formulario de ingreso de ganado)
@api.route('/ingreso/registrar', methods=['POST'])
@token_required
def registrar_ficha_grupo_animales(current_user):
    """
    Registra una ficha de grupo de animales.
    Espera: { "genero": str, "proposito": str, "raza": str, "cantidad": int }
    """
    data = request.get_json()
    required_fields = ['genero', 'proposito', 'raza', 'cantidad']
    if not data or not all(field in data for field in required_fields):
        return jsonify({"error": "Faltan campos requeridos"}), 400

    db = SessionLocal()
    try:
        # Crear un nuevo lote automáticamente
        nuevo_lote = Lote(
            nombre=f"Lote {data['proposito']} {random.randint(1000,9999)}",
            usuario_id=current_user.usuario_id,
            grupo_id=None  # Si tienes lógica para grupo, puedes asignar aquí
        )
        db.add(nuevo_lote)
        db.flush()  # Para obtener el lote_id

        animales_creados = []
        for i in range(data['cantidad']):
            animal = Animal(
                sexo=data['genero'],
                raza=data['raza'],
                lote_id=nuevo_lote.lote_id
                # Si agregas 'proposito' al modelo Animal, agrega aquí: proposito=data['proposito']
            )
            db.add(animal)
            animales_creados.append({
                "id": None,  # Se asigna después del commit
                "genero": data['genero'],
                "raza": data['raza'],
                "lote_id": nuevo_lote.lote_id
                # "proposito": data['proposito']  # Si agregas el campo al modelo
            })
        db.commit()
        # Asignar los ids después del commit
        for idx, animal in enumerate(db.query(Animal).filter(Animal.lote_id == nuevo_lote.lote_id).order_by(Animal.animal_id).all()):
            animales_creados[idx]["id"] = animal.animal_id

        return jsonify({
            "message": f"Ficha registrada exitosamente. {data['cantidad']} animales guardados.",
            "lote_id": nuevo_lote.lote_id,
            "animales": animales_creados
        }), 201
    except Exception as e:
        db.rollback()
        logger.error(f"Error al registrar ficha: {str(e)}")
        return jsonify({"error": "Error al registrar la ficha"}), 500
    finally:
        db.close()

# 4. Consultar fichas (animales) del usuario agrupadas por lote/ficha
@api.route('/ingreso/mis-fichas', methods=['GET'])
@token_required
def obtener_fichas_usuario(current_user):
    """
    Devuelve las fichas (grupos de animales) registradas por el usuario, agrupadas por lote.
    """
    db = SessionLocal()
    try:
        # Obtener los lotes del usuario
        lotes_usuario = db.query(Lote).filter_by(usuario_id=current_user.usuario_id).all()
        fichas = []
        for lote in lotes_usuario:
            animales = db.query(Animal).filter(Animal.lote_id == lote.lote_id).all()
            if not animales:
                continue
            # Se asume que todos los animales del lote tienen el mismo genero y raza (por diseño del formulario)
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
        logger.error(f"Error al obtener fichas: {str(e)}")
        return jsonify({"error": "Error al obtener las fichas"}), 500
    finally:
        db.close()

# --- Edición de ficha ---
# Es posible agregar un endpoint tipo PUT/PATCH para editar una ficha (animal) existente.
# Ejemplo futuro:
# @api.route('/ingreso/editar/<int:animal_id>', methods=['PUT'])
# @token_required
# def editar_animal(current_user, animal_id):
#     ...
# ------------------------------------------------------------
#-------------------------------------------------------------uncommited ------------------------------------------------------------
@api.route('/calculo/pesos', methods=['POST'])
def calcular_pesos():
    """
    Calcula el peso promedio individual y el peso total del lote según género y propósito.
    Espera: { "genero": str, "proposito": str, "cantidad": int }
    """
    data = request.get_json()
    required_fields = ['genero', 'proposito', 'cantidad']
    if not data or not all(field in data for field in required_fields):
        return jsonify({"error": "Faltan campos requeridos"}), 400

    genero = data['genero']
    proposito = data['proposito']
    cantidad = data['cantidad']

    # Pesos promedio de referencia (puedes ajustar estos valores según tu lógica)
    pesos_referencia = {
        # (genero, proposito): peso_promedio_kg
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
        "peso_promedio_individual": peso_individual,
        "peso_total_lote": peso_total,
        "genero": genero,
        "proposito": proposito,
        "cantidad": cantidad
    }), 200

@api.route('/auth/logout', methods=['POST'])
@token_required
def logout(current_user):
    auth_header = request.headers.get('Authorization', None)
    if not auth_header:
        return jsonify({"error": "Token no proporcionado"}), 401
    try:
        token = auth_header.split(" ")[1]
        jwt_blocklist.add(token)
        return jsonify({"message": "Successfully logged out"}), 200
    except Exception as e:
        return jsonify({"error": "Token inválido"}), 401