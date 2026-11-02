from datetime import datetime, timedelta, timezone

from fastapi import BackgroundTasks
from sqlalchemy.orm import Session

from . import models, security
from .email import enviar_codigo_verificacao
from .regras import CODIGO_VALIDADE_MIN


def emitir_codigo(db: Session, user: models.User, finalidade: str, background: BackgroundTasks):
    CV = models.CodigoVerificacao
    db.query(CV).filter(
        CV.user_id == user.id,
        CV.finalidade == finalidade,
        CV.usado == False,
    ).update({"usado": True})

    codigo = security.gerar_codigo()
    db.add(CV(
        user_id=user.id,
        codigo_hash=security.hash_codigo(codigo),
        finalidade=finalidade,
        expira_em=datetime.now(timezone.utc) + timedelta(minutes=CODIGO_VALIDADE_MIN),
    ))
    db.commit()

    background.add_task(enviar_codigo_verificacao, user.email, codigo)