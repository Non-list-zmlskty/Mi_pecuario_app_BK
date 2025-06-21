from sqlalchemy.orm import Session
from models.models import Usuario
from schemas.user import UsuarioCreate

def get_user(db: Session):
    return db.query(Usuario).all()

def get_user_by_id(db: Session, user_id: int): 
    return db.query(Usuario).filter(Usuario.usuario_id == user_id).first()

def get_user_by_username(db: Session, email: str):
    return db.query(Usuario).filter(Usuario.email == email).first()

def create_user(db: Session, user: UsuarioCreate):
    db_user = Usuario(
        nombre=user.nombre,
        email=user.email,
        hashed_password=user.password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user