"""
[ARCHIVO OBSOLETO]
Este archivo gestionaba la configuración y conexión a la base de datos utilizando SQLAlchemy, cargando variables de entorno y creando la sesión de base de datos.

Motivos de inutilización:
- La configuración de la base de datos fue migrada a un módulo más estructurado y reutilizable, alineado con la nueva organización del proyecto.
- Se mejoró la gestión de variables de entorno y la inicialización de la base de datos.

Comparativa con la versión actual:
- Antes: Configuración básica y centralizada aquí, sin separación clara de responsabilidades.
- Ahora: Configuración desacoplada, mejor manejo de variables de entorno y reutilización en toda la app.
- Antes: Menos control sobre el ciclo de vida de las sesiones.
- Ahora: Uso de dependencias y manejo adecuado de sesiones por endpoint.
- Antes: No seguía la estructura modular recomendada para proyectos Flask/FastAPI.
- Ahora: Integración limpia y modular con el resto de la aplicación.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()  # Carga las variables de entorno desde un archivo .env
print("DB_USER:", os.getenv("DB_USER"))  # Depuración: Verifica si se lee correctamente

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME")
DB_PORT = os.getenv("DB_PORT", 3306)

URL_CONNECTION = f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
engine = create_engine(URL_CONNECTION, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=True, bind=engine)
Base = declarative_base()
