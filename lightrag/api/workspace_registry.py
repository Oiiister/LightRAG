"""Persistent metadata for named LightRAG workspaces.

The workspace identifier is the storage namespace key.  The user-facing name is
metadata and can change without rewriting any storage backend.  Keeping those
two values separate matters because renaming a namespace is not uniform across
LightRAG's file, relational, graph and vector backends.

See ``docs/design/WorkspaceManagementContract.md`` for the identity, rename and
multi-worker rules.
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
import uuid
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from lightrag.utils import validate_workspace

try:  # POSIX production deployments
    import fcntl
except ImportError:  # pragma: no cover - Windows fallback
    fcntl = None


REGISTRY_VERSION = 1
REGISTRY_FILENAME = ".lightrag_workspaces.json"
MAX_WORKSPACE_NAME_LENGTH = 80


class WorkspaceRegistryError(RuntimeError):
    """Base class for workspace metadata errors."""


class WorkspaceNotFoundError(WorkspaceRegistryError):
    """The requested workspace identifier is not registered."""


class WorkspaceConflictError(WorkspaceRegistryError):
    """A workspace name or identifier conflicts with an existing record."""


class WorkspaceValidationError(WorkspaceRegistryError):
    """The supplied workspace name or identifier is invalid."""


class DefaultWorkspaceDeletionError(WorkspaceRegistryError):
    """The deployment's default workspace cannot be deleted."""


@dataclass(frozen=True)
class WorkspaceRecord:
    """One workspace known to this server."""

    id: str
    name: str
    namespace: str
    is_default: bool
    created_at: str
    updated_at: str

    def public_dict(self) -> dict[str, object]:
        """Return fields safe for API clients.

        ``namespace`` stays internal: clients select workspaces by stable
        identifier and never need to construct storage names themselves.
        """

        payload = asdict(self)
        payload.pop("namespace", None)
        return payload


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_display_name(value: object) -> str:
    """Validate a user-facing workspace name."""

    if not isinstance(value, str):
        raise WorkspaceValidationError("Workspace name must be a string")
    name = " ".join(value.split())
    if not name:
        raise WorkspaceValidationError("Workspace name is required")
    if len(name) > MAX_WORKSPACE_NAME_LENGTH:
        raise WorkspaceValidationError(
            f"Workspace name must be at most {MAX_WORKSPACE_NAME_LENGTH} characters"
        )
    if any(ord(char) < 32 or ord(char) == 127 for char in name):
        raise WorkspaceValidationError(
            "Workspace name must not contain control characters"
        )
    return name


def default_workspace_identifier(namespace: str) -> str:
    """Return the stable public id for the deployment's default workspace."""

    validate_workspace(namespace)
    return namespace or "default"


class WorkspaceRegistry:
    """A small, atomically updated JSON registry.

    The registry is re-read while holding an inter-process file lock on every
    operation.  This keeps multiple Gunicorn workers from overwriting each
    other's workspace metadata.
    """

    def __init__(self, working_dir: str | Path) -> None:
        self.working_dir = Path(working_dir)
        self.path = self.working_dir / REGISTRY_FILENAME
        self.lock_path = self.working_dir / f"{REGISTRY_FILENAME}.lock"
        self._thread_lock = threading.RLock()

    @contextmanager
    def _file_lock(self) -> Iterator[None]:
        self.working_dir.mkdir(parents=True, exist_ok=True)
        with self._thread_lock:
            with self.lock_path.open("a+b") as lock_file:
                if fcntl is not None:
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
                try:
                    yield
                finally:
                    if fcntl is not None:
                        fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

    def _empty_payload(self) -> dict[str, object]:
        return {"version": REGISTRY_VERSION, "workspaces": []}

    def _read_unlocked(self) -> dict[str, object]:
        if not self.path.exists():
            return self._empty_payload()
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise WorkspaceRegistryError(
                f"Workspace registry {self.path.name} is unreadable: {exc}"
            ) from exc
        if not isinstance(payload, dict):
            raise WorkspaceRegistryError("Workspace registry root must be an object")
        version = payload.get("version")
        if version != REGISTRY_VERSION:
            raise WorkspaceRegistryError(
                f"Unsupported workspace registry version: {version!r}"
            )
        workspaces = payload.get("workspaces")
        if not isinstance(workspaces, list):
            raise WorkspaceRegistryError("Workspace registry must contain a list")
        return payload

    def _write_unlocked(self, payload: dict[str, object]) -> None:
        self.working_dir.mkdir(parents=True, exist_ok=True)
        fd, temporary_name = tempfile.mkstemp(
            prefix=f"{REGISTRY_FILENAME}.",
            suffix=".tmp",
            dir=self.working_dir,
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as temporary:
                json.dump(payload, temporary, ensure_ascii=False, indent=2)
                temporary.write("\n")
                temporary.flush()
                os.fsync(temporary.fileno())
            os.replace(temporary_name, self.path)
        except Exception:
            try:
                os.unlink(temporary_name)
            except OSError:
                pass
            raise

    @staticmethod
    def _records(payload: dict[str, object]) -> list[WorkspaceRecord]:
        raw_records = payload.get("workspaces", [])
        records: list[WorkspaceRecord] = []
        for raw in raw_records:
            if not isinstance(raw, dict):
                raise WorkspaceRegistryError(
                    "Workspace registry contains a non-object record"
                )
            try:
                record = WorkspaceRecord(**raw)
                validate_workspace(record.namespace)
            except (TypeError, ValueError) as exc:
                raise WorkspaceRegistryError(
                    f"Workspace registry contains an invalid record: {exc}"
                ) from exc
            records.append(record)
        return records

    @staticmethod
    def _payload(records: list[WorkspaceRecord]) -> dict[str, object]:
        return {
            "version": REGISTRY_VERSION,
            "workspaces": [asdict(record) for record in records],
        }

    def ensure_default(self, namespace: str, name: str | None = None) -> WorkspaceRecord:
        """Create or return the deployment's default workspace record."""

        validate_workspace(namespace)
        workspace_id = default_workspace_identifier(namespace)
        display_name = normalize_display_name(name or namespace or "Default")
        with self._file_lock():
            payload = self._read_unlocked()
            records = self._records(payload)
            for record in records:
                if record.id == workspace_id:
                    if record.namespace != namespace or not record.is_default:
                        updated = WorkspaceRecord(
                            id=record.id,
                            name=record.name,
                            namespace=namespace,
                            is_default=True,
                            created_at=record.created_at,
                            updated_at=_utc_now(),
                        )
                        records[records.index(record)] = updated
                        self._write_unlocked(self._payload(records))
                        return updated
                    return record
            if any(record.namespace == namespace for record in records):
                raise WorkspaceConflictError(
                    f"Workspace identifier {workspace_id!r} is already in use"
                )
            timestamp = _utc_now()
            record = WorkspaceRecord(
                id=workspace_id,
                name=display_name,
                namespace=namespace,
                is_default=True,
                created_at=timestamp,
                updated_at=timestamp,
            )
            records.append(record)
            self._write_unlocked(self._payload(records))
            return record

    def list(self, query: str | None = None) -> list[WorkspaceRecord]:
        """Return workspaces, default first, optionally filtered by text."""

        payload = self._read_unlocked()
        records = self._records(payload)
        normalized_query = (query or "").strip().casefold()
        if normalized_query:
            records = [
                record
                for record in records
                if normalized_query in record.name.casefold()
                or normalized_query in record.id.casefold()
            ]
        return sorted(
            records,
            key=lambda record: (
                not record.is_default,
                record.name.casefold(),
                record.id,
            ),
        )

    def get(self, workspace_id: str) -> WorkspaceRecord:
        with self._file_lock():
            for record in self._records(self._read_unlocked()):
                if record.id == workspace_id:
                    return record
        raise WorkspaceNotFoundError(f"Workspace {workspace_id!r} was not found")

    def create(self, name: object) -> WorkspaceRecord:
        display_name = normalize_display_name(name)
        with self._file_lock():
            records = self._records(self._read_unlocked())
            if any(
                record.name.casefold() == display_name.casefold()
                for record in records
            ):
                raise WorkspaceConflictError(
                    f"A workspace named {display_name!r} already exists"
                )
            timestamp = _utc_now()
            workspace_id = f"ws_{uuid.uuid4().hex}"
            record = WorkspaceRecord(
                id=workspace_id,
                name=display_name,
                namespace=workspace_id,
                is_default=False,
                created_at=timestamp,
                updated_at=timestamp,
            )
            records.append(record)
            self._write_unlocked(self._payload(records))
            return record

    def rename(self, workspace_id: str, name: object) -> WorkspaceRecord:
        display_name = normalize_display_name(name)
        with self._file_lock():
            records = self._records(self._read_unlocked())
            index = next(
                (
                    index
                    for index, record in enumerate(records)
                    if record.id == workspace_id
                ),
                None,
            )
            if index is None:
                raise WorkspaceNotFoundError(
                    f"Workspace {workspace_id!r} was not found"
                )
            if any(
                candidate.id != workspace_id
                and candidate.name.casefold() == display_name.casefold()
                for candidate in records
            ):
                raise WorkspaceConflictError(
                    f"A workspace named {display_name!r} already exists"
                )
            current = records[index]
            updated = WorkspaceRecord(
                id=current.id,
                name=display_name,
                namespace=current.namespace,
                is_default=current.is_default,
                created_at=current.created_at,
                updated_at=_utc_now(),
            )
            records[index] = updated
            self._write_unlocked(self._payload(records))
            return updated

    def remove(self, workspace_id: str) -> WorkspaceRecord:
        with self._file_lock():
            records = self._records(self._read_unlocked())
            index = next(
                (
                    index
                    for index, record in enumerate(records)
                    if record.id == workspace_id
                ),
                None,
            )
            if index is None:
                raise WorkspaceNotFoundError(
                    f"Workspace {workspace_id!r} was not found"
                )
            record = records[index]
            if record.is_default:
                raise DefaultWorkspaceDeletionError(
                    "The default workspace cannot be deleted"
                )
            del records[index]
            self._write_unlocked(self._payload(records))
            return record
