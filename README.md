<div align="center">

# 🤖 AI Agent Chatbot

<a href="https://andres-ai.aduquehd.com/">
  <img src="https://img.shields.io/badge/🔗%20Live%20Demo-Visit%20Site-blue?style=for-the-badge" alt="Live Demo">
</a>

[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)
[![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=for-the-badge&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![OpenAI](https://img.shields.io/badge/OpenAI-412991?style=for-the-badge&logo=openai&logoColor=white)](https://openai.com/)

**A production-ready AI chatbot system built with modern web technologies**

[Repository layout](#-repository-layout) • [Features](#-features) • [Quick Start](#-quick-start) • [Development](#-development) • [Deployment](#-deployment)

</div>

---

## 🗂 Repository layout

This repo is a monorepo with two independent projects:

```
.
├── andres-ai-api/   FastAPI backend (chat streaming + admin JSON API + Postgres/pgvector + Redis)
└── andres-ai-app/   Next.js 16 frontend (chat at /, admin at /admin) — deploys to Vercel
```

They run independently and talk over HTTPS using `NEXT_PUBLIC_API_URL` (frontend → backend) and a CORS allow-list on the backend (`FRONTEND_ORIGINS`).

## ✨ Features

<table>
<tr>
<td>

### 🚀 Core Features
- 🤖 **AI-Powered Chat** - Intelligent conversational interface
- 🌐 **Modern Web UI** - Real-time streaming responses
- 🔍 **Semantic Search** - Vector embeddings with pgvector
- 📊 **Admin Panel** - Easy knowledge base management

</td>
<td>

### 🛡️ Production Ready
- 🔒 **Secure Auth** - Session management & authentication
- 🐳 **Dockerized** - Full container orchestration
- 📈 **Scalable** - Async architecture with FastAPI
- 🔧 **Configurable** - Environment-based configuration
- ⚡ **Rate Limiting** - Built-in API throttling with Redis

</td>
</tr>
</table>

## 📋 Prerequisites

<table>
<tr>
<td align="center">
<img src="https://raw.githubusercontent.com/docker/compose/main/logo.png" width="60" height="60" alt="Docker">
<br>
<b>Docker & Compose</b>
</td>
<td align="center">
<img src="https://nodejs.org/static/images/logo.svg" width="60" height="60" alt="Node.js">
<br>
<b>Node.js & pnpm</b>
</td>
<td align="center">
<img src="https://upload.wikimedia.org/wikipedia/commons/4/4d/OpenAI_Logo.svg" width="60" height="60" alt="OpenAI">
<br>
<b>OpenAI API Key</b>
</td>
</tr>
</table>

## 🚀 Quick Start

### 1️⃣ **Clone the repository**

```bash
git clone <repository-url>
cd AndresAI
```

### 2️⃣ **Configure the backend**

```bash
cd andres-ai-api
cp .env.example .env
# edit .env — at minimum set OPENAI_API_KEY, POSTGRES_PASSWORD, ADMIN_PASSWORD,
# FASTAPI_ADMIN_SECRET_KEY (32+ chars), and FRONTEND_ORIGINS
```

<details>
<summary>📝 <b>Environment Configuration</b> (click to expand)</summary>

```dotenv
# 🔑 OpenAI API Configuration
OPENAI_API_KEY=sk-proj-your-openai-api-key-here

# 📊 Logfire Configuration (optional - for observability)
LOGFIRE_TOKEN=pylf_v1_us_your-logfire-token-here

# 🗄️ Database Configuration
DB_CONNECTION_STRING=postgresql+asyncpg://chat_user:your_secure_password@db/chat_agent_db
POSTGRES_USER=chat_user
POSTGRES_PASSWORD=your_secure_password
POSTGRES_DB=chat_agent_db

# 🚦 Redis Configuration (for rate limiting)
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
# REDIS_PASSWORD=your_redis_password_if_needed

# 👤 FastAPI Admin
ADMIN_USER=admin
ADMIN_PASSWORD='your_secure_admin_password'
FASTAPI_ADMIN_SECRET_KEY='your_secret_key_here_32_chars_min'

# ⚙️ Application Configuration
APP_ENV=development
DEBUG=false

# 📈 Analytics Configuration (optional)
GA_TRACKING_ID=G-YOUR-TRACKING-ID-HERE
```

</details>

### 3️⃣ **Build and start the backend services**

```bash
# from andres-ai-api/
docker compose build
docker compose up
```

### 4️⃣ **Set up the pgvector extension**

```bash
# In another terminal
docker exec -it andres-ai-agent_db psql -U chat_user -d chat_agent_db
```

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### 5️⃣ **Configure and start the frontend**

```bash
cd ../andres-ai-app
cp .env.local.example .env.local
# edit .env.local — NEXT_PUBLIC_API_URL=http://localhost:8000 for local dev
pnpm install
pnpm dev
```

> The frontend uses **pnpm** (pinned via `packageManager` in `package.json`). Install it once with `npm install -g pnpm` or `corepack enable && corepack prepare pnpm@latest --activate`.

### 6️⃣ **Access the application**

<table>
<tr>
<td align="center">
<h4>💬 Chat Interface</h4>
<a href="http://localhost:3000/">http://localhost:3000/</a>
</td>
<td align="center">
<h4>⚙️ Admin Panel</h4>
<a href="http://localhost:3000/admin">http://localhost:3000/admin</a>
</td>
<td align="center">
<h4>⚡ API</h4>
<a href="http://localhost:8000/">http://localhost:8000/</a>
</td>
</tr>
</table>

## 🚦 API Rate Limiting

The application implements intelligent rate limiting to ensure fair usage and prevent abuse:

### Rate Limits

| Endpoint | Limit | Window | Description |
|----------|-------|--------|-------------|
| `/api/chats/history` | 100 requests | 60 seconds | Retrieve chat history |
| `/api/chats/send` | 30 requests | 60 seconds | Send messages to the AI |

### Features

- **🔴 Redis-powered** - Fast, distributed rate limiting using Redis
- **🔐 IP-based tracking** - Limits are applied per IP address (supports CloudFlare and proxies)
- **📱 User-friendly errors** - Clear messages with retry-after information
- **🔄 Automatic recovery** - Limits reset automatically after the time window

### Error Handling

When rate limits are exceeded:
- **HTTP 429 Status** - "Too Many Requests" response
- **Retry-After Header** - Indicates when the client can retry
- **User Notification** - Frontend displays friendly error messages without console spam

### Configuration

Rate limiting is automatically configured with the Redis settings in your `.env` file. No additional configuration needed!

## 💻 Development

### 🎨 Code Formatting

<table>
<tr>
<td>

#### 🐍 Python Code (Ruff)

```bash
# Format all Python files
docker compose run --rm backend uv run ruff format .

# Check for linting issues
docker compose run --rm backend uv run ruff check .

# Fix auto-fixable issues
docker compose run --rm backend uv run ruff check . --fix
```

</td>
<td>

#### 🌐 Frontend (Next.js + pnpm)

```bash
# from andres-ai-app/
pnpm dev           # dev server
pnpm build         # production build
pnpm lint          # ESLint
```

</td>
</tr>
</table>

> ⚠️ **Important**: After backend changes, run Ruff inside `andres-ai-api/`:
> ```bash
> cd andres-ai-api && docker compose run --rm backend uv run ruff format .
> ```

### 🗄️ Database Connection

```yaml
Connection String: jdbc:postgresql://localhost:15432/chat_agent_db
Username: chat_user
Password: (from your andres-ai-api/.env file)
```

### 📊 Data Management

#### Populate Geographic Data

To populate geographic data for existing users:

```bash
docker compose run --rm backend uv run python -m scripts.populate_user_geo_data
```

## 🎯 Configuring the Agent

The knowledge base powers your AI agent's contextual understanding. Manage it through the admin panel at `/admin`.

<details>
<summary>📚 <b>Knowledge Base Example</b> (click to expand)</summary>

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

The two projects deploy independently.

## Backend (`andres-ai-api/`) — Docker on your own server

> 💡 **Note**: You may need to use `sudo` for all docker commands.

### Prerequisites

- ✅ Install Docker on your server
- ✅ Configure your domain in `andres-ai-api/compose/prod/Caddyfile`
- ✅ Create production `andres-ai-api/.env`

<details>
<summary>🔐 <b>Production Environment Variables</b> (click to expand)</summary>

```dotenv
# 🔑 OpenAI API Configuration
OPENAI_API_KEY=sk-proj-your-openai-api-key-here

# 📊 Logfire Configuration (optional)
LOGFIRE_TOKEN=pylf_v1_us_your-logfire-token-here

# 🗄️ Database Configuration
DB_CONNECTION_STRING=postgresql+asyncpg://chat_user:your_secure_password@db/chat_agent_db
POSTGRES_USER=chat_user
POSTGRES_PASSWORD=your_secure_password
POSTGRES_DB=chat_agent_db

# 🚦 Redis Configuration (for rate limiting)
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
# REDIS_PASSWORD=your_redis_password_if_needed

# 👤 FastAPI Admin
ADMIN_USER=admin
ADMIN_PASSWORD='your_secure_admin_password'
FASTAPI_ADMIN_SECRET_KEY='your_secret_key_here_32_chars_min'

# ⚙️ Application Configuration
APP_ENV=production
DEBUG=false

# 📈 Analytics Configuration (optional)
GA_TRACKING_ID=G-YOUR-TRACKING-ID-HERE
```

</details>

### 🚀 Deploy Steps

```bash
cd andres-ai-api

# 1. Build the production images
docker compose -f docker-compose.prod.yml build

# 2. Start the services
docker compose -f docker-compose.prod.yml up -d

# 3. Setup pgvector extension
docker exec -it andres-ai-agent_db psql -U chat_user -d chat_agent_db -c "CREATE EXTENSION IF NOT EXISTS vector;"

# 4. Visit your API
# https://api.your-domain.com  (configured in compose/prod/Caddyfile)
```

### 🔄 Re-deployment

```bash
cd andres-ai-api
source deploy-server.sh
```

## Frontend (`andres-ai-app/`) — Vercel

The frontend is a standard Next.js app and deploys to Vercel with zero configuration.

1. Push the repo to GitHub.
2. In Vercel, create a new project and set **Root Directory** to `andres-ai-app`.
3. Add the env vars (Production + Preview):
   - `NEXT_PUBLIC_API_URL` = your deployed API base URL (no trailing slash).
   - `NEXT_PUBLIC_GA_TRACKING_ID` (optional).
4. On the backend, add the Vercel domain to `FRONTEND_ORIGINS` (comma-separated) and redeploy the API so CORS + cookie SameSite=None work.
5. Deploy. `/` is the chat, `/admin` is the admin (gated by JWT cookie). `/admin/*` is auto-excluded from indexing via `vercel.json`.

## 🛠️ Production Setup with Supervisor

<details>
<summary>⚡ <b>Auto-restart Configuration</b> (click to expand)</summary>

### 1. Install Supervisor
```bash
sudo apt install supervisor -y
```

### 2. Create Configuration
```bash
sudo nano /etc/supervisor/conf.d/ai_agent.conf
```

```ini
[program:ai_agent]
directory=/home/ubuntu/AndresAI/andres-ai-api
command=sudo /usr/bin/docker compose -f docker-compose.prod.yml up
autostart=true
autorestart=true
stderr_logfile=/var/log/ai_agent.err.log
stdout_logfile=/var/log/ai_agent.out.log
```

### 3. Apply Configuration
```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start ai_agent
```

### 📋 Useful Commands
```bash
# View logs
sudo tail -f /var/log/ai_agent.out.log

# Stop for debugging
sudo supervisorctl stop ai_agent
docker compose -f docker-compose.prod.yml up
```

</details>

---

<div align="center">

**Built with ❤️ using modern web technologies**

[![License](https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square)](LICENSE)

</div>
