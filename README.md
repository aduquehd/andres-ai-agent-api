<div align="center">

# 🤖 AndresAI — API (Backend)

<a href="https://andres-ai.aduquehd.com/">
  <img src="https://img.shields.io/badge/🔗%20Live%20Demo-Visit%20Site-blue?style=for-the-badge" alt="Live Demo">
</a>

[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Pydantic AI](https://img.shields.io/badge/Pydantic%20AI-E92063?style=for-the-badge&logo=pydantic&logoColor=white)](https://ai.pydantic.dev/)
[![Anthropic](https://img.shields.io/badge/Claude-D97757?style=for-the-badge&logo=anthropic&logoColor=white)](https://www.anthropic.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-DC382D?style=for-the-badge&logo=redis&logoColor=white)](https://redis.io/)
[![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)

**FastAPI backend for the AndresAI chat assistant — streaming chat, RAG over pgvector, real-time admin events, and a JSON admin API.**

[Companion repo](#-companion-repo) • [Features](#-features) • [Screenshots](#-screenshots) • [Quick Start](#-quick-start) • [Authentication](#-authentication) • [API](#-api-endpoints) • [Deployment](#-deployment) • [Contributing](#-contributing)

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
- 🧠 **Model-agnostic agent** — [Pydantic AI](https://ai.pydantic.dev/) with typed tool calls; defaults to Anthropic Claude, swappable via `AGENT_MODEL`
- 🔍 **Semantic search (RAG)** — vector embeddings with pgvector, auto re-embedded on save
- 📊 **Admin JSON API** — dashboard stats, conversations, users, messages, knowledge base, agent contexts
- 📡 **Real-time admin events** — WebSocket stream pushes live updates to the admin UI

</td>
<td>

### 🛡️ Production
- 🔒 **JWT admin auth** — httpOnly cookie, `SameSite=None; Secure` for cross-origin; WebSocket handshake reuses the same cookie
- 🐳 **Dockerized** — local + prod compose files, Caddy in front
- ⚡ **Rate limiting** — Redis-backed, per-IP, with CloudFlare/proxy support
- 🌍 **Geo enrichment** — visitor geolocation via ipquery.io, cached
- 📈 **Observability** — Logfire + optional Sentry

</td>
</tr>
</table>

## 📸 Screenshots

The [Next.js frontend](https://github.com/aduquehd/andres-ai-agent-app) consuming this API:

### Chat

The cyberpunk-themed chat UI streaming an answer about open source projects:

![Chat UI](docs/screenshots/chat.png)

### Admin — Dashboard

Live usage stats, latency percentiles, throughput charts, and geography:

![Admin dashboard](docs/screenshots/admin-dashboard.png)

### Admin — Conversations

One row per user with message counts, last activity, and a preview of the last message:

![Admin conversations](docs/screenshots/admin-conversations.png)

### Admin — Conversation detail

Clicking a row opens the full thread with per-user metadata (latency, client, IP, geo):

![Admin conversation detail](docs/screenshots/admin-conversation-detail.png)

## 📋 Prerequisites

- Docker & Docker Compose
- An **Anthropic API key** (the default agent model is Claude) — or set `AGENT_MODEL` to any [Pydantic AI-supported model](https://ai.pydantic.dev/models/) and provide that provider's key
- An **OpenAI API key** — used for embeddings (`text-embedding-3-small`) that power the RAG knowledge base
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
#   ANTHROPIC_API_KEY (agent), OPENAI_API_KEY (embeddings),
#   POSTGRES_PASSWORD, ADMIN_PASSWORD,
#   FASTAPI_ADMIN_SECRET_KEY (32+ chars), FRONTEND_ORIGINS
```

<details>
<summary>📝 <b>Environment variables</b> (click to expand)</summary>

```dotenv
# 🔑 LLM providers
# The agent runs on Claude by default (see AGENT_MODEL below).
ANTHROPIC_API_KEY=sk-ant-your-anthropic-api-key-here
# OpenAI is required for RAG embeddings (text-embedding-3-small).
OPENAI_API_KEY=sk-proj-your-openai-api-key-here
# Optional — only if you switch AGENT_MODEL to a Gemini model.
# GOOGLE_API_KEY=your-google-api-key-here

# 🧠 Agent / RAG (optional overrides — defaults shown)
# Any Pydantic AI model string works, e.g. openai:gpt-5, google:gemini-2.5-pro
# AGENT_MODEL is the fallback: a model config saved in the admin (/admin/model-config) wins.
# AGENT_MODEL=anthropic:claude-sonnet-4-6
# EMBEDDING_MODEL=text-embedding-3-small

# 🗄️ Database
DB_CONNECTION_STRING=postgresql+asyncpg://chat_user:your_secure_password@db/chat_agent_db
POSTGRES_USER=chat_user
POSTGRES_PASSWORD=your_secure_password
POSTGRES_DB=chat_agent_db

# 🚦 Redis (rate limiting + realtime)
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

# 📈 Optional — observability & analytics
LOGFIRE_TOKEN=pylf_v1_us_your-logfire-token-here
SENTRY_DSN=https://your-project-id@o0.ingest.sentry.io/0
GA_TRACKING_ID=G-YOUR-TRACKING-ID-HERE
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

## 🔐 Authentication

Two independent mechanisms, one per audience:

### Chat users (anonymous, UUID-based)

Chat visitors are identified by client-generated UUIDs — no signup. The frontend stores them in `localStorage` and sends them on every request:

```
Authorization: User-Id <uuid>
X-Browser-Id: <uuid>
```

Unknown UUIDs are auto-registered on first message; geo data is derived from the client IP (CloudFlare/proxy-aware) and backfilled asynchronously.

### Admin (JWT in an httpOnly cookie)

1. `POST /api/admin/login` with username/password (constant-time comparison against `ADMIN_USER`/`ADMIN_PASSWORD`).
2. The API sets an `admin_session` httpOnly cookie containing an HS256 JWT (12 h TTL), signed with `FASTAPI_ADMIN_SECRET_KEY`.
3. The cookie uses `SameSite=None; Secure` so it survives the cross-origin flow from the Vercel-hosted admin UI.
4. All `/api/admin/*` endpoints require the cookie; the **WebSocket** at `/api/admin/ws` authenticates the same way — the browser sends the cookie on the handshake, and unauthenticated connections are closed with code `4401`.

CORS is restricted to the origins in `FRONTEND_ORIGINS`, with credentials allowed.

## 🌐 API Endpoints

### Chat API (consumed by the Next.js chat at `/`)

| Method | Path                 | Description                                      | Rate limit  |
|--------|----------------------|--------------------------------------------------|-------------|
| `GET`  | `/api/chats/history` | Chat history for the authenticated UUID user     | 100/min/IP  |
| `POST` | `/api/chats/send`    | Send a message (form field `prompt`); streams newline-delimited JSON | 30/min/IP   |

### Admin API (consumed by the Next.js admin at `/admin`)

**Session**

| Method | Path                | Description                                   |
|--------|---------------------|-----------------------------------------------|
| `POST` | `/api/admin/login`  | Username/password → sets httpOnly JWT cookie  |
| `POST` | `/api/admin/logout` | Clears the JWT cookie                         |
| `GET`  | `/api/admin/me`     | Returns current admin session info            |
| `WS`   | `/api/admin/ws`     | Real-time event stream (auth via JWT cookie)  |

**Data**

| Method                  | Path                                | Description                                    |
|-------------------------|-------------------------------------|------------------------------------------------|
| `GET`                   | `/api/admin/dashboard/stats`        | Dashboard metrics; `messages_range` = `this_month`, `30d`, `60d`, `90d`, `all` |
| `GET`                   | `/api/admin/users`                  | List users                                     |
| `GET`                   | `/api/admin/users/{id}`             | User detail                                    |
| `GET`                   | `/api/admin/users/{id}/stats`       | Per-user stats                                 |
| `DELETE`                | `/api/admin/users/{id}`             | Delete user (cascades to their messages)       |
| `GET`                   | `/api/admin/conversations`          | Conversation list grouped per user             |
| `GET`                   | `/api/admin/messages`               | List messages                                  |
| `GET`                   | `/api/admin/messages/countries`     | Message counts by country                      |
| `GET`/`DELETE`          | `/api/admin/messages/{id}`          |                                                |
| `GET`                   | `/api/admin/agent-messages`         | Pydantic AI message lists per user             |
| `GET`/`DELETE`          | `/api/admin/agent-messages/{id}`    |                                                |
| `GET/POST/PATCH/DELETE` | `/api/admin/knowledge-base`         | RAG entries — regenerates the embedding on save |
| `GET/POST/PATCH/DELETE` | `/api/admin/agent-contexts`         | Agent system-prompt context entries            |
| `GET`/`PATCH`/`DELETE`  | `/api/admin/model-config`           | Agent model and request settings; `PATCH` saves only after a test turn passes, `DELETE` falls back to `AGENT_MODEL` |
| `POST`                  | `/api/admin/model-config/test`      | One real agent turn with a candidate config, not saved |

## 🚦 Rate limiting

Redis-backed, per-IP, with CloudFlare/proxy `X-Forwarded-For` support. Limits reset automatically; clients get **HTTP 429** with a `Retry-After` header. No extra config needed — uses the Redis settings from `.env`.

## 🏗️ Architecture

```
modules/
├── admin/            JSON CRUD routes + WebSocket event broadcaster (realtime.py)
├── agent/            Pydantic AI agent, tools, models
├── chats/            Chat endpoints + streaming
├── knowledge_base/   RAG over pgvector (auto-embed on save)
├── users/            User accounts
└── utils/            Shared: auth, database, embeddings, geo, rate limiting, redis
```

Key models live in `modules/*/models.py`: `User`, `AgentMessage`, `Message`, `KnowledgeBase`, `AgentContext`, `AgentModelConfig`.

The agent (`modules/agent/agent.py`) is a Pydantic AI `Agent` with a dynamic system prompt loaded from the `AgentContext` table and a `search_knowledge_base` tool that does semantic search over the pgvector-indexed knowledge base.

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

The knowledge base powers the agent's RAG context. Manage it from the admin panel at `/admin/knowledge-base` (frontend). The agent's static persona/system prompt lives in the `AgentContext` table, editable at `/admin/agent-contexts`.

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

Deployment is automated. Every push to `main` triggers
[`.github/workflows/deploy.yml`](.github/workflows/deploy.yml), which:

1. runs `ruff check`, `ruff format --check` and `pytest`;
2. builds `compose/prod/Dockerfile` and pushes it to ECR tagged `sha-<commit>`;
3. runs `scripts/deploy.sh` on the EC2 host via AWS SSM, which pulls that exact
   image, applies Alembic migrations, and restarts the stack.

The server holds no AWS keys and GitHub holds no SSH keys: both sides
authenticate with short-lived credentials (GitHub OIDC into an IAM role, and an
EC2 instance profile respectively).

### First-time server setup

```bash
# Enable pgvector (one-time)
docker exec -it andres-ai-agent_db psql -U chat_user -d chat_agent_db \
  -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

The host also needs the AWS CLI, an instance profile granting
`AmazonSSMManagedInstanceCore` + `AmazonEC2ContainerRegistryReadOnly`, and a
production `.env` in `/home/ubuntu/AndresAI-Agent/` (never baked into the image).

### Rolling back

```bash
gh workflow run "Deploy production" -f image_tag=sha-1a2b3c4
```

This redeploys that image *and* checks the config out at the same commit.

### Connecting to the production database

Postgres is bound to `127.0.0.1` on the host, so open a tunnel rather than
exposing the port. This needs the Session Manager plugin locally
(`brew install --cask session-manager-plugin`):

```bash
aws ssm start-session --target <instance-id> \
  --document-name AWS-StartPortForwardingSessionToRemoteHost \
  --parameters '{"host":["localhost"],"portNumber":["5432"],"localPortNumber":["15432"]}'
```

Then connect a client to `localhost:15432`.

## 🤝 Contributing

Contributions are welcome! To get started:

1. **Fork** the repository and create a feature branch (`git checkout -b feat/my-feature`).
2. Follow the [Quick Start](#-quick-start) to get a local stack running.
3. Make your changes. Before committing, format and lint:
   ```bash
   docker compose run --rm backend uv run ruff format .
   docker compose run --rm backend uv run ruff check . --fix
   ```
4. If you change models, generate a migration (`alembic revision --autogenerate`) and include it.
5. **Open a pull request** describing what changed and why.

For bugs and feature ideas, please [open an issue](https://github.com/aduquehd/AndresAI-Agent/issues).

## 📄 License

This project is licensed under the [MIT License](LICENSE).

---

<div align="center">

**Built with ❤️ using FastAPI, Pydantic AI, and pgvector**

[![License](https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square)](LICENSE)

</div>
