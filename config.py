import os

JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "clave_por_defecto")
