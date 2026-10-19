import logging
import smtplib
from email.message import EmailMessage

from .config import EMAIL_REMETENTE, EMAIL_SENHA

logger = logging.getLogger(__name__)


def enviar_codigo_verificacao(destinatario: str, codigo: str) -> bool:
  msg = EmailMessage()
  msg["From"] = EMAIL_REMETENTE
  msg["To"] = destinatario
  msg["Subject"] = "Seu código de verificação - Enforma-Saúde"

  texto_plano = (
      f"Olá!\n\nSeu código de verificação na Enforma-Saúde é: {codigo}\n\n"
      "Ele expira em 10 minutos. Se você não pediu este código, ignore este e-mail."
  )

  html_conteudo = f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<style>
  body {{
    font-family: Arial, sans-serif;
    background-color: #f4f7f6;
    margin: 0;
    padding: 0;
  }}
  .container {{
    max-width: 600px;
    margin: 40px auto;
    background: #ffffff;
    border-radius: 8px;
    overflow: hidden;
    box-shadow: 0 4px 10px rgba(0, 0, 0, 0.05);
  }}
  .header {{
    background-color: #00645a;
    text-align: center;
    padding: 14px 20px;
  }}
  .header img {{
    max-height: 65px;
    width: auto;
    display: block;
    margin: 0 auto;
  }}
  .content {{
    padding: 32px;
    color: #333333;
    font-size: 16px;
    line-height: 1.6;
  }}
  .code-box {{
    background-color: #f0f7f6;
    border: 2px dashed #00645a;
    border-radius: 6px;
    font-size: 34px;
    font-weight: bold;
    letter-spacing: 8px;
    color: #00645a;
    text-align: center;
    padding: 16px;
    margin: 28px 0;
  }}
  .footer {{
    text-align: center;
    padding: 16px;
    font-size: 13px;
    color: #ffffff;
    background-color: #00645a;
  }}
</style>
</head>
<body>
  <div class="container">
    <div class="header">
      <img src="https://raw.githubusercontent.com/jaq1997/informa-saude-frontend/main/informa-saude/src/assets/images/logo.svg" alt="informa-Saúde">
    </div>
    <div class="content">
      <p>Olá,</p>
      <p>Recebemos uma solicitação de acesso ou alteração em sua conta na <strong>informa-Saúde</strong>. Utilize o código abaixo para prosseguir:</p>
      <div class="code-box">{codigo}</div>
      <p>Este código <strong>expira em 10 minutos</strong>.</p>
      <p>Se você não solicitou esta alteração, pode ignorar este e-mail com total segurança.</p>
    </div>
    <div class="footer">
      <p>© informa-Saúde. Todos os direitos reservados.</p>
    </div>
  </div>
</body>
</html>
"""

  msg.set_content(texto_plano)
  msg.add_alternative(html_conteudo, subtype="html")

  try:
    with smtplib.SMTP("smtp.gmail.com", 587, timeout=10) as servidor:
      servidor.starttls()
      servidor.login(EMAIL_REMETENTE, EMAIL_SENHA)
      servidor.send_message(msg)
    return True
  except Exception as e:
    logger.error("Falha ao enviar e-mail de verificação (%s)", type(e).__name__)
    return False