from datetime import datetime, timedelta, timezone
import hmac, hashlib, secrets
from .config import SECRET_KEY
import jwt
from passlib.context import CryptContext
from .config import SECRET_KEY, ALGORITHM, EXPIRATION_MINUTES

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

def codigo_confere(codigo: str, hash_salvo: str) -> bool:
    return hmac.compare_digest(hash_codigo(codigo), hash_salvo)
    
def criar_reset_token(user_id: int) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=15)
    return jwt.encode(
        {"sub": str(user_id), "purpose": "reset", "exp": exp},
        SECRET_KEY,
        algorithm=ALGORITHM,
    )

def ler_reset_token(token: str) -> int:
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    if payload.get("purpose") != "reset":
        raise jwt.InvalidTokenError("Token não é de redefinição de senha")
    return int(payload["sub"])

def gerar_hash(senha: str) -> str:
    return pwd.hash(senha)


def verificar_senha(senha: str, senha_hash: str) -> bool:
    return pwd.verify(senha, senha_hash)


def criar_token(user_id: int, email: str) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=EXPIRATION_MINUTES)
    dados_token = {
        "sub": str(user_id),
        "email": email,
        "exp": exp,
    }
    return jwt.encode(dados_token, SECRET_KEY, algorithm=ALGORITHM)


def ler_token(token: str) -> int:
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    if payload.get("purpose"):
        raise jwt.InvalidTokenError("Token não é de acesso")
    return int(payload.get("sub"))

def gerar_codigo() -> str:
    return f"{secrets.randbelow(10**6):06d}"   

def hash_codigo(codigo: str) -> str:
    return hmac.new(SECRET_KEY.encode(), codigo.encode(), hashlib.sha256).hexdigest()