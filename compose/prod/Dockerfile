FROM python:3.14.9-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

ADD https://astral.sh/uv/install.sh /uv-installer.sh
RUN sh /uv-installer.sh && rm /uv-installer.sh
ENV PATH="/root/.local/bin/:$PATH"
ENV UV_PROJECT_ENVIRONMENT="/usr/local"
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# Dependencies first, in their own layer: this only rebuilds when pyproject.toml
# or uv.lock change, so ordinary source commits reuse the cached dependency set.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Source last: the layer that changes on every commit is also the cheapest one.
COPY . /app
RUN uv sync --frozen --no-dev

EXPOSE 8000
