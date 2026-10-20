# Informa-Saúde — Backend

API REST em **FastAPI** para autenticação e gerenciamento de contas de usuários do Informa-Saúde. Ela cuida de:

- cadastro e login (com e-mail e senha, ou com a conta do Google);
- recuperação de senha por um **código enviado por e-mail** (o envio é feito pelo [Brevo](https://www.brevo.com));
- troca de senha;
- proteções contra abuso (limite de tentativas).

> **Nunca usou um projeto assim?** Siga a seção [Como rodar (passo a passo)](#como-rodar-passo-a-passo) na ordem. Se algo der errado, veja [Problemas comuns](#problemas-comuns).

## Índice

- [Funcionalidades](#funcionalidades)
- [Tecnologias](#tecnologias)
- [Estrutura do projeto](#estrutura-do-projeto)
- [Antes de começar](#antes-de-começar)
- [Como rodar (passo a passo)](#como-rodar-passo-a-passo)
- [Configurando o envio de e-mail (Brevo)](#configurando-o-envio-de-e-mail-brevo)
- [Variáveis de ambiente](#variáveis-de-ambiente)
- [Banco de dados](#banco-de-dados)
- [Endpoints](#endpoints)
- [Testando a API](#testando-a-api)
- [Recuperação de senha](#recuperação-de-senha)
- [Segurança](#segurança)
- [Conectando o front-end](#conectando-o-front-end)
- [Problemas comuns](#problemas-comuns)
- [Produção](#produção)

## Funcionalidades

- Cadastro e login com e-mail e senha (a senha é guardada com hash bcrypt, nunca em texto puro)
- Login com Google
- Recuperação de senha em 3 passos, com código de 6 dígitos enviado por e-mail (via Brevo)
- Autenticação por JWT (um "crachá" digital que o usuário recebe ao entrar), com sessões invalidadas quando a senha muda
- Perfil do usuário (`/me`) e troca de senha
- Limite de tentativas em login, cadastro e códigos de recuperação
- Documentação interativa automática em `/docs` (desativada em produção)

## Tecnologias

- Python 3.10 ou mais novo
- FastAPI e Uvicorn (a API e o servidor que a executa)
- PostgreSQL com SQLAlchemy (o banco de dados)
- PyJWT e Passlib/bcrypt (login seguro)
- google-auth (login com Google)
- Pydantic v2 com `email-validator` (validação dos dados recebidos)
- httpx (comunicação com a API do Brevo para enviar e-mails)
- python-dotenv (leitura do arquivo `.env`)

## Estrutura do projeto

```
backend-python/
├── api/
│   ├── main.py        # as rotas da API e as regras de negócio
│   ├── config.py      # lê as configurações do arquivo .env
│   ├── database.py    # conexão com o PostgreSQL
│   ├── models.py      # as tabelas do banco (SQLAlchemy)
│   ├── schemas.py     # formato dos dados que a API aceita e devolve
│   ├── security.py    # senhas, tokens JWT e códigos de verificação
│   ├── limites.py     # limite de tentativas por e-mail, IP e usuário
│   └── email.py       # envio de e-mails pela API do Brevo
├── requirements.txt   # lista das bibliotecas do projeto
└── .env               # suas configurações locais (NÃO vai para o Git)
```

## Antes de começar

Você precisa ter instalado ou criado:

| O que | Para quê | Onde conseguir |
| --- | --- | --- |
| **Python 3.10+** | rodar o projeto | https://www.python.org/downloads/ |
| **PostgreSQL** | guardar os dados | https://www.postgresql.org/download/ |
| **Git** | baixar o projeto | https://git-scm.com/downloads |
| **Conta no Brevo** | enviar os e-mails de código | https://www.brevo.com |
| **Client ID do Google** | login com Google | https://console.cloud.google.com/apis/credentials |

> Dica para Windows: ao instalar o Python, marque a opção **"Add Python to PATH"**.

## Como rodar (passo a passo)

### 1. Baixar o projeto

```
git clone https://github.com/andersoncrespani/backend-python.git
cd backend-python
```

### 2. Criar o ambiente virtual

O ambiente virtual (`venv`) é uma "caixinha" onde ficam só as bibliotecas deste projeto, para não misturar com o resto do computador.

```
python -m venv venv
```

Agora **ative** o ambiente (precisa fazer isso toda vez que abrir um terminal novo):

- **Windows (PowerShell):** `.\venv\Scripts\activate`
- **Windows (Prompt de Comando):** `venv\Scripts\activate.bat`
- **Mac / Linux:** `source venv/bin/activate`

Quando der certo, aparece `(venv)` no começo da linha do terminal.

> No PowerShell, se aparecer um erro dizendo que a execução de scripts está desabilitada, rode uma vez: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` e tente ativar de novo.

### 3. Instalar as bibliotecas

Com o `(venv)` ativo:

```
pip install -r requirements.txt
```

Se o projeto ainda não tiver o `requirements.txt`, instale manualmente:

```
pip install fastapi "uvicorn[standard]" sqlalchemy psycopg2-binary python-dotenv pyjwt "passlib[bcrypt]" google-auth requests email-validator httpx
```

### 4. Criar o banco de dados

Crie um banco vazio no PostgreSQL (pelo pgAdmin, ou pelo terminal):

```
psql -U postgres -c "CREATE DATABASE nome_do_seu_banco;"
```

Depois crie as tabelas rodando o SQL da seção [Banco de dados](#banco-de-dados). No pgAdmin, abra o banco, clique em *Query Tool*, cole o SQL e execute.

### 5. Configurar o envio de e-mail

Siga a seção [Configurando o envio de e-mail (Brevo)](#configurando-o-envio-de-e-mail-brevo). É rápido, e sem isso o código de recuperação de senha não chega.

### 6. Criar o arquivo `.env`

Na pasta principal do projeto (a mesma do `README.md`), crie um arquivo chamado **`.env`** (com o ponto na frente, sem extensão) e preencha conforme [Variáveis de ambiente](#variáveis-de-ambiente).

### 7. Ligar a API

Com o PostgreSQL funcionando e o `(venv)` ativo:

```
uvicorn api.main:app --reload
```

Se aparecer `Application startup complete`, deu certo. A API fica em `http://localhost:8000` e a documentação interativa em `http://localhost:8000/docs`.

## Configurando o envio de e-mail (Brevo)

A API envia o código de recuperação de senha pelo **Brevo**, um serviço de e-mail. São três passos:

**1. Criar a conta**
Crie uma conta gratuita em https://www.brevo.com e confirme o seu e-mail.

**2. Gerar a chave de API**
No painel do Brevo, abra o menu da sua conta e vá em **SMTP & API → API Keys**. Clique em gerar uma nova chave, dê um nome (por exemplo, `informa-saude`) e copie. Ela começa com `xkeysib-`. Guarde em um lugar seguro, porque ela só é mostrada uma vez. Esta chave vai no `.env` como `BREVO_API_KEY`.

**3. Validar o remetente**
O remetente é o endereço que aparece no "De:" do e-mail. O Brevo só envia por endereços que você comprovou ser seus:

1. Vá em **Senders, Domains & Dedicated IPs → Senders**.
2. Clique em *Add a sender*, informe o nome e o e-mail.
3. O Brevo manda uma mensagem de confirmação para esse e-mail. Abra e confirme.
4. Use **exatamente esse e-mail** no `EMAIL_REMETENTE` do `.env`.

> **Dica para os e-mails não caírem no spam:** prefira um endereço de domínio próprio (como `contato@seusite.com.br`) e configure o SPF e o DKIM do domínio no painel do Brevo. Remetentes `@gmail.com`, `@hotmail.com` ou `@outlook.com` costumam ser tratados como spam ou recusados.

## Variáveis de ambiente

São as configurações do projeto, guardadas no arquivo `.env`.

| Variável | Obrigatória | O que é |
| --- | --- | --- |
| `DB_USER` | sim | Usuário do PostgreSQL |
| `DB_PASSWORD` | sim | Senha do PostgreSQL |
| `DB_NAME` | sim | Nome do banco que você criou |
| `DB_HOST` | não | Onde está o banco. Padrão: `localhost` |
| `DB_PORT` | não | Porta do banco. Padrão: `5432` |
| `SECRET_KEY` | sim | Chave secreta usada nos tokens e códigos. **Mínimo de 32 caracteres** |
| `JWT_ALGORITHM` | não | Padrão: `HS256` |
| `JWT_EXPIRATION_MINUTES` | não | Por quantos minutos o login vale. Padrão: `60` |
| `GOOGLE_CLIENT_ID` | sim | ID do cliente OAuth do Google |
| `BREVO_API_KEY` | sim | Chave de API do Brevo (começa com `xkeysib-`) |
| `EMAIL_REMETENTE` | sim | E-mail remetente, **já validado no Brevo** |
| `NOME_REMETENTE` | não | Nome que aparece ao lado do remetente. Padrão: `Informa-Saúde` |
| `CORS_ORIGINS` | não | Endereços do front-end que podem usar a API, separados por vírgula e sem barra no final. Padrão: localhost nas portas 5173 e 3000 |
| `AMBIENTE` | não | `desenvolvimento` (padrão) ou `producao`. Em produção o `/docs` fica escondido |

Exemplo de `.env`:

```
AMBIENTE=desenvolvimento

DB_USER=postgres
DB_PASSWORD=sua_senha
DB_NAME=nome_do_seu_banco
DB_HOST=localhost
DB_PORT=5432

SECRET_KEY=gere_uma_chave_com_pelo_menos_32_caracteres
JWT_EXPIRATION_MINUTES=60

GOOGLE_CLIENT_ID=seu-client-id.apps.googleusercontent.com

BREVO_API_KEY=xkeysib-cole-sua-chave-aqui
EMAIL_REMETENTE=contato@seudominio.com.br
NOME_REMETENTE=Informa-Saúde

CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000
```

Para gerar uma `SECRET_KEY` segura, rode no terminal:

```
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

> Depois de mudar o `.env`, **pare e ligue a API de novo** (`Ctrl+C` e depois `uvicorn api.main:app --reload`). Ela só lê o arquivo quando inicia.

## Banco de dados

**SQL para criar as tabelas**

```sql
CREATE TABLE users (
    id               BIGSERIAL PRIMARY KEY,
    nome             VARCHAR(120) NOT NULL,
    email            VARCHAR(180) NOT NULL UNIQUE,
    senha_hash       VARCHAR(72),
    sexo             VARCHAR(50)  NOT NULL,
    data_nascimento  DATE,
    telefone         VARCHAR(30) UNIQUE,
    provider         VARCHAR(20)  NOT NULL DEFAULT 'LOCAL',
    provider_id      VARCHAR(255),
    avatar_url       TEXT,
    token_version    INTEGER      NOT NULL DEFAULT 0,
    criado_em        TIMESTAMPTZ  DEFAULT now()
);

CREATE UNIQUE INDEX idx_users_email_lower ON users (lower(email));

CREATE TABLE codigos_verificacao (
    id           BIGSERIAL PRIMARY KEY,
    user_id      BIGINT      NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    codigo_hash  VARCHAR(64) NOT NULL,
    finalidade   VARCHAR(30) NOT NULL DEFAULT 'RECUPERAR_SENHA',
    tentativas   SMALLINT    NOT NULL DEFAULT 0,
    usado        BOOLEAN     NOT NULL DEFAULT FALSE,
    expira_em    TIMESTAMPTZ NOT NULL,
    criado_em    TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_codigos_user_finalidade_usado
    ON codigos_verificacao (user_id, finalidade, usado);

CREATE TABLE limites_requisicao (
    id        BIGSERIAL PRIMARY KEY,
    acao      VARCHAR(30)  NOT NULL,
    chave     VARCHAR(200) NOT NULL,
    criado_em TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX idx_limites_acao_chave ON limites_requisicao (acao, chave, criado_em);
CREATE INDEX idx_limites_criado_em  ON limites_requisicao (criado_em);
```

**O que cada tabela guarda**

- `users`: as contas dos usuários (login local ou Google).
- `codigos_verificacao`: os códigos de recuperação de senha (guardados só como hash, então ninguém consegue ler o código original).
- `limites_requisicao`: registro das tentativas, usado para bloquear abusos.

## Endpoints

Endpoint é cada "endereço" da API. Os que precisam de login pedem o token no cabeçalho `Authorization: Bearer SEU_TOKEN`.

| Método | Rota | Precisa de | O que faz |
| --- | --- | --- | --- |
| `POST` | `/register` | nada | Cria uma conta com e-mail e senha |
| `POST` | `/login` | nada | Login com e-mail e senha; devolve o token |
| `POST` | `/auth/google` | nada | Login com Google; cria a conta se não existir |
| `POST` | `/auth/recuperar/pedir` | nada | Envia um código de 6 dígitos por e-mail |
| `POST` | `/auth/recuperar/verificar` | nada | Confere o código e devolve um `reset_token` |
| `POST` | `/auth/recuperar/nova-senha` | `reset_token` | Define a nova senha |
| `GET` | `/me` | Bearer | Dados do usuário logado |
| `POST` | `/me/senha` | Bearer | Troca a senha estando logado |

## Testando a API

O jeito mais fácil é pela documentação interativa, sem escrever código:

1. Com a API ligada, abra http://localhost:8000/docs no navegador.
2. Clique na rota que quer testar (por exemplo, `POST /register`).
3. Clique em **Try it out**, preencha o corpo (**apague os textos de exemplo e coloque valores reais**) e clique em **Execute**.
4. A resposta aparece logo abaixo.

Também dá para testar pelo terminal com `curl`:

**Cadastro**

```
curl -X POST http://localhost:8000/register \
  -H "Content-Type: application/json" \
  -d '{
    "nome": "Maria Silva",
    "email": "maria@exemplo.com",
    "senha": "minhasenha123",
    "sexo": "Feminino",
    "data_nascimento": "1990-05-20",
    "telefone": "51999999999"
  }'
```

**Login**

```
curl -X POST http://localhost:8000/login \
  -H "Content-Type: application/json" \
  -d '{"email": "maria@exemplo.com", "senha": "minhasenha123"}'
```

Resposta:

```
{ "access_token": "eyJhbGciOi...", "token_type": "bearer" }
```

**Dados do usuário logado**

```
curl http://localhost:8000/me -H "Authorization: Bearer SEU_TOKEN"
```

```
{ "id": 1, "nome": "Maria Silva", "email": "maria@exemplo.com", "avatar_url": null }
```

## Recuperação de senha

O fluxo tem 3 passos, nesta ordem:

```
Esqueci a senha → recebo um código por e-mail → digito o código → crio a nova senha
```

1. `POST /auth/recuperar/pedir` com `{"email": "..."}`.
   A API envia por e-mail um código de **6 dígitos**, que vale por **10 minutos**. A resposta é sempre a mesma, exista o e-mail ou não (assim ninguém descobre quem tem conta).
2. `POST /auth/recuperar/verificar` com `{"email": "...", "codigo": "123456"}`.
   Se o código estiver certo, devolve um `reset_token` válido por 15 minutos.
3. `POST /auth/recuperar/nova-senha` com `{"reset_token": "...", "nova_senha": "..."}`.
   O `reset_token` só funciona uma vez.

**Bom saber**

- O e-mail só é enviado se a conta existir **e** se já passou 1 minuto desde o último pedido. Fora disso a API responde "ok" sem enviar nada, de propósito.
- Cada código aceita no máximo 5 tentativas erradas. Depois disso é preciso pedir um novo.

## Segurança

- **Senhas** com hash bcrypt, entre 8 e 72 bytes (acentos e emojis contam mais de 1).
- **Códigos de recuperação** guardados com HMAC, com validade de 10 minutos e no máximo 5 tentativas por código.
- **Sessões invalidadas** quando a senha muda, e `reset_token` de uso único.
- **Sem vazamento de dados:** a recuperação responde igual para e-mails existentes e inexistentes, e o login leva o mesmo tempo nos dois casos.
- **Limite de tentativas** (resposta `429`, com o cabeçalho `Retry-After` dizendo quanto esperar):

| Ação | Limite |
| --- | --- |
| Login com senha errada | 5 por e-mail e 20 por IP, em 15 min |
| Pedir código de recuperação | 5 por e-mail e 10 por IP, em 1 h |
| Cadastro | 10 por IP, em 1 h |
| Código de recuperação errado | 10 por e-mail e 30 por IP, em 1 h |
| Senha atual errada em `/me/senha` | 5 por usuário, em 15 min |

- **CORS** restrito às origens do `CORS_ORIGINS`, com apenas `GET` e `POST`.
- **E-mails** sempre salvos em minúsculas, com índice único.
- **Chaves e senhas** ficam só no `.env` (nunca no código).
- **Logs** sem dados sensíveis (sem tokens, e-mails ou detalhes de conexão).

> Ao testar muitas vezes o "esqueci minha senha" com o mesmo e-mail, você pode bater no limite de 5 pedidos por hora. É o comportamento esperado. Para testar à vontade, aumente temporariamente o número em `PEDIR_POR_EMAIL` no `api/main.py`.

## Conectando o front-end

O front-end (React) conversa com esta API pelo endereço definido em `VITE_API_URL`. Sem essa variável, ele usa `http://127.0.0.1:8000`.

Para o navegador aceitar a conversa, o endereço do front precisa estar no `CORS_ORIGINS`. Por padrão já estão liberados `http://localhost:5173`, `http://127.0.0.1:5173` e `http://localhost:3000`.

## Problemas comuns

| O que aparece | O que significa | Como resolver |
| --- | --- | --- |
| `ModuleNotFoundError: No module named 'httpx'` (ou outra biblioteca) | A biblioteca não está instalada **neste** Python, geralmente por causa do `(venv)` desativado | Ative o `(venv)` e rode `python -m pip install -r requirements.txt` |
| `Variável de ambiente ausente: ...` | Falta uma linha obrigatória no `.env` | Adicione a variável citada na mensagem e reinicie a API |
| `SECRET_KEY muito curta` | A chave tem menos de 32 caracteres | Gere outra com o comando da seção [Variáveis de ambiente](#variáveis-de-ambiente) |
| `OperationalError` ou `connection refused` | O PostgreSQL está desligado, ou os dados do banco no `.env` estão errados | Ligue o serviço do PostgreSQL e confira `DB_*` |
| O e-mail com o código não chega | O Brevo recusou ou o e-mail foi parar no spam | Veja o terminal da API (erros aparecem como `Erro Brevo (...)`), confira o painel do Brevo em **Transactional → Logs** e olhe a caixa de spam |
| `Erro Brevo (401)` | Chave de API errada | Gere uma nova chave e atualize o `BREVO_API_KEY` |
| `Erro Brevo (400)` citando o remetente (*sender*) | O `EMAIL_REMETENTE` não está validado no Brevo | Valide o remetente (veja [Configurando o envio de e-mail](#configurando-o-envio-de-e-mail-brevo)) |
| `Erro Brevo` falando de IP não autorizado | O Brevo está bloqueando o seu IP | No Brevo, em *Security → Authorized IPs*, desative o bloqueio ou adicione o seu IP |
| `422 Unprocessable Content` | Os dados enviados não passaram na validação | Veja a resposta: o campo `detail` mostra qual campo está errado (e-mail inválido, campo faltando, senha curta...) |
| `429 Too Many Requests` | Muitas tentativas em pouco tempo | Espere o tempo indicado em `Retry-After` |
| "Pedi o código, a API respondeu ok, mas não veio e-mail" | O e-mail não está cadastrado, ou faltou 1 minuto desde o último pedido | Use um e-mail com conta criada e espere 1 minuto entre pedidos |
| Erro de **CORS** no navegador | O endereço do front não está liberado | Adicione o endereço ao `CORS_ORIGINS` e reinicie a API |
| `ImportError: cannot import name ...` ao ligar | O `config.py` não está igual ao esperado pelo `main.py` | Confira se o `config.py` tem todas as variáveis (como `CORS_ORIGINS` e `EM_PRODUCAO`) |

## Produção

- Use **HTTPS**.
- Defina `AMBIENTE=producao` e `CORS_ORIGINS` com o domínio real do front.
- Atrás de proxy (Nginx, Render, Railway etc.), rode o servidor com `--proxy-headers --forwarded-allow-ips="IP_DO_PROXY"` para o limite por IP enxergar o IP real:

```
uvicorn api.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips="IP_DO_PROXY"
```

- Use um remetente de **domínio próprio** e autentique o domínio (SPF/DKIM) no Brevo, para os e-mails chegarem na caixa de entrada.
- Conecte ao banco com um usuário de poucas permissões (apenas `SELECT`, `INSERT`, `UPDATE` e `DELETE`), e não com o superusuário.
- **Nunca suba o `.env` para o Git.** Se isso já aconteceu, troque a `SECRET_KEY`, a senha do banco e a chave do Brevo (apague a antiga no painel do Brevo e gere outra).
- Faça backups do banco (`pg_dump`) e mantenha as dependências atualizadas (`pip-audit`).