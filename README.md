<div align="center">

# 🤖 AndresAI — API (Backend)

<a href="https://andres-ai.aduquehd.com/">
  <img src="https://img.shields.io/badge/🔗%20Live%20Demo-Visit%20Site-blue?style=for-the-badge" alt="Live Demo">
</a>

[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-DC382D?style=for-the-badge&logo=redis&logoColor=white)](https://redis.io/)
[![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)
[![OpenAI](https://img.shields.io/badge/OpenAI-412991?style=for-the-badge&logo=openai&logoColor=white)](https://openai.com/)

**FastAPI backend for the AndresAI chat assistant — streaming chat, RAG over pgvector, and a JSON admin API.**

[Companion repo](#-companion-repo) • [Features](#-features) • [Quick Start](#-quick-start) • [API](#-api-endpoints) • [Deployment](#-deployment)

</div>

---

## 🔗 Companion repo

This is the **backend** half of AndresAI. It used to be a monorepo, but the frontend now lives in its own repository:

- **Backend (this repo)** — [`AndresAI-Agent`](https://github.com/aduquehd/AndresAI-Agent): FastAPI, PostgreSQL/pgvector, Redis. Deployed via Docker on a server.
- **Frontend** — [`andres-ai-agent-app`](https://github.com/aduquehd/andres-ai-agent-app): Next.js 16 app that serves the chat at `/` and the admin at `/admin`. Deployed on Vercel.

The two communicate over HTTPS. The frontend points at this API via `NEXT_PUBLIC_API_URL`, and this API allows the frontend's origin via `FRONTEND_ORIGINS` (CORS allow-list, with credentials).

## ✨ Features

<table>
<tr>
<td>

### 🚀 Core
- 🤖 **Streaming chat** — newline-delimited JSON over HTTP
- 🔍 **Semantic search** — vector embeddings with pgvector
- 📊 **Admin JSON API** — CRUD over users, messages, knowledge base, agent contexts
- 🧠 **Pydantic AI** — typed agent + tool calls

</td>
<td>

### 🛡️ Production
- 🔒 **JWT admin auth** — httpOnly cookie, `SameSite=None; Secure` for cross-origin
- 🐳 **Dockerized** — local + prod compose files, Caddy in front
- ⚡ **Rate limiting** — Redis-backed, per-IP, with CloudFlare/proxy support
- 📈 **Observability** — Logfire + optional Sentry

</td>
</tr>
</table>

## 📋 Prerequisites

- Docker & Docker Compose
- An OpenAI API key
- (For the full chat experience) the [frontend repo](https://github.com/aduquehd/andres-ai-agent-app) running and pointed at this API

## 🚀 Quick Start

### 1️⃣ Clone

```bash
git clone git@github.com:aduquehd/AndresAI-Agent.git
cd AndresAI-Agent
```

### 2️⃣ Configure

```bash
cp .env.example .env
# Edit .env — at minimum set:
#   OPENAI_API_KEY, POSTGRES_PASSWORD, ADMIN_PASSWORD,
#   FASTAPI_ADMIN_SECRET_KEY (32+ chars), FRONTEND_ORIGINS
```

<details>
<summary>📝 <b>Environment variables</b> (click to expand)</summary>

```dotenv
# 🔑 OpenAI API
OPENAI_API_KEY=sk-proj-your-openai-api-key-here

# 📊 Logfire (optional - observability)
LOGFIRE_TOKEN=pylf_v1_us_your-logfire-token-here

# 🗄️ Database
DB_CONNECTION_STRING=postgresql+asyncpg://chat_user:your_secure_password@db/chat_agent_db
POSTGRES_USER=chat_user
POSTGRES_PASSWORD=your_secure_password
POSTGRES_DB=chat_agent_db

# 🚦 Redis (rate limiting)
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
# REDIS_PASSWORD=your_redis_password_if_needed

# 👤 Admin auth (JWT cookie for the Next.js admin UI)
ADMIN_USER=admin
ADMIN_PASSWORD='your_secure_admin_password'
FASTAPI_ADMIN_SECRET_KEY='your_secret_key_here_32_chars_min'

# 🌐 CORS — comma-separated origins the frontend will hit this API from
FRONTEND_ORIGINS=http://localhost:3000,https://your-vercel-domain.vercel.app

# ⚙️ App
APP_ENV=development
DEBUG=false

# 📈 Optional
GA_TRACKING_ID=G-YOUR-TRACKING-ID-HERE
SENTRY_DSN=https://your-project-id@o0.ingest.sentry.io/0
```

</details>

### 3️⃣ Build and start

```bash
docker compose build
docker compose up
```

### 4️⃣ Enable the pgvector extension (one-time, after first start)

```bash
docker exec -it andres-ai-agent_db psql -U chat_user -d chat_agent_db -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### 5️⃣ Apply migrations

```bash
docker compose run --rm backend uv run alembic upgrade head
```

### 6️⃣ Run the frontend (separate repo)

```bash
# In another terminal, outside this repo
git clone git@github.com:aduquehd/andres-ai-agent-app.git
cd andres-ai-agent-app
cp .env.local.example .env.local   # NEXT_PUBLIC_API_URL=http://localhost:8000
pnpm install
pnpm dev
```

The API is now at <http://localhost:8000>, the chat at <http://localhost:3000/>, and the admin at <http://localhost:3000/admin>.

## 🌐 API Endpoints

### Chat API (consumed by the Next.js chat at `/`)

| Method | Path                 | Description                                      | Rate limit  |
|--------|----------------------|--------------------------------------------------|-------------|
| `GET`  | `/api/chats/history` | Chat history for the authenticated UUID user     | 100/min/IP  |
| `POST` | `/api/chats/send`    | Send a message; streams newline-delimited JSON   | 30/min/IP   |

Auth headers (CORS allows credentials):
- `Authorization: User-Id <uuid>`
- `X-Browser-Id: <uuid>`

### Admin API (consumed by the Next.js admin at `/admin`)

| Method                  | Path                          | Description                                 |
|-------------------------|-------------------------------|---------------------------------------------|
| `POST`                  | `/api/admin/login`            | Username/password → sets httpOnly JWT cookie |
| `POST`                  | `/api/admin/logout`           | Clears the JWT cookie                        |
| `GET`                   | `/api/admin/me`               | Returns current admin session info           |
| `GET/POST/PATCH/DELETE` | `/api/admin/users`            |                                              |
| `GET/POST/PATCH/DELETE` | `/api/admin/messages`         |                                              |
| `GET/POST/PATCH/DELETE` | `/api/admin/agent-messages`   |                                              |
| `GET/POST/PATCH/DELETE` | `/api/admin/knowledge-base`   | Regenerates the embedding on save            |
| `GET/POST/PATCH/DELETE` | `/api/admin/agent-contexts`   |                                              |

The admin cookie is set with `SameSite=None; Secure` so it survives the cross-origin admin flow from Vercel.

## 🚦 Rate limiting

Redis-backed, per-IP, with CloudFlare/proxy `X-Forwarded-For` support. Limits reset automatically; clients get **HTTP 429** with a `Retry-After` header. No extra config needed — uses the Redis settings from `.env`.

## 🏗️ Architecture

```
modules/
├── admin/            JSON CRUD routes consumed by the Next.js admin UI
├── agent/            Pydantic AI agent, tools, models
├── chats/            Chat endpoints + streaming
├── knowledge_base/   RAG over pgvector (auto-embed on save)
├── users/            User accounts
└── utils/            Shared: auth, database, agent, rate limiting
```

Key models live in `modules/*/models.py`: `User`, `AgentMessage`, `Message`, `KnowledgeBase`, `AgentContext`.

## 💻 Development

### 🐍 Lint & format (Ruff)

```bash
# format
docker compose run --rm backend uv run ruff format .
# lint
docker compose run --rm backend uv run ruff check .
# autofix
docker compose run --rm backend uv run ruff check . --fix
```

### 🗄️ Local DB

```yaml
Connection String: jdbc:postgresql://localhost:15432/chat_agent_db
Username: chat_user
Password: (from your .env)
```

### 🧰 Migrations

```bash
# apply
docker compose run --rm backend uv run alembic upgrade head
# new revision (autogenerate)
docker compose run --rm backend uv run alembic revision --autogenerate -m "description"
```

### 📊 Populate geographic data for existing users

```bash
docker compose run --rm backend uv run python -m scripts.populate_user_geo_data
```

## 🎯 Configuring the agent

The knowledge base powers the agent's RAG context. Manage it from the admin panel at `/admin/knowledge-base` (frontend).

<details>
<summary>📚 <b>Knowledge base example</b> (click to expand)</summary>

```json
[
  {
    "type": "hobbies",
    "title": "Racing bikes",
    "content": "I've been racing bikes for 3 years, and I love the adrenaline rush."
  },
  {
    "type": "hobbies",
    "title": "Playing guitar",
    "content": "Started playing guitar last year, it helps me relax after work."
  }
]
```

</details>

# 🚢 Deployment

The backend deploys to your own server via Docker. The frontend deploys to Vercel — see the [frontend repo](https://github.com/aduquehd/andres-ai-agent-app#-deployment) for those instructions.

## Backend — Docker on your own server

> 💡 You may need `sudo` for docker commands depending on your setup.

### Prerequisites

- ✅ Docker installed on the server
- ✅ Your domain configured in `compose/prod/Caddyfile`
- ✅ A production `.env` file (use `APP_ENV=production`)
- ✅ The frontend's deployed origin listed in `FRONTEND_ORIGINS` (comma-separated)

### Deploy steps

```bash
# 1. Build production images
docker compose -f docker-compose.prod.yml build

# 2. Start the stack
docker compose -f docker-compose.prod.yml up -d

# 3. Enable pgvector (one-time)
docker exec -it andres-ai-agent_db psql -U chat_user -d chat_agent_db \
  -c "CREATE EXTENSION IF NOT EXISTS vector;"

# 4. Apply migrations
docker compose -f docker-compose.prod.yml run --rm backend uv run alembic upgrade head
```

Caddy will serve the API on the domain configured in `compose/prod/Caddyfile`.

### Re-deployment

```bash
source deploy-server.sh
```

### Production with Supervisor (auto-restart)

<details>
<summary>⚡ <b>Supervisor configuration</b> (click to expand)</summary>

```bash
sudo apt install supervisor -y
sudo nano /etc/supervisor/conf.d/ai_agent.conf
```

```ini
[program:ai_agent]
directory=/home/ubuntu/AndresAI-Agent
command=sudo /usr/bin/docker compose -f docker-compose.prod.yml up
autostart=true
autorestart=true
stderr_logfile=/var/log/ai_agent.err.log
stdout_logfile=/var/log/ai_agent.out.log
```

```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start ai_agent
```

Useful:
```bash
sudo tail -f /var/log/ai_agent.out.log
sudo supervisorctl stop ai_agent
docker compose -f docker-compose.prod.yml up
```

</details>

---

<div align="center">

**Built with ❤️ using FastAPI, Pydantic AI, and pgvector**

[![License](https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square)](LICENSE)

</div>
