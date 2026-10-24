from datetime import datetime, timedelta, timezone
from .config import PROXIES_CONFIAVEIS
from fastapi import HTTPException, Request
from sqlalchemy import func
from sqlalchemy.orm import Session

from .models import LimiteRequisicao as L

GUARDA_DIAS = 1  


def ip_do_cliente(request: Request) -> str:
    """IP real do cliente.

    Sem proxy (PROXIES_CONFIAVEIS=0), usa o IP da conexão. Atrás de proxy, lê o
    X-Forwarded-For contando a partir do FIM da lista: cada proxy confiável
    acrescenta o IP de quem conectou nele, então o IP do cliente é o N-ésimo
    de trás para frente. Os IPs à esquerda podem ter sido forjados pelo cliente.
    """
    if PROXIES_CONFIAVEIS > 0:
        encaminhado = request.headers.get("x-forwarded-for", "")
        ips = [ip.strip() for ip in encaminhado.split(",") if ip.strip()]
        if len(ips) >= PROXIES_CONFIAVEIS:
            return ips[-PROXIES_CONFIAVEIS]
    return request.client.host if request.client else "desconhecido"


def k_email(email: str) -> str:
    return f"email:{email.lower()}"


def k_ip(ip: str) -> str:
    return f"ip:{ip}"


def k_usuario(user_id: int) -> str:
    return f"usuario:{user_id}"


def _contar(db: Session, acao: str, chave: str, janela_min: int) -> int:
    desde = datetime.now(timezone.utc) - timedelta(minutes=janela_min)
    return (
        db.query(func.count(L.id))
        .filter(L.acao == acao, L.chave == chave, L.criado_em >= desde)
        .scalar()
    )


def checar(db: Session, acao: str, regras: list[tuple[str, int, int]]):
    """regras: lista de (chave, máximo, janela em minutos). Levanta 429 se alguma estourou."""
    for chave, maximo, janela_min in regras:
        if _contar(db, acao, chave, janela_min) >= maximo:
            raise HTTPException(
                status_code=429,
                detail=f"Muitas tentativas. Tente novamente em {janela_min} minutos.",
                headers={"Retry-After": str(janela_min * 60)},
            )


def registrar(db: Session, acao: str, *chaves: str):
    db.add_all([L(acao=acao, chave=chave) for chave in chaves])
    db.query(L).filter(
        L.criado_em < datetime.now(timezone.utc) - timedelta(days=GUARDA_DIAS)
    ).delete(synchronize_session=False)
    db.commit()


def limpar(db: Session, acao: str, chave: str):
    db.query(L).filter(L.acao == acao, L.chave == chave).delete(synchronize_session=False)
    db.commit()