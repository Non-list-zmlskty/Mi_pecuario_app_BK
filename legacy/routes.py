"""
[ARCHIVO OBSOLETO]
Este archivo centralizaba todas las rutas (endpoints) de la API, gestionando la lógica de acceso a la base de datos y la definición de endpoints.

Motivos de inutilización:
- La lógica de rutas fue migrada a blueprints separados en la carpeta `routes/` para mejorar la modularidad y escalabilidad.
- Cada entidad (auth, usuario, lote, animal) tiene ahora su propio archivo de rutas.

Comparativa con la versión actual (`routes/*.py`):
- Antes: Todas las rutas en un solo archivo, dificultando el mantenimiento.
- Ahora: Rutas separadas por entidad, fácil de localizar y modificar.
- Antes: Problemas de concurrencia y manejo de sesiones.
- Ahora: Buenas prácticas en el manejo de sesiones y modularidad.
- Antes: Dificultad para agregar nuevas funcionalidades.
- Ahora: Estructura preparada para crecimiento y colaboración.
"""

# routes.py
# Este archivo ha sido migrado a la nueva estructura modular.
# Toda la lógica de endpoints ahora se encuentra en:
# - routes/auth_routes.py
# - routes/user_routes.py
# - routes/lote_routes.py
# - routes/animal_routes.py
# Mantén este archivo solo como referencia temporal.

from flask import Blueprint

# -------------------
# Blueprint para modularidad de rutas
# -------------------
api = Blueprint('api', __name__)

# NOTA: Para evitar errores de pool de conexiones, cada endpoint que use la base de datos debe:
# 1. Abrir la sesión con db = SessionLocal()
# 2. Usar try/except/finally y cerrar SIEMPRE con db.close()
# 3. Hacer db.rollback() en except si hay error
# 4. No compartir sesiones entre peticiones/hilos
# 5. No abrir sesiones dentro de bucles sin cerrarlas
# 6. No dejar sesiones abiertas en tareas en segundo plano
# Si no se sigue esto, puedes tener errores como:
# - QueuePool limit of size 5 overflow 10 reached, connection timed out
# - Conexiones colgadas o lentitud
# - Errores de concurrencia
# - Estado inconsistente en la base de datos
#
# Ejemplo correcto:
# db = SessionLocal()
# try:
#     ...operaciones...
# except Exception as e:
#     db.rollback()
#     ...manejo de error...
# finally:
#     db.close()