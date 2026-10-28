import importlib
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

_original_argv = sys.argv[:]
sys.argv = [sys.argv[0]]
_graph_routes = importlib.import_module("lightrag.api.routers.graph_routes")
sys.argv = _original_argv


def _client() -> TestClient:
    nodes = [
        {
            "id": "P-101A",
            "entity_id": "P-101A",
            "entity_type": "Equipment",
            "class_code": "Equipment",
        },
        {
            "id": "出口压力不足",
            "entity_id": "出口压力不足",
            "entity_type": "FaultEvent",
            "class_code": "FaultEvent",
        },
    ]

    async def get_nodes_batch(node_ids):
        return {
            node["id"]: dict(node)
            for node in nodes
            if node["id"] in node_ids
        }

    storage = SimpleNamespace(
        get_all_nodes=AsyncMock(return_value=nodes),
        get_nodes_batch=AsyncMock(side_effect=get_nodes_batch),
        get_popular_labels=AsyncMock(
            return_value=["出口压力不足", "P-101A"]
        ),
        get_all_edges=AsyncMock(
            return_value=[
                {
                    "id": "edge-1",
                    "source": "P-101A",
                    "target": "出口压力不足",
                    "relation_code": "HAS_FAULT",
                }
            ]
        ),
    )
    rag = SimpleNamespace(workspace="dept_utility", chunk_entity_relation_graph=storage)
    rag.doc_status = SimpleNamespace(
        get_docs_paginated=AsyncMock(
            return_value=(
                [
                    (
                        "doc-1",
                        SimpleNamespace(
                            file_path="manual.md",
                            status="processed",
                            chunks_count=2,
                            content_summary="manual",
                            created_at="2026-01-01",
                            updated_at="2026-01-02",
                        ),
                    )
                ],
                1,
            )
        )
    )
    app = FastAPI()
    app.include_router(
        _graph_routes.create_graph_routes(rag, api_key="test-key")
    )
    return TestClient(app)


def test_graph_view_endpoint_returns_bounded_projection():
    response = _client().get(
        "/graph/views/equipment-faults?root=P-101A",
        headers={"X-API-Key": "test-key"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["view"] == "equipment-faults"
    assert payload["workspace"] == "dept_utility"
    assert {node["id"] for node in payload["nodes"]} == {
        "P-101A",
        "出口压力不足",
    }
    assert payload["edges"][0]["type"] == "HAS_FAULT"


def test_fault_causes_requires_an_explicit_root():
    response = _client().get(
        "/graph/views/fault-causes",
        headers={"X-API-Key": "test-key"},
    )

    assert response.status_code == 400
    assert "requires root" in response.json()["detail"]


def test_fault_causes_accepts_depth_above_ten():
    response = _client().get(
        "/graph/views/fault-causes?root=出口压力不足&max_depth=11&max_nodes=100",
        headers={"X-API-Key": "test-key"},
    )

    assert response.status_code == 200
    assert response.json()["root"] == "出口压力不足"


def test_fault_causes_still_rejects_depth_below_one():
    response = _client().get(
        "/graph/views/fault-causes?root=出口压力不足&max_depth=0",
        headers={"X-API-Key": "test-key"},
    )

    assert response.status_code == 422


def test_fault_causes_rejects_a_non_fault_event_root():
    response = _client().get(
        "/graph/views/fault-causes?root=P-101A",
        headers={"X-API-Key": "test-key"},
    )

    assert response.status_code == 400
    assert "must be a FaultEvent" in response.json()["detail"]


def test_label_details_returns_types_in_requested_order():
    response = _client().post(
        "/graph/label/details",
        headers={"X-API-Key": "test-key"},
        json={"labels": ["出口压力不足", "P-101A", "缺失节点"]},
    )

    assert response.status_code == 200
    assert response.json() == [
        {"label": "出口压力不足", "type": "FaultEvent", "exists": True},
        {"label": "P-101A", "type": "Equipment", "exists": True},
        {"label": "缺失节点", "type": "Unknown", "exists": False},
    ]


def test_popular_labels_can_include_types_without_changing_default_shape():
    client = _client()

    plain = client.get(
        "/graph/label/popular?limit=2",
        headers={"X-API-Key": "test-key"},
    )
    typed = client.get(
        "/graph/label/popular?limit=2&include_types=true",
        headers={"X-API-Key": "test-key"},
    )

    assert plain.status_code == 200
    assert plain.json() == ["出口压力不足", "P-101A"]
    assert typed.status_code == 200
    assert typed.json() == [
        {"label": "出口压力不足", "type": "FaultEvent", "exists": True},
        {"label": "P-101A", "type": "Equipment", "exists": True},
    ]


def test_department_files_view_uses_document_status_as_its_source():
    response = _client().get(
        "/graph/views/department-files",
        headers={"X-API-Key": "test-key"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert {node["id"] for node in payload["nodes"]} == {
        "department:dept_utility",
        "file:doc-1",
    }
    assert payload["edges"][0]["type"] == "OWNS_FILE"
