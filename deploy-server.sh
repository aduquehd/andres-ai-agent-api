#!/bin/sh

git pull
sudo docker compose -f docker-compose.prod.yml build

# Run DB migrations inside the backend container
sudo docker compose -f docker-compose.prod.yml run --rm backend uv run alembic upgrade head

# Restart services
sudo supervisorctl stop ai_agent
sudo docker compose -f docker-compose.prod.yml down
sudo docker compose -f docker-compose.prod.yml stop
sudo supervisorctl restart ai_agent
