"""Workspace CRUD endpoints share one stable id and editable display name."""

from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# The API router package imports modules that parse the server CLI at import
# time. Keep pytest's flags out of that parser, as the neighbouring route tests
# also do.
_original_argv = sys.argv[:]
sys.argv = [sys.argv[0]]
from lightrag.api.routers.workspace_routes import create_workspace_routes  # noqa: E402
from lightrag.api.workspace_registry import WorkspaceRegistry  # noqa: E402

sys.argv = _original_argv

pytestmark = pytest.mark.offline
_HEADERS = {"X-API-Key": "test-key"}


def _client(tmp_path: Path):
    registry = WorkspaceRegistry(tmp_path)
    registry.ensure_default("", name="Default")
    runtime = SimpleNamespace(
        registry=registry,
        default_workspace_id="default",
        record=registry.get,
        delete_workspace_data=AsyncMock(return_value=None),
    )
    app = FastAPI()
    app.include_router(create_workspace_routes(runtime, api_key="test-key"))
    return TestClient(app), runtime


def test_create_query_rename_and_delete(tmp_path: Path) -> None:
    client, runtime = _client(tmp_path)

    initial = client.get("/workspaces", headers=_HEADERS)
    assert initial.status_code == 200
    assert initial.json()["default_workspace_id"] == "default"
    assert [item["name"] for item in initial.json()["workspaces"]] == ["Default"]

    created = client.post(
        "/workspaces", json={"name": "Customer A"}, headers=_HEADERS
    )
    assert created.status_code == 201
    workspace = created.json()
    assert workspace["id"].startswith("ws_")
    assert workspace["name"] == "Customer A"
    assert "namespace" not in workspace

    fetched = client.get(f"/workspaces/{workspace['id']}", headers=_HEADERS)
    assert fetched.status_code == 200
    assert fetched.json() == workspace

    filtered = client.get(
        "/workspaces", params={"q": "customer"}, headers=_HEADERS
    )
    assert [item["id"] for item in filtered.json()["workspaces"]] == [
        workspace["id"]
    ]

    renamed = client.patch(
        f"/workspaces/{workspace['id']}",
        json={"name": "Customer Legal"},
        headers=_HEADERS,
    )
    assert renamed.status_code == 200
    assert renamed.json()["id"] == workspace["id"]
    assert renamed.json()["name"] == "Customer Legal"

    deleted = client.delete(
        f"/workspaces/{workspace['id']}", headers=_HEADERS
    )
    assert deleted.status_code == 200
    assert deleted.json()["deleted"] is True
    runtime.delete_workspace_data.assert_awaited_once()
    assert client.get(
        f"/workspaces/{workspace['id']}", headers=_HEADERS
    ).status_code == 404


def test_duplicate_name_is_a_conflict(tmp_path: Path) -> None:
    client, _ = _client(tmp_path)

    first = client.post("/workspaces", json={"name": "Research"}, headers=_HEADERS)
    second = client.post("/workspaces", json={"name": "research"}, headers=_HEADERS)

    assert first.status_code == 201
    assert second.status_code == 409
