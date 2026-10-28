"""Workspace management endpoints for the admin WebUI."""

from __future__ import annotations

import traceback
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from lightrag.utils import logger

from ..utils_api import get_combined_auth_dependency, internal_server_error
from ..workspace_registry import (
    DefaultWorkspaceDeletionError,
    WorkspaceConflictError,
    WorkspaceNotFoundError,
    WorkspaceRegistryError,
    WorkspaceValidationError,
)
from ..workspace_runtime import (
    WorkspaceBusyError,
    WorkspaceDataDeletionError,
    WorkspaceRuntime,
)


class WorkspaceNameRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)


class WorkspaceInfo(BaseModel):
    id: str
    name: str
    is_default: bool
    created_at: str
    updated_at: str


class WorkspaceListResponse(BaseModel):
    workspaces: list[WorkspaceInfo]
    default_workspace_id: str


class WorkspaceDeleteResponse(BaseModel):
    deleted: bool
    workspace: WorkspaceInfo


def _workspace_error(exc: Exception) -> HTTPException:
    if isinstance(exc, WorkspaceNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(
        exc,
        (
            WorkspaceConflictError,
            WorkspaceValidationError,
            DefaultWorkspaceDeletionError,
            WorkspaceBusyError,
        ),
    ):
        return HTTPException(status_code=409, detail=str(exc))
    if isinstance(exc, WorkspaceRegistryError):
        logger.error("Workspace registry error: %s", exc)
        return HTTPException(status_code=503, detail="Workspace metadata is unavailable")
    return internal_server_error(exc)


def create_workspace_routes(
    runtime: WorkspaceRuntime, api_key: Optional[str] = None
) -> APIRouter:
    """Create the workspace CRUD router.

    A workspace is registered before data is created.  Selecting it in the
    WebUI lazily builds the complete LightRAG storage set for that namespace.
    """

    router = APIRouter(prefix="/workspaces", tags=["workspaces"])
    combined_auth = get_combined_auth_dependency(api_key)

    def _public(record):
        return WorkspaceInfo(**record.public_dict())

    @router.get(
        "",
        response_model=WorkspaceListResponse,
        dependencies=[Depends(combined_auth)],
    )
    async def list_workspaces(
        q: str | None = Query(
            None,
            max_length=80,
            description="Filter by workspace display name or identifier",
        )
    ):
        try:
            return WorkspaceListResponse(
                workspaces=[_public(record) for record in runtime.registry.list(q)],
                default_workspace_id=runtime.default_workspace_id,
            )
        except WorkspaceRegistryError as exc:
            raise _workspace_error(exc) from exc

    @router.get(
        "/{workspace_id}",
        response_model=WorkspaceInfo,
        dependencies=[Depends(combined_auth)],
    )
    async def get_workspace(workspace_id: str):
        try:
            return _public(runtime.record(workspace_id))
        except Exception as exc:
            raise _workspace_error(exc) from exc

    @router.post(
        "",
        response_model=WorkspaceInfo,
        status_code=201,
        dependencies=[Depends(combined_auth)],
    )
    async def create_workspace(payload: WorkspaceNameRequest):
        try:
            return _public(runtime.registry.create(payload.name))
        except Exception as exc:
            raise _workspace_error(exc) from exc

    @router.patch(
        "/{workspace_id}",
        response_model=WorkspaceInfo,
        dependencies=[Depends(combined_auth)],
    )
    async def rename_workspace(workspace_id: str, payload: WorkspaceNameRequest):
        try:
            return _public(runtime.registry.rename(workspace_id, payload.name))
        except Exception as exc:
            raise _workspace_error(exc) from exc

    @router.delete(
        "/{workspace_id}",
        response_model=WorkspaceDeleteResponse,
        dependencies=[Depends(combined_auth)],
    )
    async def delete_workspace(workspace_id: str):
        """Delete one workspace's data and metadata.

        The registry row is removed only after every storage backend reported a
        successful drop.  A partial failure leaves the row in place so the
        operator can retry instead of hiding data under an unregistered id.
        """

        try:
            record = runtime.record(workspace_id)
            await runtime.delete_workspace_data(record)
            removed = runtime.registry.remove(workspace_id)
            return WorkspaceDeleteResponse(
                deleted=True,
                workspace=_public(removed),
            )
        except WorkspaceDataDeletionError as exc:
            logger.error("Workspace deletion failed: %s", exc)
            logger.error(traceback.format_exc())
            if str(exc) in {
                "The default workspace cannot be deleted",
            } or "busy" in str(exc).lower() or "being deleted" in str(exc).lower():
                raise HTTPException(status_code=409, detail=str(exc)) from exc
            raise HTTPException(
                status_code=500,
                detail="Workspace data could not be fully deleted. The workspace was kept so the deletion can be retried.",
            ) from exc
        except Exception as exc:
            raise _workspace_error(exc) from exc

    return router
