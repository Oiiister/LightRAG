"""Request-scoped LightRAG instances for multi-workspace API use.

Every HTTP request selects one workspace through ``LIGHTRAG-WORKSPACE``.  The
routes keep receiving a stable object, while this module resolves that object to
the initialized LightRAG instance (and document manager) for the selected
workspace.  Storage namespaces, uploaded files, graph state, vectors, document
status and pipeline state therefore all move together.

See ``docs/design/WorkspaceManagementContract.md`` for the request-isolation,
deletion ordering and accepted multi-worker residues.
"""

from __future__ import annotations

import asyncio
import contextvars
import inspect
import shutil
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

from lightrag.utils import logger, validate_workspace

from .asgi_helpers import header_value, send_json
from .workspace_registry import (
    WorkspaceNotFoundError,
    WorkspaceRecord,
    WorkspaceRegistry,
    WorkspaceRegistryError,
)

WORKSPACE_HEADER = b"lightrag-workspace"


async def _await_if_needed(value: Any) -> None:
    if inspect.isawaitable(value):
        await value


class WorkspaceDataDeletionError(RuntimeError):
    """Workspace data could not be fully removed."""


class WorkspaceBusyError(RuntimeError):
    """A workspace is being deleted or is otherwise unavailable for a new request."""


class WorkspaceRuntimeError(RuntimeError):
    """A request tried to use a workspace whose instance was unavailable."""


class _ScopedObject:
    def __init__(self, runtime: "WorkspaceRuntime", kind: str) -> None:
        object.__setattr__(self, "_runtime", runtime)
        object.__setattr__(self, "_kind", kind)

    def _target(self) -> Any:
        if self._kind == "rag":
            return self._runtime.current_rag()
        return self._runtime.current_document_manager()

    def __getattr__(self, name: str) -> Any:
        return getattr(self._target(), name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith("_"):
            object.__setattr__(self, name, value)
            return
        setattr(self._target(), name, value)

    def __dir__(self) -> list[str]:
        return sorted(set(super().__dir__()) | set(dir(self._target())))

    def __repr__(self) -> str:
        return f"<scoped {self._kind} workspace={self._runtime.current_workspace_id()!r}>"


class WorkspaceRuntime:
    """Own the default instance and lazily initialized named workspaces."""

    def __init__(
        self,
        *,
        registry: WorkspaceRegistry,
        default_record: WorkspaceRecord,
        default_rag: Any,
        rag_factory: Callable[[str], Any],
        document_manager_factory: Callable[[str], Any],
        on_instance_created: Callable[[Any], None] | None = None,
    ) -> None:
        self.registry = registry
        self.default_record = default_record
        self.default_workspace_id = default_record.id
        self._instances: dict[str, Any] = {default_record.id: default_rag}
        self._document_managers: dict[str, Any] = {
            default_record.id: document_manager_factory(default_record.namespace)
        }
        self._initialized: set[str] = set()
        self._rag_factory = rag_factory
        self._document_manager_factory = document_manager_factory
        self._on_instance_created = on_instance_created
        self._activation_lock = asyncio.Lock()
        self._activity_condition = asyncio.Condition()
        self._active_requests: dict[str, int] = {}
        self._deleting: set[str] = set()
        self._active_workspace: contextvars.ContextVar[str | None] = (
            contextvars.ContextVar("lightrag_active_workspace", default=None)
        )
        self.rag = _ScopedObject(self, "rag")
        self.document_manager = _ScopedObject(self, "document_manager")

    def current_workspace_id(self) -> str:
        return self._active_workspace.get() or self.default_workspace_id

    def current_rag(self) -> Any:
        workspace_id = self.current_workspace_id()
        try:
            return self._instances[workspace_id]
        except KeyError as exc:
            raise WorkspaceRuntimeError(
                f"Workspace {workspace_id!r} is not active"
            ) from exc

    def current_document_manager(self) -> Any:
        workspace_id = self.current_workspace_id()
        try:
            return self._document_managers[workspace_id]
        except KeyError as exc:
            raise WorkspaceRuntimeError(
                f"Document manager for workspace {workspace_id!r} is not active"
            ) from exc

    async def _initialize_instance(self, workspace_id: str, instance: Any) -> None:
        if workspace_id in self._initialized:
            return
        # Test doubles expose these as synchronous mocks; real LightRAG methods
        # return awaitables. Supporting both keeps route-level tests independent
        # of the storage stack.
        await _await_if_needed(instance.initialize_storages())
        await _await_if_needed(instance.check_and_migrate_data())
        self._initialized.add(workspace_id)

    async def initialize_default(self) -> None:
        await self._initialize_instance(
            self.default_workspace_id, self._instances[self.default_workspace_id]
        )

    async def activate(self, workspace_id: str | None) -> contextvars.Token[str | None]:
        """Select, initialize and bind one workspace to the current request."""

        requested_id = (workspace_id or "").strip() or self.default_workspace_id
        record = self.registry.get(requested_id)
        async with self._activation_lock:
            instance = self._instances.get(record.id)
            if instance is None:
                instance = self._rag_factory(record.namespace)
                if self._on_instance_created is not None:
                    self._on_instance_created(instance)
                document_manager = self._document_manager_factory(record.namespace)
                self._instances[record.id] = instance
                self._document_managers[record.id] = document_manager
            await self._initialize_instance(record.id, instance)
        async with self._activity_condition:
            if record.id in self._deleting:
                raise WorkspaceBusyError(
                    f"Workspace {record.name!r} is being deleted"
                )
            self._active_requests[record.id] = (
                self._active_requests.get(record.id, 0) + 1
            )
        return self._active_workspace.set(record.id)

    async def release(self, token: contextvars.Token[str | None]) -> None:
        workspace_id = self.current_workspace_id()
        self._active_workspace.reset(token)
        await self._release_activity(workspace_id)

    async def _release_activity(self, workspace_id: str) -> None:
        async with self._activity_condition:
            current = self._active_requests.get(workspace_id, 0)
            if current <= 1:
                self._active_requests.pop(workspace_id, None)
            else:
                self._active_requests[workspace_id] = current - 1
            self._activity_condition.notify_all()

    def record(self, workspace_id: str) -> WorkspaceRecord:
        return self.registry.get(workspace_id)

    async def delete_workspace_data(self, record: WorkspaceRecord) -> None:
        """Drop every storage namespace and remove workspace-owned files."""

        if record.is_default:
            raise WorkspaceDataDeletionError(
                "The default workspace cannot be deleted"
            )
        current_workspace_id = self.current_workspace_id()
        own_request_count = 1 if current_workspace_id == record.id else 0
        async with self._activity_condition:
            if record.id in self._deleting:
                raise WorkspaceBusyError(
                    f"Workspace {record.name!r} is already being deleted"
                )
            self._deleting.add(record.id)
            await self._activity_condition.wait_for(
                lambda: self._active_requests.get(record.id, 0) <= own_request_count
            )
        try:
            await self._delete_workspace_data_locked(record)
        finally:
            async with self._activity_condition:
                self._deleting.discard(record.id)
                self._activity_condition.notify_all()

    async def _delete_workspace_data_locked(self, record: WorkspaceRecord) -> None:
        validate_workspace(record.namespace)
        async with self._activation_lock:
            instance = self._instances.get(record.id)
            if instance is None:
                instance = self._rag_factory(record.namespace)
                if self._on_instance_created is not None:
                    self._on_instance_created(instance)
                document_manager = self._document_manager_factory(record.namespace)
                self._instances[record.id] = instance
                self._document_managers[record.id] = document_manager
            await self._initialize_instance(record.id, instance)

        # Imported lazily: document_routes imports route factories which rely on
        # this runtime module, and a module-level import would create a cycle.
        from .routers.document_routes import (
            _acquire_destructive_busy,
            _release_destructive_busy,
        )

        token = uuid.uuid4().hex
        acquired = False
        drop_failures: list[str] = []
        try:
            acquired, reason = await _acquire_destructive_busy(
                instance,
                token,
                kind="workspace_delete",
                operation_record={"kind": "workspace_delete", "workspace": record.id},
            )
            if not acquired:
                raise WorkspaceBusyError(reason or "Workspace is busy")

            storages = [
                instance.text_chunks,
                instance.full_docs,
                instance.full_entities,
                instance.full_relations,
                instance.entity_chunks,
                instance.relation_chunks,
                instance.entities_vdb,
                instance.relationships_vdb,
                instance.chunks_vdb,
                instance.chunk_entity_relation_graph,
                instance.doc_status,
            ]
            results = await asyncio.gather(
                *(storage.drop() for storage in storages if storage is not None),
                return_exceptions=True,
            )
            for result in results:
                if isinstance(result, Exception):
                    drop_failures.append(type(result).__name__)
                    logger.error("Workspace deletion storage drop failed: %s", result)
                elif isinstance(result, dict) and result.get("status") != "success":
                    drop_failures.append(type(result).__name__)
                    logger.error(
                        "Workspace deletion storage drop failed: %s",
                        result.get("message", "unknown error"),
                    )
            if drop_failures:
                raise WorkspaceDataDeletionError(
                    "One or more storage backends could not be cleared"
                )

            # Drop the derived LLM cache only after every attribution-carrying
            # store succeeded. On a partial failure the workspace row is kept,
            # and preserving the cache avoids forcing surviving documents to
            # repay extraction work on the retry.
            cache_result = await instance.llm_response_cache.drop()
            if isinstance(cache_result, dict) and cache_result.get("status") != "success":
                raise WorkspaceDataDeletionError(
                    "The LLM response cache could not be cleared"
                )
        finally:
            if acquired:
                await _release_destructive_busy(instance, token)

        working_dir = Path(instance.working_dir).resolve()
        storage_dir = (working_dir / record.namespace).resolve()
        document_manager = self._document_managers.get(record.id)
        input_dir = (
            (Path(document_manager.base_input_dir) / record.namespace).resolve()
            if document_manager is not None and record.namespace
            else None
        )
        for candidate, parent in (
            (storage_dir, working_dir),
            (input_dir, Path(document_manager.base_input_dir).resolve())
            if input_dir is not None
            else (None, None),
        ):
            if candidate is None or parent is None or candidate == parent:
                continue
            if candidate.parent != parent or not candidate.name:
                raise WorkspaceDataDeletionError(
                    "Refusing to remove a workspace directory outside its root"
                )
            if candidate.exists():
                await asyncio.to_thread(shutil.rmtree, candidate)

        try:
            await _await_if_needed(instance.finalize_storages())
        except Exception as exc:
            logger.warning(
                "Workspace %s was cleared but its runtime could not finalize: %s",
                record.id,
                exc,
            )
        async with self._activation_lock:
            self._instances.pop(record.id, None)
            self._document_managers.pop(record.id, None)
            self._initialized.discard(record.id)

    async def finalize_all(self) -> None:
        instances = list(self._instances.values())
        for instance in instances:
            try:
                await _await_if_needed(instance.finalize_storages())
            except Exception as exc:
                logger.error("Failed to finalize a workspace runtime: %s", exc)
        self._instances.clear()
        self._document_managers.clear()
        self._initialized.clear()


class WorkspaceScopeMiddleware:
    """Bind the request's workspace before admission and route handling."""

    def __init__(
        self,
        app,
        *,
        runtime: WorkspaceRuntime | None = None,
        runtime_getter: Callable[[], WorkspaceRuntime] | None = None,
    ) -> None:
        self.app = app
        self._runtime = runtime
        self._runtime_getter = runtime_getter

    def _resolve_runtime(self) -> WorkspaceRuntime:
        if self._runtime is not None:
            return self._runtime
        if self._runtime_getter is None:
            raise WorkspaceRuntimeError("Workspace runtime is not configured")
        return self._runtime_getter()

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        workspace_id = header_value(scope, WORKSPACE_HEADER)
        if workspace_id is not None and len(workspace_id) > 256:
            await send_json(send, 400, "Workspace identifier is too long")
            return
        try:
            runtime = self._resolve_runtime()
            token = await runtime.activate(workspace_id)
        except WorkspaceNotFoundError as exc:
            await send_json(send, 404, str(exc))
            return
        except WorkspaceBusyError as exc:
            await send_json(send, 409, str(exc))
            return
        except WorkspaceRegistryError:
            logger.exception("Could not resolve the requested workspace")
            await send_json(send, 503, "Workspace metadata is unavailable")
            return
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Could not initialize the requested workspace")
            await send_json(send, 500, "Workspace could not be initialized")
            return

        try:
            await self.app(scope, receive, send)
        finally:
            await runtime.release(token)
