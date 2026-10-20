import os

from dotenv import load_dotenv

load_dotenv()


def _obrigatoria(nome: str) -> str:
    valor = os.getenv(nome)
    if not valor:
        raise RuntimeError(f"Variável de ambiente ausente: {nome}")
    return valor


AMBIENTE = os.getenv("AMBIENTE", "desenvolvimento").strip().lower()
EM_PRODUCAO = AMBIENTE in ("producao", "produção", "production", "prod")


EMAIL_REMETENTE = _obrigatoria("EMAIL_REMETENTE")
NOME_REMETENTE = os.getenv("NOME_REMETENTE", "Informa-Saúde")
BREVO_API_KEY = _obrigatoria("BREVO_API_KEY")

DB_USER = _obrigatoria("DB_USER")
DB_PASSWORD = _obrigatoria("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = _obrigatoria("DB_NAME")

SECRET_KEY = _obrigatoria("SECRET_KEY")
if len(SECRET_KEY) < 32:
    raise RuntimeError(
        "SECRET_KEY muito curta (mínimo de 32 caracteres). "
        'Gere uma com: python -c "import secrets; print(secrets.token_urlsafe(48))"'
    )
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
EXPIRATION_MINUTES = int(os.getenv("JWT_EXPIRATION_MINUTES", "60"))

GOOGLE_CLIENT_ID = _obrigatoria("GOOGLE_CLIENT_ID")

CORS_ORIGINS = [
    origem.strip()
    for origem in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000",
    ).split(",")
    if origem.strip()
]