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