import logging
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from . import models, schemas, security
from .config import CORS_ORIGINS, GOOGLE_CLIENT_ID
from .database import get_db
from .email import enviar_codigo_verificacao

logger = logging.getLogger(__name__)

app = FastAPI()
bearer = HTTPBearer()

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

CODIGO_VALIDADE_MIN = 10
MAX_TENTATIVAS = 5
RESPOSTA_PEDIR = {"mensagem": "Se o e-mail estiver cadastrado, enviaremos um código."}


JANELA_LOGIN_MIN = 15
MAX_FALHAS_POR_EMAIL = 5
MAX_FALHAS_POR_IP = 20


def ip_do_cliente(request: Request) -> str:
    return request.client.host if request.client else "desconhecido"


def checar_bloqueio_login(db: Session, email: str, ip: str):
    desde = datetime.now(timezone.utc) - timedelta(minutes=JANELA_LOGIN_MIN)
    TL = models.TentativaLogin

    falhas_email = (
        db.query(func.count(TL.id))
        .filter(TL.email == email, TL.criado_em >= desde)
        .scalar()
    )
    falhas_ip = (
        db.query(func.count(TL.id))
        .filter(TL.ip == ip, TL.criado_em >= desde)
        .scalar()
    )

    if falhas_email >= MAX_FALHAS_POR_EMAIL or falhas_ip >= MAX_FALHAS_POR_IP:
        raise HTTPException(
            status_code=429,
            detail=f"Muitas tentativas de login. Tente novamente em {JANELA_LOGIN_MIN} minutos.",
            headers={"Retry-After": str(JANELA_LOGIN_MIN * 60)},
        )


@app.post("/auth/google", response_model=schemas.Token)
def login_google(dados: schemas.GoogleLogin, db: Session = Depends(get_db)):
    try:
        info = id_token.verify_oauth2_token(
            dados.credential,
            google_requests.Request(),
            GOOGLE_CLIENT_ID,
            clock_skew_in_seconds=10,
        )
    except ValueError:
        # não loga a exceção: a mensagem pode carregar pedaços do token
        logger.warning("Falha ao validar a credencial do Google")
        raise HTTPException(status_code=401, detail="Credencial do Google inválida")

    if not info.get("email_verified"):
        raise HTTPException(status_code=401, detail="E-mail do Google não verificado")

    email = info["email"].lower()
    google_id = info["sub"]

    user = db.query(models.User).filter(models.User.email == email).first()

    if not user:
        user = models.User(
            nome=info.get("name") or email.split("@")[0],
            email=email,
            sexo="Outro / Prefiro não informar",  # o Google não fornece, e a coluna é obrigatória
            provider="GOOGLE",
            provider_id=google_id,
            avatar_url=info.get("picture"),
        )
        db.add(user)
    else:
        if not user.provider_id:
            user.provider_id = google_id
        if not user.avatar_url:
            user.avatar_url = info.get("picture")

    db.commit()
    db.refresh(user)
    return {"access_token": security.criar_token(user.id, user.email)}


@app.post("/register", status_code=201)
def register(dados: schemas.UserCreate, db: Session = Depends(get_db)):
    filtros = [models.User.email == dados.email]
    if dados.telefone:
        filtros.append(models.User.telefone == dados.telefone)

    if db.query(models.User).filter(or_(*filtros)).first():
        raise HTTPException(status_code=400, detail="E-mail ou telefone já cadastrados")

    user = models.User(
        nome=dados.nome,
        email=dados.email,
        senha_hash=security.gerar_hash(dados.senha),
        sexo=dados.sexo,
        data_nascimento=dados.data_nascimento,
        telefone=dados.telefone,
        provider="LOCAL",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"id": user.id, "nome": user.nome, "email": user.email}


@app.post("/auth/recuperar/pedir")
def pedir_codigo(
    dados: schemas.PedirCodigo,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
):
    user = (
        db.query(models.User)
        .filter(func.lower(models.User.email) == dados.email.lower())
        .first()
    )
    if not user:
        return RESPOSTA_PEDIR

    CV = models.CodigoVerificacao
    ultimo = (
        db.query(CV)
        .filter(CV.user_id == user.id, CV.finalidade == "RECUPERAR_SENHA")
        .order_by(CV.criado_em.desc())
        .first()
    )

    if ultimo and datetime.now(timezone.utc) - ultimo.criado_em < timedelta(seconds=60):
        return RESPOSTA_PEDIR

    db.query(CV).filter(
        CV.user_id == user.id,
        CV.finalidade == "RECUPERAR_SENHA",
        CV.usado == False,
    ).update({"usado": True})

    codigo = security.gerar_codigo()
    db.add(CV(
        user_id=user.id,
        codigo_hash=security.hash_codigo(codigo),
        expira_em=datetime.now(timezone.utc) + timedelta(minutes=CODIGO_VALIDADE_MIN),
    ))
    db.commit()

    background.add_task(enviar_codigo_verificacao, user.email, codigo)
    return RESPOSTA_PEDIR


@app.post("/auth/recuperar/verificar")
def verificar_codigo(dados: schemas.VerificarCodigo, db: Session = Depends(get_db)):
    invalido = HTTPException(status_code=400, detail="Código inválido ou expirado")

    user = (
        db.query(models.User)
        .filter(func.lower(models.User.email) == dados.email.lower())
        .first()
    )
    if not user:
        raise invalido

    CV = models.CodigoVerificacao
    registro = (
        db.query(CV)
        .filter(
            CV.user_id == user.id,
            CV.finalidade == "RECUPERAR_SENHA",
            CV.usado == False,
        )
        .order_by(CV.criado_em.desc())
        .first()
    )
    if not registro or registro.expira_em < datetime.now(timezone.utc):
        raise invalido

    if registro.tentativas >= MAX_TENTATIVAS:
        raise HTTPException(status_code=429, detail="Muitas tentativas. Peça um novo código.")

    if not security.codigo_confere(dados.codigo, registro.codigo_hash):
        registro.tentativas += 1
        db.commit()
        raise invalido

    registro.usado = True
    db.commit()
    return {"reset_token": security.criar_reset_token(user.id)}


@app.post("/auth/recuperar/nova-senha")
def nova_senha(dados: schemas.NovaSenha, db: Session = Depends(get_db)):
    try:
        user_id = security.ler_reset_token(dados.reset_token)
    except jwt.PyJWTError:
        raise HTTPException(status_code=400, detail="Sessão de recuperação inválida ou expirada")

    user = db.get(models.User, user_id)
    if not user:
        raise HTTPException(status_code=400, detail="Sessão de recuperação inválida ou expirada")

    user.senha_hash = security.gerar_hash(dados.nova_senha)
    db.commit()
    return {"mensagem": "Senha alterada com sucesso"}


@app.post("/login", response_model=schemas.Token)
def login(dados: schemas.LoginData, request: Request, db: Session = Depends(get_db)):
    email = dados.email.lower()
    ip = ip_do_cliente(request)

    
    checar_bloqueio_login(db, email, ip)

    user = db.query(models.User).filter(func.lower(models.User.email) == email).first()
    if not user or not user.senha_hash or not security.verificar_senha(dados.senha, user.senha_hash):
        TL = models.TentativaLogin
        db.add(TL(email=email, ip=ip))
        
        db.query(TL).filter(
            TL.criado_em < datetime.now(timezone.utc) - timedelta(days=1)
        ).delete()
        db.commit()
        raise HTTPException(status_code=401, detail="E-mail ou senha inválidos")

    
    db.query(models.TentativaLogin).filter(models.TentativaLogin.email == email).delete()
    db.commit()

    return {"access_token": security.criar_token(user.id, user.email)}


def usuario_atual(
    cred: HTTPAuthorizationCredentials = Depends(bearer),
    db: Session = Depends(get_db),
):
    try:
        user_id = security.ler_token(cred.credentials)
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado")

    user = db.get(models.User, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Usuário não encontrado")
    return user


@app.get("/me")
def me(user: models.User = Depends(usuario_atual)):
    return {
        "id": user.id,
        "nome": user.nome,
        "email": user.email,
        "avatar_url": user.avatar_url,
    }

@app.post("/me/senha")
def alterar_senha(
    dados: schemas.AlterarSenha,
    user: models.User = Depends(usuario_atual),
    db: Session = Depends(get_db),
):
    if not user.senha_hash:
        raise HTTPException(
            status_code=400,
            detail="Sua conta usa o login do Google e ainda não tem senha. Use 'Esqueci minha senha' para criar uma.",
        )

    if not security.verificar_senha(dados.senha_atual, user.senha_hash):
        raise HTTPException(status_code=400, detail="Senha atual incorreta")

    if dados.senha_atual == dados.nova_senha:
        raise HTTPException(status_code=400, detail="A nova senha precisa ser diferente da atual")

    user.senha_hash = security.gerar_hash(dados.nova_senha)
    db.commit()
    return {"mensagem": "Senha alterada com sucesso"}

