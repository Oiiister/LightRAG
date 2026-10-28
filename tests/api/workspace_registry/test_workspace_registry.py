"""Workspace metadata is stable, searchable and safe to mutate concurrently."""

from pathlib import Path

import pytest

from lightrag.api.workspace_registry import (
    DefaultWorkspaceDeletionError,
    WorkspaceConflictError,
    WorkspaceNotFoundError,
    WorkspaceRegistry,
    WorkspaceRegistryError,
    WorkspaceValidationError,
)

pytestmark = pytest.mark.offline


def test_default_record_is_registered_once(tmp_path: Path) -> None:
    registry = WorkspaceRegistry(tmp_path)

    first = registry.ensure_default("", name="Default")
    second = registry.ensure_default("", name="Ignored after creation")

    assert first == second
    assert first.id == "default"
    assert first.namespace == ""
    assert first.is_default is True
    assert [record.id for record in registry.list()] == ["default"]


def test_create_rename_search_and_delete(tmp_path: Path) -> None:
    registry = WorkspaceRegistry(tmp_path)
    registry.ensure_default("default")

    created = registry.create("  Customer   A  ")
    assert created.name == "Customer A"
    assert created.id.startswith("ws_")
    assert created.namespace == created.id

    renamed = registry.rename(created.id, "法务知识库")
    assert renamed.id == created.id
    assert renamed.namespace == created.namespace
    assert renamed.name == "法务知识库"
    assert [record.id for record in registry.list("法务")] == [created.id]
    assert [record.id for record in registry.list(created.id[:8])] == [created.id]

    removed = registry.remove(created.id)
    assert removed.id == created.id
    with pytest.raises(WorkspaceNotFoundError):
        registry.get(created.id)


def test_names_are_unique_case_insensitively(tmp_path: Path) -> None:
    registry = WorkspaceRegistry(tmp_path)
    registry.ensure_default("default")
    created = registry.create("Finance")

    with pytest.raises(WorkspaceConflictError):
        registry.create("finance")
    with pytest.raises(WorkspaceConflictError):
        registry.rename("default", "FINANCE")

    assert registry.get(created.id).name == "Finance"


def test_default_workspace_cannot_be_deleted(tmp_path: Path) -> None:
    registry = WorkspaceRegistry(tmp_path)
    default = registry.ensure_default("", name="Primary")

    with pytest.raises(DefaultWorkspaceDeletionError):
        registry.remove(default.id)


@pytest.mark.parametrize(
    "name",
    ["", " ", "\n", "x" * 81, "bad\x00name"],
)
def test_invalid_names_are_rejected(tmp_path: Path, name: str) -> None:
    registry = WorkspaceRegistry(tmp_path)
    registry.ensure_default("default")

    with pytest.raises(WorkspaceValidationError):
        registry.create(name)


def test_corrupt_registry_fails_loudly(tmp_path: Path) -> None:
    registry = WorkspaceRegistry(tmp_path)
    registry.path.write_text("{not json", encoding="utf-8")

    with pytest.raises(WorkspaceRegistryError):
        registry.list()
