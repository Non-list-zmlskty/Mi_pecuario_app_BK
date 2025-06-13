from pydantic import BaseModel, Field, EmailStr, validator
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from forms_DB_CAM import Usuario
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

class UsuarioResponse(BaseModel):
    usuario_id: int
    nombre: str
    email: str

    class Config:
        from_attributes = True

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def create_user(db: Session, user: UsuarioCreate):
    db_user = Usuario(
        nombre=user.nombre,
        email=user.email,
        hashed_password=hash_password(user.password)
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user