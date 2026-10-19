import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from passlib.context import CryptContext

from .config import ALGORITHM, EXPIRATION_MINUTES, SECRET_KEY

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


MAX_BYTES_SENHA = 72


_HASH_FALSO = pwd.hash("senha-falsa-para-igualar-o-tempo")


def senha_cabe(senha: str) -> bool:
    return len(senha.encode("utf-8")) <= MAX_BYTES_SENHA


def gerar_hash(senha: str) -> str:
    return pwd.hash(senha)


def verificar_senha(senha: str, senha_hash: str) -> bool:
    if not senha_cabe(senha):
        return False
    return pwd.verify(senha, senha_hash)


def gastar_tempo_de_hash(senha: str) -> None:
    """Faz uma conferência de mentira, para o login demorar igual com e sem e-mail cadastrado."""
    if senha_cabe(senha):
        pwd.verify(senha, _HASH_FALSO)


def gerar_codigo() -> str:
    return f"{secrets.randbelow(10**6):06d}"


def hash_codigo(codigo: str) -> str:
    return hmac.new(SECRET_KEY.encode(), codigo.encode(), hashlib.sha256).hexdigest()


def codigo_confere(codigo: str, hash_salvo: str) -> bool:
    return hmac.compare_digest(hash_codigo(codigo), hash_salvo)


def criar_token(user_id: int, email: str, token_version: int) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=EXPIRATION_MINUTES)
    dados_token = {
        "sub": str(user_id),
        "email": email,
        "tv": token_version,
        "exp": exp,
    }
    return jwt.encode(dados_token, SECRET_KEY, algorithm=ALGORITHM)


def ler_token(token: str) -> tuple[int, int]:
    """Devolve (user_id, token_version)."""
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    if payload.get("purpose"):
        raise jwt.InvalidTokenError("Token não é de acesso")
    return int(payload["sub"]), int(payload.get("tv", 0))


def criar_reset_token(user_id: int, token_version: int) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=15)
    return jwt.encode(
        {"sub": str(user_id), "purpose": "reset", "tv": token_version, "exp": exp},
        SECRET_KEY,
        algorithm=ALGORITHM,
    )


def ler_reset_token(token: str) -> tuple[int, int]:
    """Devolve (user_id, token_version)."""
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    if payload.get("purpose") != "reset":
        raise jwt.InvalidTokenError("Token não é de redefinição de senha")
    return int(payload["sub"]), int(payload.get("tv", 0))