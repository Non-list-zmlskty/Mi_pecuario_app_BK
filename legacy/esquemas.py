"""
[ARCHIVO OBSOLETO]
Este archivo definía los esquemas Pydantic para validación de datos y utilidades relacionadas, principalmente para usuarios.

Motivos de inutilización:
- Los esquemas fueron migrados a la carpeta `schemas/` para mantener una estructura modular y escalable.
- Ahora cada entidad tiene su propio archivo de esquema, facilitando el mantenimiento y la extensión.

Comparativa con la versión actual (`schemas/`):
- Antes: Todos los esquemas en un solo archivo, dificultando la organización.
- Ahora: Esquemas separados por entidad, mejor mantenibilidad.
- Antes: Validaciones y utilidades mezcladas.
- Ahora: Validaciones específicas y reutilizables por entidad.
- Antes: Dificultad para escalar y mantener.
- Ahora: Modularidad y claridad en la estructura de datos.
"""

# NOTA: Este archivo (esquemas.py) se usaba originalmente para definir esquemas Pydantic y utilidades de validación de datos.
# Actualmente, los esquemas deben migrarse a la carpeta schemas/ para mantener la organización modular.
# Si ya no se usa, puede eliminarse o mantenerse solo como referencia temporal.

from pydantic import BaseModel, Field, validator
import re

class UsuarioCreate(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., min_length=1)
    password: str = Field(..., min_length=6)

    @validator('email')
    def validate_email(cls, v):
        if not re.match(r"[^@]+@[^@]+\.[^@]+", v):
            raise ValueError('Email inválido')
        return v

# Si tienes más esquemas, migra a schemas/ y elimina este archivo si ya no se usa.