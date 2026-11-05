from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import limites, models, schemas, security
from ..database import get_db
from ..dependencias import usuario_atual
from ..email import enviar_aviso_senha_alterada
from ..regras import SENHA_ATUAL_POR_USUARIO

router = APIRouter(tags=["Usuário"])


@router.get("/me")
def me(user: models.User = Depends(usuario_atual)):
    return {
        "id": user.id,
        "nome": user.nome,
        "email": user.email,
        "avatar_url": user.avatar_url,
    }


@router.post("/me/senha")
def alterar_senha(
    dados: schemas.AlterarSenha,
    background: BackgroundTasks,
    user: models.User = Depends(usuario_atual),
    db: Session = Depends(get_db),
):
    if not user.senha_hash:
        raise HTTPException(
            status_code=400,
            detail="Sua conta usa o login do Google e ainda não tem senha. Use 'Esqueci minha senha' para criar uma.",
        )

    chave = limites.k_usuario(user.id)
    limites.checar(db, "SENHA_ATUAL", [(chave, *SENHA_ATUAL_POR_USUARIO)])

    if not security.verificar_senha(dados.senha_atual, user.senha_hash):
        limites.registrar(db, "SENHA_ATUAL", chave)
        raise HTTPException(status_code=400, detail="Senha atual incorreta")

    if dados.senha_atual == dados.nova_senha:
        raise HTTPException(status_code=400, detail="A nova senha precisa ser diferente da atual")

    user.senha_hash = security.gerar_hash(dados.nova_senha)
    user.token_version += 1
    db.commit()
    limites.limpar(db, "SENHA_ATUAL", chave)

    background.add_task(enviar_aviso_senha_alterada, user.email)

    return {
        "mensagem": "Senha alterada com sucesso",
        "access_token": security.criar_token(user.id, user.email, user.token_version),
    }