# CLAUDE.md — andres-ai-api

This file provides guidance to Claude Code (claude.ai/code) when working with the **backend API** in this directory. The frontend (chat UI + admin) lives in `../andres-ai-app/`.

## Project Overview

FastAPI backend for the AndresAI chat assistant. Provides streaming chat endpoints (RAG over PostgreSQL+pgvector) and a JSON admin API consumed by the Next.js frontend. Users are identified by client-generated UUIDs sent in headers.

## Key Technologies

- **Backend**: FastAPI, SQLModel, Pydantic AI
- **Database**: PostgreSQL with pgvector extension
- **Cache/Rate Limiting**: Redis with fastapi-limiter
- **Containerization**: Docker Compose
- **Package Manager**: uv (Python)
- **Code Quality**: Ruff for linting/formatting
- **Migrations**: Alembic
- **Frontend**: served separately by `../andres-ai-app/` (Next.js on Vercel)

## Essential Commands

Run all commands from this directory (`andres-ai-api/`).

### Development

```bash
# Build and start services
docker compose build
docker compose up

# Run database migrations
docker compose run --rm backend uv run alembic upgrade head

# Create new migration
docker compose run --rm backend uv run alembic revision --autogenerate -m "description"

# Lint and format Python code
uv run ruff check .
uv run ruff format .

# API base URL (local): http://localhost:8000
```

### Production Deployment

```bash
# Quick deploy (uses deploy-server.sh)
source deploy-server.sh

# Manual deploy
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up
```

## Architecture

- **modules/**: Core business logic organized by domain
  - **admin/**: JSON CRUD routes for the admin UI (replaces the prior SQLAdmin views)
  - **agent/**: AI agent logic and models
  - **chats/**: Chat functionality and streaming
  - **knowledge_base/**: RAG system for agent context
  - **users/**: User management
  - **utils/**: Shared utilities (auth, database, agent, rate limiting)

The Jinja templates and TypeScript frontend that used to live here have moved to `../andres-ai-app/`.

## Critical Setup Requirements

1. **Environment Variables**: Create `.env` in this directory with:

   ```dotenv
   # OpenAI API Configuration
   OPENAI_API_KEY=sk-proj-your-openai-api-key-here

   # Logfire Configuration (optional - for observability)
   LOGFIRE_TOKEN=pylf_v1_us_your-logfire-token-here

   # Database Configuration
   DB_CONNECTION_STRING=postgresql+asyncpg://chat_user:your_secure_password@db/chat_agent_db
   POSTGRES_USER=chat_user
   POSTGRES_PASSWORD=your_secure_password
   POSTGRES_DB=chat_agent_db

   # Redis Configuration (for rate limiting)
   REDIS_HOST=redis
   REDIS_PORT=6379
   REDIS_DB=0

   # Admin auth (JWT for admin API)
   ADMIN_USER=admin
   ADMIN_PASSWORD='your_secure_admin_password'
   FASTAPI_ADMIN_SECRET_KEY='your_secret_key_here_32_chars_min'

   # CORS — comma-separated list of allowed Next.js origins
   FRONTEND_ORIGINS=http://localhost:3000,https://your-vercel-domain.vercel.app

   # Application Configuration
   APP_ENV=development
   DEBUG=false

   # Optional
   GA_TRACKING_ID=G-YOUR-TRACKING-ID-HERE
   SENTRY_DSN=https://your-project-id@o0.ingest.sentry.io/0
   ```

2. **pgvector Extension**: Must be manually enabled after first container start:
   ```bash
   docker exec -it andres-ai-agent_db psql -U chat_user -d chat_agent_db
   CREATE EXTENSION IF NOT EXISTS vector;
   \q
   ```

## API Endpoints

### Chat API (consumed by the Next.js chat UI)

- `GET /api/chats/history` — chat history for the authenticated UUID user. Rate limit: 100/min/IP.
- `POST /api/chats/send` — sends a message; streams newline-delimited JSON. Rate limit: 30/min/IP.

Auth: `Authorization: User-Id <uuid>` and `X-Browser-Id: <uuid>` headers (CORS allows credentials).

### Admin API (consumed by the Next.js admin at `/admin`)

- `POST /api/admin/login` — username/password → sets httpOnly JWT cookie
- `POST /api/admin/logout` — clears cookie
- `GET /api/admin/me` — returns current admin session info
- `GET/POST/PATCH/DELETE /api/admin/users`
- `GET/POST/PATCH/DELETE /api/admin/messages`
- `GET/POST/PATCH/DELETE /api/admin/agent-messages`
- `GET/POST/PATCH/DELETE /api/admin/knowledge-base` (regenerates embedding on save)
- `GET/POST/PATCH/DELETE /api/admin/agent-contexts`

## Database Schema

Key models in `modules/*/models.py`:

- **User**: User accounts
- **AgentMessage**: Pydantic AI message lists per user
- **Message**: Individual user/agent message records
- **KnowledgeBase**: Vector-indexed agent context
- **AgentContext**: Agent context entries

## Local Database Connection

- Connection string: `jdbc:postgresql://localhost:15432/chat_agent_db`
- Username: `chat_user`
- Password: from `.env`
