from sqlalchemy import Column, String, Integer, DateTime, Float, Boolean, ForeignKey, Date, DECIMAL, Text, Enum
from db.session import Base

class Usuario(Base):
    __tablename__ = 'Usuario'
    __table_args__ = {'extend_existing': True}
    usuario_id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(100))
    email = Column(String(100), unique=True)
    hashed_password = Column(String(128), nullable=False)
    reset_code = Column(String(6), nullable=True)
    reset_code_expiry = Column(DateTime, nullable=True)

class Grupo(Base):
    __tablename__ = 'Grupo'
    __table_args__ = {'extend_existing': True}
    grupo_id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(100), nullable=False)
    descripcion = Column(Text)
    proposito = Column(Enum('Lechera', 'Cría', 'Ceba', 'Levante'), nullable=False)

class Lote(Base):
    __tablename__ = 'Lote'
    __table_args__ = {'extend_existing': True}
    lote_id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(100))
    usuario_id = Column(Integer, ForeignKey('Usuario.usuario_id'))
    grupo_id = Column(Integer, ForeignKey('Grupo.grupo_id'))
    cantidad = Column(Integer, nullable=True)  # <-- NUEVO CAMPO

class Animal(Base):
    __tablename__ = 'Animal'
    __table_args__ = {'extend_existing': True}
    animal_id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(100))
    lote_id = Column(Integer, ForeignKey('Lote.lote_id'))
    fecha_nacimiento = Column(Date)
    raza = Column(String(50))
    sexo = Column(Enum('Hembra', 'Macho'), nullable=False)

class Alimento(Base):
    __tablename__ = 'Alimento'
    __table_args__ = {'extend_existing': True}
    alimento_id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(100))
    descripcion = Column(Text)

class NutriAlimento(Base):
    __tablename__ = 'NutriAlimento'
    __table_args__ = {'extend_existing': True}
    nutri_alimento_id = Column(Integer, primary_key=True, autoincrement=True)
    grupo_id = Column(Integer, ForeignKey('Grupo.grupo_id'), nullable=False)
    alimento_id = Column(Integer, ForeignKey('Alimento.alimento_id'), nullable=False)
    cantidad_recomendada = Column(DECIMAL(10,2), nullable=False)
    frecuencia = Column(Enum('Diaria', 'Semanal', 'Mensual'), nullable=False)
    proposito = Column(Enum('Lechera', 'Cría', 'Ceba', 'Levante'), nullable=False)

class SeguimientoAlimento(Base):
    __tablename__ = 'SeguimientoAlimento'
    __table_args__ = {'extend_existing': True}
    seguimiento_alimento_id = Column(Integer, primary_key=True, autoincrement=True)
    lote_id = Column(Integer, ForeignKey('Lote.lote_id'), nullable=False)
    nutri_alimento_id = Column(Integer, ForeignKey('NutriAlimento.nutri_alimento_id'), nullable=False)
    fecha = Column(Date, nullable=False)
    cantidad_suministrada = Column(DECIMAL(10,2), nullable=False)

class PesoLote(Base):
    __tablename__ = 'PesoLote'
    __table_args__ = {'extend_existing': True}
    peso_lote_id = Column(Integer, primary_key=True, autoincrement=True)
    lote_id = Column(Integer, ForeignKey('Lote.lote_id'))
    fecha = Column(Date)
    peso = Column(DECIMAL(7,2))

class Alertas(Base):
    __tablename__ = 'Alertas'
    __table_args__ = {'extend_existing': True}
    alerta_id = Column(Integer, primary_key=True, autoincrement=True)
    lote_id = Column(Integer, ForeignKey('Lote.lote_id'), nullable=False)
    fecha = Column(Date, nullable=False)
    tipo = Column(Enum('Ingesta insuficiente', 'Ingesta excesiva', 'Desviación peso', 'Falta suministro', 'Otro'), nullable=False)
    mensaje = Column(String(255), nullable=False)
