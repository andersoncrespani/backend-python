import os
from dotenv import load_dotenv

load_dotenv()

def _obrigatoria(nome: str) -> str:
    valor = os.getenv(nome)
    if not valor:
        raise RuntimeError(f"Variável de ambiente ausente: {nome}")
    return valor

EMAIL_REMETENTE = _obrigatoria("EMAIL_REMETENTE")
EMAIL_SENHA = _obrigatoria("EMAIL_SENHA")

DB_USER = _obrigatoria("DB_USER")
DB_PASSWORD = _obrigatoria("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = _obrigatoria("DB_NAME")

SECRET_KEY = _obrigatoria("SECRET_KEY")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
EXPIRATION_MINUTES = int(os.getenv("JWT_EXPIRATION_MINUTES", "60"))
GOOGLE_CLIENT_ID = _obrigatoria("GOOGLE_CLIENT_ID")