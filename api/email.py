import logging
from html import escape

import httpx

from .config import BREVO_API_KEY, EMAIL_REMETENTE, NOME_REMETENTE

logger = logging.getLogger(__name__)

BREVO_URL = "https://api.brevo.com/v3/smtp/email"
LOGO_URL = "https://raw.githubusercontent.com/jaq1997/informa-saude-frontend/main/informa-saude/src/assets/images/logo.svg"

ESTILO = """
body { font-family: Arial, sans-serif; background-color: #f4f7f6; margin: 0; padding: 0; }
.container { max-width: 600px; margin: 40px auto; background: #ffffff; border-radius: 8px;
             overflow: hidden; box-shadow: 0 4px 10px rgba(0, 0, 0, 0.05); }
.header { background-color: #00645a; text-align: center; padding: 14px 20px; }
.header img { max-height: 65px; width: auto; display: block; margin: 0 auto; }
.content { padding: 32px; color: #333333; font-size: 16px; line-height: 1.6; }
.code-box { background-color: #f0f7f6; border: 2px dashed #00645a; border-radius: 6px;
            font-size: 34px; font-weight: bold; letter-spacing: 8px; color: #00645a;
            text-align: center; padding: 16px; margin: 28px 0; }
.footer { text-align: center; padding: 16px; font-size: 13px; color: #ffffff; background-color: #00645a; }
"""


def _montar_html(conteudo: str) -> str:
    """Layout padrão dos e-mails: cabeçalho com logo, conteúdo e rodapé."""
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<style>{ESTILO}</style>
</head>
<body>
<div class="container">
<div class="header"><img src="{LOGO_URL}" alt="informa-Saúde"></div>
<div class="content">
{conteudo}
</div>
<div class="footer"><p>© informa-Saúde. Todos os direitos reservados.</p></div>
</div>
</body>
</html>"""


def enviar_email(
    destinatario: str,
    assunto: str,
    html: str,
    texto: str | None = None,
    nome_destinatario: str | None = None,
) -> bool:
    """Envia um e-mail transacional pela API do Brevo. Retorna True se aceito."""
    para = {"email": destinatario}
    if nome_destinatario:
        para["name"] = nome_destinatario

    payload = {
        "sender": {"name": NOME_REMETENTE, "email": EMAIL_REMETENTE},
        "to": [para],
        "subject": assunto,
        "htmlContent": html,
    }
    if texto:
        payload["textContent"] = texto

    try:
        resposta = httpx.post(
            BREVO_URL,
            json=payload,
            headers={"api-key": BREVO_API_KEY, "accept": "application/json"},
            timeout=10,
        )
        print(f"BREVO -> {destinatario}: {resposta.status_code} {resposta.text}")
        resposta.raise_for_status()
        return True
    except httpx.HTTPStatusError as e:
        logger.error("Erro Brevo (%s): %s", e.response.status_code, e.response.text)
        return False
    except httpx.HTTPError as e:
        logger.error("Erro ao enviar e-mail: %s", e)
        return False


def enviar_codigo_verificacao(destinatario: str, codigo: str) -> bool:
    texto_plano = (
        f"Olá!\n\nSeu código de verificação na informa-Saúde é: {codigo}\n\n"
        "Ele expira em 10 minutos. Se você não pediu este código, ignore este e-mail."
    )
    conteudo = f"""
<p>Olá,</p>
<p>Recebemos uma solicitação de acesso ou alteração em sua conta na <strong>informa-Saúde</strong>. Utilize o código abaixo para prosseguir:</p>
<div class="code-box">{escape(codigo)}</div>
<p>Este código <strong>expira em 10 minutos</strong>.</p>
<p>Se você não solicitou esta alteração, pode ignorar este e-mail com total segurança.</p>
"""
    return enviar_email(
        destinatario,
        "Seu código de verificação - informa-Saúde",
        _montar_html(conteudo),
        texto_plano,
    )