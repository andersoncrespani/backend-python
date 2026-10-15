from sqlalchemy import (
    BigInteger, Boolean, Column, Date, DateTime, ForeignKey,
    SmallInteger, String, Text, func,
)
from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True)
    nome = Column(String(120), nullable=False)
    email = Column(String(180), nullable=False, unique=True)
    senha_hash = Column(String(72))
    sexo = Column(String(50), nullable=False)
    data_nascimento = Column(Date)
    telefone = Column(String(30), unique=True)
    provider = Column(String(20), nullable=False, default="LOCAL")
    provider_id = Column(String(255))
    avatar_url = Column(Text)
    criado_em = Column(DateTime(timezone=True), server_default=func.now())


class CodigoVerificacao(Base):
    __tablename__ = "codigos_verificacao"

    id = Column(BigInteger, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    codigo_hash = Column(String(64), nullable=False)
    finalidade = Column(String(30), nullable=False, default="RECUPERAR_SENHA")
    tentativas = Column(SmallInteger, nullable=False, default=0)
    usado = Column(Boolean, nullable=False, default=False)
    expira_em = Column(DateTime(timezone=True), nullable=False)
    criado_em = Column(DateTime(timezone=True), server_default=func.now())