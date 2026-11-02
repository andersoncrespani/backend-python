import logging
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import limites, models, schemas, security
from ..codigos import emitir_codigo
from ..config import GOOGLE_CLIENT_ID
from ..database import get_db
from ..regras import (
    CODIGO_POR_EMAIL,
    CODIGO_POR_IP,
    FINALIDADE_RECUPERAR,
    LOGIN_POR_EMAIL,
    LOGIN_POR_IP,
    MAX_TENTATIVAS,
    PEDIR_POR_EMAIL,
    PEDIR_POR_IP,
    RESPOSTA_PEDIR,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Autenticação"])


@router.post("/auth/google", response_model=schemas.Token)
def login_google(dados: schemas.GoogleLogin, db: Session = Depends(get_db)):
    try:
        info = id_token.verify_oauth2_token(
            dados.credential,
            google_requests.Request(),
            GOOGLE_CLIENT_ID,
            clock_skew_in_seconds=10,
        )
    except ValueError:
        logger.warning("Falha ao validar a credencial do Google")
        raise HTTPException(status_code=401, detail="Credencial do Google inválida")

    if not info.get("email_verified"):
        raise HTTPException(status_code=401, detail="E-mail do Google não verificado")

    email = info["email"].lower()
    google_id = info["sub"]

    user = db.query(models.User).filter(func.lower(models.User.email) == email).first()

    if not user:
        user = models.User(
            nome=info.get("name") or email.split("@")[0],
            email=email,
            sexo="Outro / Prefiro não informar",
            provider="GOOGLE",
            provider_id=google_id,
            avatar_url=info.get("picture"),
            email_verificado=True,
        )
        db.add(user)
    else:
        if not user.provider_id:
            user.provider_id = google_id
            if user.senha_hash:
                user.senha_hash = None
                user.token_version += 1
        if not user.avatar_url:
            user.avatar_url = info.get("picture")
        user.email_verificado = True

    db.commit()
    db.refresh(user)
    return {"access_token": security.criar_token(user.id, user.email, user.token_version)}


@router.post("/login", response_model=schemas.Token)
def login(dados: schemas.LoginData, request: Request, db: Session = Depends(get_db)):
    email = dados.email.lower()
    chave_email = limites.k_email(email)
    chave_ip = limites.k_ip(limites.ip_do_cliente(request))

    limites.checar(db, "LOGIN", [(chave_email, *LOGIN_POR_EMAIL), (chave_ip, *LOGIN_POR_IP)])

    user = db.query(models.User).filter(func.lower(models.User.email) == email).first()

    if user and user.senha_hash:
        senha_ok = security.verificar_senha(dados.senha, user.senha_hash)
    else:
        security.gastar_tempo_de_hash(dados.senha)
        senha_ok = False

    if not senha_ok:
        limites.registrar(db, "LOGIN", chave_email, chave_ip)
        raise HTTPException(status_code=401, detail="E-mail ou senha inválidos")

    if not user.email_verificado:
        raise HTTPException(
            status_code=403,
            detail="Confirme seu e-mail antes de entrar. Refaça o cadastro para receber um novo código.",
        )

    limites.limpar(db, "LOGIN", chave_email)
    return {"access_token": security.criar_token(user.id, user.email, user.token_version)}


@router.post("/auth/recuperar/pedir")
def pedir_codigo(
    dados: schemas.PedirCodigo,
    request: Request,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
):
    email = dados.email.lower()
    chave_email = limites.k_email(email)
    chave_ip = limites.k_ip(limites.ip_do_cliente(request))

    limites.checar(db, "PEDIR", [(chave_email, *PEDIR_POR_EMAIL), (chave_ip, *PEDIR_POR_IP)])
    limites.registrar(db, "PEDIR", chave_email, chave_ip)

    user = (
        db.query(models.User)
        .filter(func.lower(models.User.email) == email)
        .first()
    )

    if not user:
        return RESPOSTA_PEDIR

    CV = models.CodigoVerificacao
    ultimo = (
        db.query(CV)
        .filter(CV.user_id == user.id, CV.finalidade == FINALIDADE_RECUPERAR)
        .order_by(CV.criado_em.desc())
        .first()
    )

    if ultimo and datetime.now(timezone.utc) - ultimo.criado_em < timedelta(seconds=60):
        return RESPOSTA_PEDIR

    emitir_codigo(db, user, FINALIDADE_RECUPERAR, background)
    return RESPOSTA_PEDIR


@router.post("/auth/recuperar/verificar")
def verificar_codigo(
    dados: schemas.VerificarCodigo,
    request: Request,
    db: Session = Depends(get_db),
):
    invalido = HTTPException(status_code=400, detail="Código inválido ou expirado")

    email = dados.email.lower()
    chave_email = limites.k_email(email)
    chave_ip = limites.k_ip(limites.ip_do_cliente(request))

    limites.checar(db, "CODIGO", [(chave_email, *CODIGO_POR_EMAIL), (chave_ip, *CODIGO_POR_IP)])

    def recusar():
        limites.registrar(db, "CODIGO", chave_email, chave_ip)
        return invalido

    user = (
        db.query(models.User)
        .filter(func.lower(models.User.email) == email)
        .first()
    )
    if not user:
        raise recusar()

    CV = models.CodigoVerificacao
    registro = (
        db.query(CV)
        .filter(
            CV.user_id == user.id,
            CV.finalidade == FINALIDADE_RECUPERAR,
            CV.usado == False,
        )
        .order_by(CV.criado_em.desc())
        .first()
    )
    if not registro or registro.expira_em < datetime.now(timezone.utc):
        raise recusar()

    if registro.tentativas >= MAX_TENTATIVAS:
        raise HTTPException(status_code=429, detail="Muitas tentativas. Peça um novo código.")

    if not security.codigo_confere(dados.codigo, registro.codigo_hash):
        registro.tentativas += 1
        db.commit()
        raise recusar()

    registro.usado = True
    db.commit()
    limites.limpar(db, "CODIGO", chave_email)
    return {"reset_token": security.criar_reset_token(user.id, user.token_version)}


@router.post("/auth/recuperar/nova-senha")
def nova_senha(dados: schemas.NovaSenha, db: Session = Depends(get_db)):
    sessao_invalida = HTTPException(
        status_code=400, detail="Sessão de recuperação inválida ou expirada"
    )

    try:
        user_id, versao = security.ler_reset_token(dados.reset_token)
    except (jwt.PyJWTError, ValueError, TypeError, KeyError):
        raise sessao_invalida

    user = db.get(models.User, user_id)

    if not user or user.token_version != versao:
        raise sessao_invalida

    user.senha_hash = security.gerar_hash(dados.nova_senha)
    user.token_version += 1
    user.email_verificado = True

    CV = models.CodigoVerificacao
    db.query(CV).filter(CV.user_id == user.id, CV.usado == False).update({"usado": True})

    db.commit()
    return {"mensagem": "Senha alterada com sucesso"}