from datetime import date
from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    nome: str
    email: EmailStr
    senha: str = Field(min_length=8, max_length=72)
    sexo: str
    data_nascimento: date | None = None
    telefone: str | None = None

class AlterarSenha(BaseModel):
    senha_atual: str = Field(min_length=1, max_length=72)
    nova_senha: str = Field(min_length=8, max_length=72)

class LoginData(BaseModel):
    email: EmailStr
    senha: str

class PedirCodigo(BaseModel):
    email: EmailStr

class VerificarCodigo(BaseModel):
    email: EmailStr
    codigo: str = Field(pattern=r"^\d{6}$")

class NovaSenha(BaseModel):
    reset_token: str
    nova_senha: str = Field(min_length=8, max_length=72)

class GoogleLogin(BaseModel):
    credential: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"