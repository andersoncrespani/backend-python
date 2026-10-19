# Informa-Saúde — Backend

API REST em **FastAPI** para autenticação e gerenciamento de contas de usuários do Informa-Saúde. Cuida de cadastro, login (e-mail e senha ou Google), recuperação de senha por código enviado por e-mail e troca de senha, com proteções contra abuso.

## Funcionalidades

- Cadastro e login com e-mail e senha (hash com bcrypt)
- Login com Google (validação do `id_token`)
- Recuperação de senha em 3 passos, com código de 6 dígitos enviado por e-mail
- Autenticação por JWT, com sessões invalidadas quando a senha muda
- Perfil do usuário (`/me`) e troca de senha
- Limite de tentativas em login, cadastro e códigos de recuperação
- Documentação interativa automática em `/docs` (desativada em produção)

## Tecnologias

- Python 3.10+
- FastAPI e Uvicorn
- PostgreSQL com SQLAlchemy (psycopg2)
- PyJWT e Passlib (bcrypt)
- google-auth
- Pydantic v2 (com `email-validator`)
- python-dotenv

## Estrutura

```
backend-python/
├── api/
│   ├── main.py        # rotas e regras da API
│   ├── config.py      # variáveis de ambiente
│   ├── database.py    # conexão com o PostgreSQL
│   ├── models.py      # tabelas (SQLAlchemy)
│   ├── schemas.py     # validação de entrada e saída (Pydantic)
│   ├── security.py    # senhas, JWT e códigos de verificação
│   ├── limites.py     # limite de tentativas por e-mail, IP e usuário
│   └── email.py       # envio de e-mail (SMTP do Gmail)
└── .env               # configurações locais (não vai para o Git)
```

## Como rodar

### 1. Clonar e instalar

```bash
git clone https://github.com/andersoncrespani/backend-python.git
cd backend-python

python -m venv .venv
source .venv/bin/activate        # no Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

Se o projeto ainda não tiver `requirements.txt`, as bibliotecas principais são:

```bash
pip install fastapi "uvicorn[standard]" sqlalchemy psycopg2-binary python-dotenv \
            pyjwt "passlib[bcrypt]" google-auth requests email-validator
```

### 2. Criar o banco

Crie um banco no PostgreSQL e as tabelas (veja [Banco de dados](#banco-de-dados)).

### 3. Configurar o `.env`

Crie um arquivo `.env` na raiz do projeto (veja [Variáveis de ambiente](#variáveis-de-ambiente)).

### 4. Subir a API

```bash
uvicorn api.main:app --reload
```

A API fica em `http://localhost:8000` e a documentação em `http://localhost:8000/docs`.

## Variáveis de ambiente

| Variável | Obrigatória | Descrição |
|---|---|---|
| `DB_USER` | sim | Usuário do PostgreSQL |
| `DB_PASSWORD` | sim | Senha do PostgreSQL |
| `DB_NAME` | sim | Nome do banco |
| `DB_HOST` | não | Padrão: `localhost` |
| `DB_PORT` | não | Padrão: `5432` |
| `SECRET_KEY` | sim | Chave dos JWTs e dos códigos. **Mínimo de 32 caracteres** |
| `JWT_ALGORITHM` | não | Padrão: `HS256` |
| `JWT_EXPIRATION_MINUTES` | não | Validade do token de acesso. Padrão: `60` |
| `GOOGLE_CLIENT_ID` | sim | ID do cliente OAuth do Google |
| `EMAIL_REMETENTE` | sim | Conta do Gmail que envia os códigos |
| `EMAIL_SENHA` | sim | Senha de app do Gmail |
| `CORS_ORIGINS` | não | Origens liberadas, separadas por vírgula e sem barra no final. Padrão: localhost (portas 5173 e 3000) |
| `AMBIENTE` | não | `desenvolvimento` (padrão) ou `producao`. Em produção o `/docs` fica escondido |

Exemplo:

```env
AMBIENTE=desenvolvimento

DB_USER=postgres
DB_PASSWORD=sua_senha
DB_NAME=nome_do_seu_banco
DB_HOST=localhost
DB_PORT=5432

SECRET_KEY=gere_uma_chave_com_pelo_menos_32_caracteres
JWT_EXPIRATION_MINUTES=60

GOOGLE_CLIENT_ID=seu-client-id.apps.googleusercontent.com

EMAIL_REMETENTE=seuemail@gmail.com
EMAIL_SENHA=senha_de_app_do_gmail

CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000
```

Para gerar uma `SECRET_KEY`:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

## Banco de dados

<details>
<summary>SQL para criar as tabelas</summary>

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

</details>

## Tabelas

### `users`

Contas de usuário, tanto de login local quanto do Google.

| Coluna | Tipo | Obrigatória | Descrição |
|---|---|---|---|
| `id` | BIGSERIAL | sim | Chave primária |
| `nome` | VARCHAR(120) | sim | Nome completo |
| `email` | VARCHAR(180) | sim | Único, sempre em minúsculas |
| `senha_hash` | VARCHAR(72) | não | Hash bcrypt (vazio em contas Google) |
| `sexo` | VARCHAR(50) | sim | Sexo informado |
| `data_nascimento` | DATE | não | Data de nascimento |
| `telefone` | VARCHAR(30) | não | Único |
| `provider` | VARCHAR(20) | sim | `LOCAL` ou `GOOGLE` |
| `provider_id` | VARCHAR(255) | não | ID da conta no Google |
| `avatar_url` | TEXT | não | Foto de perfil |
| `token_version` | INTEGER | sim | Sobe a cada troca de senha e invalida os JWTs antigos |
| `criado_em` | TIMESTAMPTZ | não | Data de criação |

Exemplo de linhas:

| id | nome | email | senha_hash | sexo | data_nascimento | telefone | provider | provider_id | avatar_url | token_version |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Maria Silva | maria@exemplo.com | `$2b$12$k3...` | Feminino | 1990-05-20 | 51999999999 | LOCAL | null | null | 0 |
| 2 | João Souza | joao@gmail.com | null | Masculino | null | null | GOOGLE | 1087654321... | https://lh3.googleusercontent.com/... | 0 |

### `codigos_verificacao`

Códigos de recuperação de senha. O código em si nunca é salvo, só o hash.

| Coluna | Tipo | Obrigatória | Descrição |
|---|---|---|---|
| `id` | BIGSERIAL | sim | Chave primária |
| `user_id` | BIGINT | sim | Dono do código (`users.id`, apaga junto com o usuário) |
| `codigo_hash` | VARCHAR(64) | sim | HMAC do código de 6 dígitos |
| `finalidade` | VARCHAR(30) | sim | Padrão: `RECUPERAR_SENHA` |
| `tentativas` | SMALLINT | sim | Erros de digitação (máximo de 5) |
| `usado` | BOOLEAN | sim | `true` depois de usado |
| `expira_em` | TIMESTAMPTZ | sim | Validade de 10 minutos |
| `criado_em` | TIMESTAMPTZ | não | Data de criação |

Exemplo de linhas:

| id | user_id | codigo_hash | finalidade | tentativas | usado | expira_em |
|---|---|---|---|---|---|---|
| 1 | 1 | `9f2c1a...` | RECUPERAR_SENHA | 0 | true | 2026-10-19 14:10:00-03 |
| 2 | 1 | `b71e0d...` | RECUPERAR_SENHA | 2 | false | 2026-10-19 15:40:00-03 |

### `limites_requisicao`

Registro de tentativas, usado para bloquear abusos (veja [Segurança](#segurança)). Cada linha é uma tentativa.

| Coluna | Tipo | Obrigatória | Descrição |
|---|---|---|---|
| `id` | BIGSERIAL | sim | Chave primária |
| `acao` | VARCHAR(30) | sim | Tipo da tentativa (login, cadastro, recuperação...) |
| `chave` | VARCHAR(200) | sim | E-mail, IP ou usuário que fez a tentativa |
| `criado_em` | TIMESTAMPTZ | sim | Momento da tentativa |

Exemplo de linhas:

| id | acao | chave | criado_em |
|---|---|---|---|
| 1 | login | email:maria@exemplo.com | 2026-10-19 14:01:10-03 |
| 2 | login | ip:203.0.113.7 | 2026-10-19 14:01:10-03 |

### Consultas úteis

```sql
-- Ver os usuários cadastrados
SELECT id, nome, email, provider, criado_em FROM users ORDER BY id;

-- Ver códigos de recuperação ainda válidos
SELECT user_id, tentativas, expira_em
FROM codigos_verificacao
WHERE usado = FALSE AND expira_em > now();

-- Limpar tentativas antigas (mais de 1 dia)
DELETE FROM limites_requisicao WHERE criado_em < now() - interval '1 day';
```

## Endpoints

| Método | Rota | Autenticação | Descrição |
|---|---|---|---|
| `POST` | `/register` | não | Cria uma conta com e-mail e senha |
| `POST` | `/login` | não | Login com e-mail e senha; devolve o token |
| `POST` | `/auth/google` | não | Login com Google; cria a conta se não existir |
| `POST` | `/auth/recuperar/pedir` | não | Envia um código de 6 dígitos por e-mail |
| `POST` | `/auth/recuperar/verificar` | não | Confere o código e devolve um `reset_token` |
| `POST` | `/auth/recuperar/nova-senha` | `reset_token` | Define a nova senha |
| `GET` | `/me` | Bearer | Dados do usuário logado |
| `POST` | `/me/senha` | Bearer | Troca a senha estando logado |

### Exemplos

**Cadastro**

```bash
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

```bash
curl -X POST http://localhost:8000/login \
  -H "Content-Type: application/json" \
  -d '{"email": "maria@exemplo.com", "senha": "minhasenha123"}'
```

Resposta:

```json
{ "access_token": "eyJhbGciOi...", "token_type": "bearer" }
```

**Dados do usuário logado**

```bash
curl http://localhost:8000/me -H "Authorization: Bearer SEU_TOKEN"
```

```json
{ "id": 1, "nome": "Maria Silva", "email": "maria@exemplo.com", "avatar_url": null }
```

### Recuperação de senha

1. `POST /auth/recuperar/pedir` com `{"email": "..."}`. A resposta é sempre a mesma, exista o e-mail ou não.
2. `POST /auth/recuperar/verificar` com `{"email": "...", "codigo": "123456"}`. Devolve um `reset_token` válido por 15 minutos.
3. `POST /auth/recuperar/nova-senha` com `{"reset_token": "...", "nova_senha": "..."}`. O `reset_token` só funciona uma vez.

## Segurança

- **Senhas** com hash bcrypt, entre 8 e 72 bytes (acentos e emojis contam mais de 1).
- **Códigos de recuperação** guardados com HMAC, com validade de 10 minutos e no máximo 5 tentativas por código.
- **Sessões invalidadas** quando a senha muda, e `reset_token` de uso único.
- **Limite de tentativas** (resposta `429` com o cabeçalho `Retry-After`):

| Ação | Limite |
|---|---|
| Login com senha errada | 5 por e-mail e 20 por IP, em 15 min |
| Pedir código de recuperação | 5 por e-mail e 10 por IP, em 1 h |
| Cadastro | 10 por IP, em 1 h |
| Código de recuperação errado | 10 por e-mail e 30 por IP, em 1 h |
| Senha atual errada em `/me/senha` | 5 por usuário, em 15 min |

- **CORS** restrito às origens do `CORS_ORIGINS`, com apenas `GET` e `POST`.
- **E-mails** sempre salvos em minúsculas, com índice único.
- **Logs** sem dados sensíveis (sem tokens, e-mails ou detalhes de conexão).

## Produção

- Use **HTTPS**.
- Defina `AMBIENTE=producao` e `CORS_ORIGINS` com o domínio real do front.
- Atrás de proxy (Nginx, Render, Railway etc.), rode o servidor com `--proxy-headers --forwarded-allow-ips="IP_DO_PROXY"` para o limite por IP enxergar o IP real:

  ```bash
  uvicorn api.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips="IP_DO_PROXY"
  ```

- Conecte ao banco com um usuário de poucas permissões (apenas `SELECT`, `INSERT`, `UPDATE` e `DELETE`), e não com o superusuário.
- Nunca suba o `.env` para o Git. Se isso já aconteceu, troque `SECRET_KEY`, a senha do banco e a senha de app do Gmail.
- Faça backups do banco (`pg_dump`) e mantenha as dependências atualizadas (`pip-audit`).