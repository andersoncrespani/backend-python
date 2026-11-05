import ipaddress
import logging
import random
from datetime import timedelta

from fastapi import HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .config import PROXIES_CONFIAVEIS
from .models import LimiteRequisicao as L

logger = logging.getLogger(__name__)

GUARDA_DIAS = 1
PROBABILIDADE_LIMPEZA = 0.02


def _normalizar_ip(ip: str) -> str:
    try:
        endereco = ipaddress.ip_address(ip)
    except ValueError:
        return ip
    if endereco.version == 6:
        if endereco.ipv4_mapped:
            return str(endereco.ipv4_mapped)
        return str(ipaddress.ip_network(f"{endereco}/64", strict=False))
    return str(endereco)


def ip_do_cliente(request: Request) -> str:
    if PROXIES_CONFIAVEIS > 0:
        encaminhado = request.headers.get("x-forwarded-for", "")
        ips = [ip.strip() for ip in encaminhado.split(",") if ip.strip()]
        if len(ips) >= PROXIES_CONFIAVEIS:
            return _normalizar_ip(ips[-PROXIES_CONFIAVEIS])
        logger.warning(
            "X-Forwarded-For com menos IPs que PROXIES_CONFIAVEIS=%s; usando o IP da conexão",
            PROXIES_CONFIAVEIS,
        )
    if request.client:
        return _normalizar_ip(request.client.host)
    return "desconhecido"


def k_email(email: str) -> str:
    return f"email:{email.lower()}"


def k_ip(ip: str) -> str:
    return f"ip:{ip}"


def k_usuario(user_id: int) -> str:
    return f"usuario:{user_id}"


def _travar(db: Session, acao: str, chaves: list[str]) -> None:
    for chave in sorted(set(chaves)):
        db.execute(
            select(func.pg_advisory_xact_lock(func.hashtextextended(f"{acao}|{chave}", 0)))
        )


def _contar(db: Session, acao: str, chave: str, janela_min: int) -> int:
    desde = func.now() - timedelta(minutes=janela_min)
    return (
        db.query(func.count(L.id))
        .filter(L.acao == acao, L.chave == chave, L.criado_em >= desde)
        .scalar()
    )


def checar(db: Session, acao: str, regras: list[tuple[str, int, int]]):
    _travar(db, acao, [chave for chave, _, _ in regras])
    for chave, maximo, janela_min in regras:
        if _contar(db, acao, chave, janela_min) >= maximo:
            raise HTTPException(
                status_code=429,
                detail=f"Muitas tentativas. Tente novamente em {janela_min} minutos.",
                headers={"Retry-After": str(janela_min * 60)},
            )


def registrar(db: Session, acao: str, *chaves: str):
    db.add_all([L(acao=acao, chave=chave) for chave in chaves])
    if random.random() < PROBABILIDADE_LIMPEZA:
        db.query(L).filter(
            L.criado_em < func.now() - timedelta(days=GUARDA_DIAS)
        ).delete(synchronize_session=False)
    db.commit()


def limpar(db: Session, acao: str, chave: str):
    db.query(L).filter(L.acao == acao, L.chave == chave).delete(synchronize_session=False)
    db.commit()