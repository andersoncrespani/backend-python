from api.email import enviar_email

ok = enviar_email(
    "andersonpessoal2007@gmail.com",
    "Teste Brevo",
    "<p>Funcionou!</p>",
    "Funcionou!",
)
print("Resultado:", ok)