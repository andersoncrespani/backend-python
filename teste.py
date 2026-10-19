from api.email import enviar_codigo_verificacao
from api.security import gerar_codigo


codigo = gerar_codigo()
print("Código gerado:", codigo)

ok = enviar_codigo_verificacao("seu_email@example.com", codigo)
print("Enviado?", ok)

