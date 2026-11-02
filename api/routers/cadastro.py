from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import limites, models, schemas, security
from ..codigos import emitir_codigo
from ..database import get_db
from ..regras import (
    CODIGO_POR_EMAIL,
    CODIGO_POR_IP,
    FINALIDADE_VERIFICAR_EMAIL,
    MAX_TENTATIVAS,
    PEDIR_POR_EMAIL,
    PEDIR_POR_IP,
    REGISTRO_POR_IP,
    RESPOSTA_PEDIR,
)

router = APIRouter(tags=["Cadastro"])


@router.post("/register", status_code=201)
def register(
    dados: schemas.UserCreate,
    request: Request,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
):
    chave_ip = limites.k_ip(limites.ip_do_cliente(request))
    limites.checar(db, "REGISTER", [(chave_ip, *REGISTRO_POR_IP)])
    limites.registrar(db, "REGISTER", chave_ip)

    duplicado = HTTPException(status_code=400, detail="E-mail ou telefone já cadastrados")

    existente = (
        db.query(models.User)
        .filter(func.lower(models.User.email) == dados.email)
        .first()
    )
    if existente and existente.email_verificado:
        raise duplicado

    if dados.telefone:
        consulta_telefone = db.query(models.User).filter(models.User.telefone == dados.telefone)
        if existente:
            consulta_telefone = consulta_telefone.filter(models.User.id != existente.id)
        if consulta_telefone.first():
            raise duplicado

    if existente:
        user = existente
        user.nome = dados.nome
        user.senha_hash = security.gerar_hash(dados.senha)
        user.sexo = dados.sexo
        user.data_nascimento = dados.data_nascimento
        user.telefone = dados.telefone
        user.token_version += 1
    else:
        user = models.User(
            nome=dados.nome,
            email=dados.email,
            senha_hash=security.gerar_hash(dados.senha),
            sexo=dados.sexo,
            data_nascimento=dados.data_nascimento,
            telefone=dados.telefone,
            provider="LOCAL",
            email_verificado=False,
        )
        db.add(user)

    db.commit()
    db.refresh(user)

    emitir_codigo(db, user, FINALIDADE_VERIFICAR_EMAIL, background)
    return {"id": user.id, "nome": user.nome, "email": user.email}


@router.post("/register/verificar")
def verificar_email(
    dados: schemas.VerificarCodigo,
    request: Request,
    db: Session = Depends(get_db),
):
    invalido = HTTPException(status_code=400, detail="Código inválido ou expirado")

    email = dados.email.lower()
    chave_email = limites.k_email(email)
    chave_ip = limites.k_ip(limites.ip_do_cliente(request))

    limites.checar(
        db, "EMAIL_CODIGO", [(chave_email, *CODIGO_POR_EMAIL), (chave_ip, *CODIGO_POR_IP)]
    )

    def recusar():
        limites.registrar(db, "EMAIL_CODIGO", chave_email, chave_ip)
        return invalido

    user = (
        db.query(models.User)
        .filter(func.lower(models.User.email) == email)
        .first()
    )
    if not user or user.email_verificado:
        raise recusar()

    CV = models.CodigoVerificacao
    registro = (
        db.query(CV)
        .filter(
            CV.user_id == user.id,
            CV.finalidade == FINALIDADE_VERIFICAR_EMAIL,
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
    user.email_verificado = True
    db.commit()
    limites.limpar(db, "EMAIL_CODIGO", chave_email)
    return {"mensagem": "E-mail verificado com sucesso"}


@router.post("/register/reenviar")
def reenviar_codigo_cadastro(
    dados: schemas.PedirCodigo,
    request: Request,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
):
    email = dados.email.lower()
    chave_email = limites.k_email(email)
    chave_ip = limites.k_ip(limites.ip_do_cliente(request))

    limites.checar(
        db, "EMAIL_PEDIR", [(chave_email, *PEDIR_POR_EMAIL), (chave_ip, *PEDIR_POR_IP)]
    )
    limites.registrar(db, "EMAIL_PEDIR", chave_email, chave_ip)

    user = (
        db.query(models.User)
        .filter(func.lower(models.User.email) == email)
        .first()
    )
    if not user or user.email_verificado:
        return RESPOSTA_PEDIR

    CV = models.CodigoVerificacao
    ultimo = (
        db.query(CV)
        .filter(CV.user_id == user.id, CV.finalidade == FINALIDADE_VERIFICAR_EMAIL)
        .order_by(CV.criado_em.desc())
        .first()
    )
    if ultimo and datetime.now(timezone.utc) - ultimo.criado_em < timedelta(seconds=60):
        return RESPOSTA_PEDIR

    emitir_codigo(db, user, FINALIDADE_VERIFICAR_EMAIL, background)
    return RESPOSTA_PEDIR