import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from . import models, security
from .database import get_db

bearer = HTTPBearer()


def usuario_atual(
    cred: HTTPAuthorizationCredentials = Depends(bearer),
    db: Session = Depends(get_db),
):
    try:
        user_id, versao = security.ler_token(cred.credentials)
    except (jwt.PyJWTError, ValueError, TypeError, KeyError):
        raise HTTPException(status_code=401, detail="Token inválido ou expirado")

    user = db.get(models.User, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Usuário não encontrado")
    if user.token_version != versao:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado")
    return user