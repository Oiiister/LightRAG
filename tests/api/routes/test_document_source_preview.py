import importlib
import sys
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

_original_argv = sys.argv[:]
sys.argv = [sys.argv[0]]
_document_routes = importlib.import_module("lightrag.api.routers.document_routes")
sys.argv = _original_argv

DocumentManager = _document_routes.DocumentManager
create_document_routes = _document_routes.create_document_routes

pytestmark = pytest.mark.offline


class _DocStatusStorage:
    def __init__(self, docs: dict[str, dict[str, str]]):
        self.docs = docs

    async def get_by_id(self, doc_id: str):
        return self.docs.get(doc_id)


def _client(input_dir, docs: dict[str, dict[str, str]]) -> TestClient:
    app = FastAPI()
    app.include_router(
        create_document_routes(
            SimpleNamespace(
                doc_status=_DocStatusStorage(docs),
                workspace="",
            ),
            DocumentManager(str(input_dir)),
            api_key="test-key",
        )
    )
    return TestClient(app)


def _headers() -> dict[str, str]:
    return {"X-API-Key": "test-key"}


def test_processed_source_is_served_as_safe_text_preview(tmp_path):
    input_dir = tmp_path / "inputs"
    parsed_dir = input_dir / "__parsed__"
    parsed_dir.mkdir(parents=True)
    (parsed_dir / "report.html").write_text(
        "<script>alert('must stay text')</script>", encoding="utf-8"
    )

    response = _client(
        input_dir,
        {"doc-1": {"file_path": "report.html"}},
    ).get("/documents/doc-1/file", headers=_headers())

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.text == "<script>alert('must stay text')</script>"


def test_pdf_preview_keeps_the_pdf_media_type(tmp_path):
    input_dir = tmp_path / "inputs"
    parsed_dir = input_dir / "__parsed__"
    parsed_dir.mkdir(parents=True)
    (parsed_dir / "manual.pdf").write_bytes(b"%PDF-1.7\n")

    response = _client(
        input_dir,
        {"doc-pdf": {"file_path": "manual.pdf"}},
    ).get("/documents/doc-pdf/file", headers=_headers())

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content == b"%PDF-1.7\n"


def test_svg_preview_is_sandboxed(tmp_path):
    input_dir = tmp_path / "inputs"
    input_dir.mkdir()
    (input_dir / "diagram.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>',
        encoding="utf-8",
    )

    response = _client(
        input_dir,
        {"doc-svg": {"file_path": "diagram.svg"}},
    ).get("/documents/doc-svg/file", headers=_headers())

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/svg+xml"
    assert response.headers["content-security-policy"].startswith("sandbox")


def test_unknown_document_returns_404(tmp_path):
    input_dir = tmp_path / "inputs"
    input_dir.mkdir()

    response = _client(input_dir, {}).get(
        "/documents/missing/file", headers=_headers()
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Document not found"


def test_missing_source_file_returns_404(tmp_path):
    input_dir = tmp_path / "inputs"
    input_dir.mkdir()

    response = _client(
        input_dir,
        {"doc-missing-file": {"file_path": "deleted.txt"}},
    ).get("/documents/doc-missing-file/file", headers=_headers())

    assert response.status_code == 404
    assert "no longer available" in response.json()["detail"]


def test_source_lookup_refuses_a_symlink_escape(tmp_path):
    input_dir = tmp_path / "inputs"
    parsed_dir = input_dir / "__parsed__"
    parsed_dir.mkdir(parents=True)
    outside = tmp_path / "outside-secret.txt"
    outside.write_text("must not leak", encoding="utf-8")
    (parsed_dir / "linked.txt").symlink_to(outside)

    response = _client(
        input_dir,
        {"doc-link": {"file_path": "linked.txt"}},
    ).get("/documents/doc-link/file", headers=_headers())

    assert response.status_code == 404
    assert "no longer available" in response.json()["detail"]
