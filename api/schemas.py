from datetime import date
from typing import Annotated

from pydantic import AfterValidator, BaseModel, EmailStr, Field

MAX_BYTES_SENHA = 72  

def _minusculo(valor: str) -> str:
    return valor.lower()


def _cabe_no_bcrypt(valor: str) -> str:
    if len(valor.encode("utf-8")) > MAX_BYTES_SENHA:
        raise ValueError(
            "Senha longa demais: o limite é de 72 bytes (acentos e emojis contam mais de 1)"
        )
    return valor


Email = Annotated[EmailStr, AfterValidator(_minusculo)]
SenhaNova = Annotated[
    str,
    Field(min_length=8, max_length=72),
    AfterValidator(_cabe_no_bcrypt),
]


class UserCreate(BaseModel):
    nome: str
    email: Email
    senha: SenhaNova
    sexo: str
    data_nascimento: date | None = None
    telefone: str | None = None


class AlterarSenha(BaseModel):
    senha_atual: str = Field(min_length=1, max_length=72)
    nova_senha: SenhaNova


class LoginData(BaseModel):
    email: Email
    senha: str = Field(max_length=128)  


class PedirCodigo(BaseModel):
    email: Email


class VerificarCodigo(BaseModel):
    email: Email
    codigo: str = Field(pattern=r"^\d{6}$")


class NovaSenha(BaseModel):
    reset_token: str
    nova_senha: SenhaNova


class GoogleLogin(BaseModel):
    credential: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"