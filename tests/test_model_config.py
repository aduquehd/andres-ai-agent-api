from collections.abc import AsyncIterator, Iterator
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from pydantic_ai.exceptions import ModelHTTPError
from pydantic_ai.models.function import AgentInfo, FunctionModel

from config import settings
from modules.admin.auth import require_admin
from modules.admin.routers import router as admin_router
from modules.agent.agent import DEFAULT_MAX_TOKENS, agent
from modules.agent.models import AgentModelConfig
from modules.agent.services import build_model_settings, get_agent_model_config
from modules.utils.database import get_session


class FakeSession:
    """Just enough of AsyncSession for the single-row model config."""

    def __init__(self) -> None:
        self.rows: dict[tuple[type, int], object] = {}

    async def get(self, model: type, pk: int) -> object | None:
        return self.rows.get((model, pk))

    def add(self, obj: object) -> None:
        self.rows[(type(obj), obj.id)] = obj

    async def delete(self, obj: object) -> None:
        self.rows.pop((type(obj), obj.id), None)

    async def commit(self) -> None:
        pass

    async def refresh(self, obj: object) -> None:
        pass


@pytest.fixture
def session() -> FakeSession:
    return FakeSession()


@pytest.fixture
async def client(
    session: FakeSession, monkeypatch: pytest.MonkeyPatch
) -> AsyncIterator[AsyncClient]:
    # Saving a model builds its provider client, which needs a key to exist.
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    app = FastAPI()
    app.include_router(admin_router)
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[require_admin] = lambda: "admin"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


SAVED = {
    "model": "anthropic:claude-opus-5-5",
    "effort": "low",
    "max_tokens": 2048,
    "temperature": None,
}


# The stand-in models only stream, so a test turn that didn't stream the way the
# chat does would fail.


async def answer(_messages, _info: AgentInfo) -> AsyncIterator[str]:
    yield "I'm Andres."


async def reject(_messages, _info: AgentInfo) -> AsyncIterator[str]:
    raise ModelHTTPError(status_code=404, model_name="claude-typo", body={"message": "nope"})
    yield  # unreachable, makes this an async generator


@pytest.fixture
def provider_accepts(system_prompt: str, kb_search: AsyncMock) -> Iterator[None]:
    """Stand in for the provider so the test turn that saving runs passes."""
    with agent.override(model=FunctionModel(stream_function=answer)):
        yield


def test_build_model_settings_skips_unset_fields():
    assert build_model_settings(AgentModelConfig(model="anthropic:claude-sonnet-5-5")) == {}


def test_build_model_settings_maps_every_field():
    config = AgentModelConfig(
        model="anthropic:claude-sonnet-4-6", effort="high", max_tokens=1000, temperature=0.0
    )
    assert build_model_settings(config) == {
        "anthropic_effort": "high",
        "max_tokens": 1000,
        "temperature": 0.0,
    }


async def test_agent_uses_settings_default_when_nothing_saved(session: FakeSession):
    config = await get_agent_model_config(session)
    assert config.model == settings.agent_model
    assert build_model_settings(config) == {}


async def test_get_reports_default_when_nothing_saved(client: AsyncClient):
    body = (await client.get("/api/admin/model-config")).json()
    assert body["source"] == "default"
    assert body["model"] == settings.agent_model
    assert body["default_max_tokens"] == DEFAULT_MAX_TOKENS
    assert body["updated_at"] is None


@pytest.mark.usefixtures("provider_accepts")
async def test_save_is_read_back_by_admin_and_agent(client: AsyncClient, session: FakeSession):
    response = await client.patch("/api/admin/model-config", json=SAVED)
    assert response.status_code == 200
    assert response.json()["source"] == "database"

    body = (await client.get("/api/admin/model-config")).json()
    assert {key: body[key] for key in SAVED} == SAVED
    assert body["updated_at"]

    config = await get_agent_model_config(session)
    assert config.model == SAVED["model"]
    assert build_model_settings(config) == {"anthropic_effort": "low", "max_tokens": 2048}


@pytest.mark.usefixtures("provider_accepts")
async def test_reset_falls_back_to_default(client: AsyncClient):
    await client.patch("/api/admin/model-config", json=SAVED)
    response = await client.delete("/api/admin/model-config")
    assert response.json()["source"] == "default"
    assert (await client.get("/api/admin/model-config")).json()["model"] == settings.agent_model


@pytest.mark.parametrize(
    "payload",
    [
        {"model": "claude-sonnet-5-5"},  # no provider prefix
        {"model": "anthropic:"},
        {"model": "anthropic:claude-sonnet-5-5", "effort": "extreme"},
        {"model": "anthropic:claude-sonnet-5-5", "max_tokens": 0},
        {"model": "anthropic:claude-sonnet-5-5", "temperature": 3},
    ],
)
async def test_save_rejects_malformed_payload(client: AsyncClient, payload: dict):
    assert (await client.patch("/api/admin/model-config", json=payload)).status_code == 422
    assert (await client.get("/api/admin/model-config")).json()["source"] == "default"


async def test_save_rejects_unknown_provider(client: AsyncClient):
    response = await client.patch("/api/admin/model-config", json={"model": "nope:some-model"})
    assert response.status_code == 400
    assert "nope:some-model" in response.json()["detail"]
    assert (await client.get("/api/admin/model-config")).json()["source"] == "default"


async def test_save_rejects_provider_without_api_key(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.delenv("ANTHROPIC_API_KEY")
    response = await client.patch("/api/admin/model-config", json=SAVED)
    assert response.status_code == 400


async def test_save_rejects_temperature_the_model_would_drop(client: AsyncClient):
    payload = SAVED | {"model": "anthropic:claude-sonnet-5-5", "temperature": 0.5}
    response = await client.patch("/api/admin/model-config", json=payload)
    assert response.status_code == 400
    assert "temperature" in response.json()["detail"]
    assert (await client.get("/api/admin/model-config")).json()["source"] == "default"


@pytest.mark.usefixtures("provider_accepts")
async def test_save_keeps_temperature_for_models_that_take_it(client: AsyncClient):
    payload = SAVED | {"model": "anthropic:claude-sonnet-4-6", "temperature": 0.5}
    response = await client.patch("/api/admin/model-config", json=payload)
    assert response.status_code == 200
    assert response.json()["temperature"] == 0.5


async def test_save_refuses_config_the_provider_rejects(
    client: AsyncClient, system_prompt: str, kb_search: AsyncMock
):
    with agent.override(model=FunctionModel(stream_function=reject)):
        response = await client.patch("/api/admin/model-config", json=SAVED)

    assert response.status_code == 400
    assert "404" in response.json()["detail"]
    assert (await client.get("/api/admin/model-config")).json()["source"] == "default"


async def test_test_endpoint_runs_agent_with_candidate_config(
    client: AsyncClient, system_prompt: str, kb_search: AsyncMock
):
    seen: list[AgentInfo] = []

    async def reply(_messages, info: AgentInfo) -> AsyncIterator[str]:
        seen.append(info)
        yield "I'm Andres."

    with agent.override(model=FunctionModel(stream_function=reply)):
        response = await client.post("/api/admin/model-config/test", json=SAVED)

    body = response.json()
    assert body["ok"] is True
    assert body["output"] == "I'm Andres."
    assert seen[0].model_settings == {"anthropic_effort": "low", "max_tokens": 2048}
    # Testing a config must not save it.
    assert (await client.get("/api/admin/model-config")).json()["source"] == "default"


async def test_test_endpoint_reports_provider_errors(
    client: AsyncClient, system_prompt: str, kb_search: AsyncMock
):
    with agent.override(model=FunctionModel(stream_function=reject)):
        response = await client.post("/api/admin/model-config/test", json=SAVED)

    body = response.json()
    assert response.status_code == 200
    assert body["ok"] is False
    assert "404" in body["error"]


async def test_test_endpoint_reports_unexpected_errors(
    client: AsyncClient, system_prompt: str, kb_search: AsyncMock
):
    async def crash(_messages, _info: AgentInfo) -> AsyncIterator[str]:
        raise RuntimeError("embedding service down")
        yield  # unreachable, makes this an async generator

    with agent.override(model=FunctionModel(stream_function=crash)):
        response = await client.post("/api/admin/model-config/test", json=SAVED)

    assert response.status_code == 200
    assert response.json() == {"ok": False, "error": "RuntimeError: embedding service down"}


async def test_test_endpoint_refuses_an_empty_reply(
    client: AsyncClient, system_prompt: str, kb_search: AsyncMock
):
    async def silent(_messages, _info: AgentInfo) -> AsyncIterator[str]:
        yield ""

    with agent.override(model=FunctionModel(stream_function=silent)):
        response = await client.post("/api/admin/model-config/test", json=SAVED)

    # Pydantic AI refuses an empty answer itself, so it can't be saved as a passing config.
    assert response.json()["ok"] is False
