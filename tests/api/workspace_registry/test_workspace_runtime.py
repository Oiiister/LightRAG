"""Request scope selects the matching LightRAG and document manager."""

import asyncio
import sys
import types
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from lightrag.api.workspace_registry import WorkspaceRegistry
from lightrag.api.workspace_runtime import (
    WorkspaceRuntime,
    WorkspaceScopeMiddleware,
)

pytestmark = pytest.mark.offline


class FakeRag:
    def __init__(self, namespace: str, working_dir: str) -> None:
        self.workspace = namespace
        self.working_dir = working_dir
        self.initialized = 0
        self.migrated = 0
        self.finalized = 0
        for name in (
            "text_chunks",
            "full_docs",
            "full_entities",
            "full_relations",
            "entity_chunks",
            "relation_chunks",
            "entities_vdb",
            "relationships_vdb",
            "chunks_vdb",
            "chunk_entity_relation_graph",
            "llm_response_cache",
            "doc_status",
        ):
            setattr(self, name, FakeStorage())

    async def initialize_storages(self) -> None:
        await asyncio.sleep(0)
        self.initialized += 1

    async def check_and_migrate_data(self) -> None:
        self.migrated += 1

    async def finalize_storages(self) -> None:
        self.finalized += 1


class FakeStorage:
    def __init__(self) -> None:
        self.dropped = 0

    async def drop(self) -> dict[str, str]:
        self.dropped += 1
        return {"status": "success", "message": "dropped"}


class FakeDocumentManager:
    def __init__(self, namespace: str, input_dir: Path) -> None:
        self.workspace = namespace
        self.base_input_dir = input_dir


def _build(
    tmp_path: Path,
) -> tuple[WorkspaceRuntime, WorkspaceRegistry, list[FakeRag]]:
    registry = WorkspaceRegistry(tmp_path)
    default = registry.ensure_default("", name="Default")
    created: list[FakeRag] = []
    working_dir = tmp_path / "working"
    input_dir = tmp_path / "inputs"
    working_dir.mkdir()
    input_dir.mkdir()

    def build_rag(namespace: str) -> FakeRag:
        instance = FakeRag(namespace, str(working_dir))
        created.append(instance)
        return instance

    default_rag = FakeRag("", str(working_dir))
    runtime = WorkspaceRuntime(
        registry=registry,
        default_record=default,
        default_rag=default_rag,
        rag_factory=build_rag,
        document_manager_factory=lambda namespace: FakeDocumentManager(
            namespace, input_dir
        ),
    )
    return runtime, registry, created


def test_request_header_selects_isolated_instance(tmp_path: Path) -> None:
    runtime, registry, built = _build(tmp_path)
    workspace = registry.create("Research")

    app = FastAPI()
    app.add_middleware(WorkspaceScopeMiddleware, runtime=runtime)

    @app.get("/who")
    async def who() -> dict[str, Any]:
        return {
            "rag": runtime.rag.workspace,
            "document_manager": runtime.document_manager.workspace,
        }

    client = TestClient(app)
    default_response = client.get("/who")
    named_response = client.get(
        "/who", headers={"LIGHTRAG-WORKSPACE": workspace.id}
    )
    default_again = client.get("/who")

    assert default_response.json() == {"rag": "", "document_manager": ""}
    assert named_response.json() == {
        "rag": workspace.namespace,
        "document_manager": workspace.namespace,
    }
    assert default_again.json() == {"rag": "", "document_manager": ""}
    assert len(built) == 1
    assert built[0].initialized == 1
    assert built[0].migrated == 1


def test_unknown_workspace_is_rejected_before_route(tmp_path: Path) -> None:
    runtime, _, _ = _build(tmp_path)
    app = FastAPI()
    app.add_middleware(WorkspaceScopeMiddleware, runtime=runtime)

    @app.get("/who")
    async def who() -> dict[str, str]:
        return {"workspace": runtime.rag.workspace}

    response = TestClient(app).get(
        "/who", headers={"LIGHTRAG-WORKSPACE": "does_not_exist"}
    )

    assert response.status_code == 404
    assert "was not found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_concurrent_requests_keep_their_own_scope(tmp_path: Path) -> None:
    runtime, registry, _ = _build(tmp_path)
    first = registry.create("First")
    second = registry.create("Second")

    async def read(namespace: str):
        token = await runtime.activate(namespace)
        try:
            await asyncio.sleep(0.01)
            return runtime.rag.workspace
        finally:
            await runtime.release(token)

    values = await asyncio.gather(
        read(first.id),
        read(second.id),
        read(None),
        read(first.id),
    )

    assert values == [first.namespace, second.namespace, "", first.namespace]


@pytest.mark.asyncio
async def test_delete_workspace_drops_all_stores_and_removes_files(
    tmp_path: Path, monkeypatch
) -> None:
    runtime, registry, built = _build(tmp_path)
    workspace = registry.create("Temporary")
    working_workspace = tmp_path / "working" / workspace.namespace
    input_workspace = tmp_path / "inputs" / workspace.namespace
    working_workspace.mkdir()
    input_workspace.mkdir()
    (working_workspace / "data.json").write_text("{}", encoding="utf-8")
    (input_workspace / "document.txt").write_text("hello", encoding="utf-8")

    token = await runtime.activate(workspace.id)
    await runtime.release(token)
    instance = built[0]

    routers_package = types.ModuleType("lightrag.api.routers")
    routers_package.__path__ = []
    document_routes = types.ModuleType(
        "lightrag.api.routers.document_routes"
    )
    document_routes._acquire_destructive_busy = AsyncMock(return_value=(True, None))
    document_routes._release_destructive_busy = AsyncMock(return_value=None)
    monkeypatch.setitem(sys.modules, "lightrag.api.routers", routers_package)
    monkeypatch.setitem(
        sys.modules,
        "lightrag.api.routers.document_routes",
        document_routes,
    )

    await runtime.delete_workspace_data(workspace)

    for name in (
        "text_chunks",
        "full_docs",
        "full_entities",
        "full_relations",
        "entity_chunks",
        "relation_chunks",
        "entities_vdb",
        "relationships_vdb",
        "chunks_vdb",
        "chunk_entity_relation_graph",
        "llm_response_cache",
        "doc_status",
    ):
        assert getattr(instance, name).dropped == 1, name
    assert instance.finalized == 1
    assert not working_workspace.exists()
    assert not input_workspace.exists()
    # The route removes metadata only after data deletion succeeds.
    assert registry.get(workspace.id) == workspace
