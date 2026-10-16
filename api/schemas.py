from datetime import date
from typing import Annotated

from pydantic import AfterValidator, BaseModel, EmailStr, Field


def normalizar_email(v: str) -> str:
    v = v.strip().lower()
    if len(v) > 180:
        raise ValueError("E-mail muito longo")
    return v


Email = Annotated[EmailStr, AfterValidator(normalizar_email)]


class UserCreate(BaseModel):
    nome: str = Field(min_length=1, max_length=120)
    email: Email
    senha: str = Field(min_length=8, max_length=72)
    sexo: str = Field(min_length=1, max_length=50)
    data_nascimento: date | None = None
    telefone: str | None = Field(default=None, max_length=30)


class AlterarSenha(BaseModel):
    senha_atual: str = Field(min_length=1, max_length=72)
    nova_senha: str = Field(min_length=8, max_length=72)


class LoginData(BaseModel):
    email: Email
    senha: str = Field(min_length=1, max_length=72)


class PedirCodigo(BaseModel):
    email: Email


class VerificarCodigo(BaseModel):
    email: Email
    codigo: str = Field(pattern=r"^\d{6}$")


class NovaSenha(BaseModel):
    reset_token: str = Field(max_length=2000)
    nova_senha: str = Field(min_length=8, max_length=72)


class GoogleLogin(BaseModel):
    credential: str = Field(max_length=5000)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"