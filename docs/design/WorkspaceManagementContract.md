# Workspace Management Contract

This contract covers the named workspaces exposed by the admin WebUI. It does
not describe the `/workspace` query-only frontend entry; that URL and a storage
workspace are unrelated concepts.

## Identity

Each workspace has two values:

- `id` is a stable ASCII identifier used in `LIGHTRAG-WORKSPACE` and in every
  storage namespace.
- `name` is editable display metadata.

Rename updates only `name`. It deliberately does not migrate data between
storage namespaces: file directories, relational tables, graph labels and
vector collections do not share a rename primitive, and a best-effort rename
across them would be non-atomic.

The deployment's default workspace also has a stable public id:

- A non-empty `WORKSPACE` setting uses that value.
- An empty `WORKSPACE` setting uses `default`.

The public `default` id maps to the empty physical namespace, so existing
deployments keep their current files and database rows.

## Request Isolation

`WorkspaceScopeMiddleware` resolves `LIGHTRAG-WORKSPACE` before admission
control and all business routes. It binds one initialized `LightRAG` instance
and one `DocumentManager` to the request through a context variable.

The scoped `LightRAG` instance carries the same configuration into all four
storage categories:

- KV: full documents, chunks, attribution anchors and LLM cache
- vector: entities, relations and chunks
- graph: entities and relations
- document status: ingestion and recovery state

That set also includes pipeline status, ingress mailboxes and workspace locks,
which are namespaced by the same workspace value.

The `DocumentManager` uses `<INPUT_DIR>/<namespace>/` for uploads, parsed
artifacts and scan spools. Switching the header therefore changes document
listings, uploads, graph reads and edits, retrieval, pipeline state and health
reporting together.

The admin WebUI's retrieval history is stored under a workspace-specific local
key. This prevents one workspace's conversation from becoming the
`conversation_history` sent with a query in another workspace. The default
workspace keeps the original history key for backward compatibility.

The WebUI also clears its graph store and selected entity before switching, and
remounts the document, graph and retrieval views. This prevents the previous
workspace's canvas, filters or in-flight query state from being displayed while
the new workspace loads.

There is no frontend-only filtering step. A caller that omits the header gets
the deployment's default workspace. A header naming an unregistered workspace
is rejected before any route runs.

## Concurrent Requests

The runtime tracks in-flight requests per workspace. A delete marks the
workspace as deleting, rejects new requests, and waits for other in-flight
requests to release it before dropping storage. The delete request itself is
excluded from that count.

The pipeline's shared `busy` / `destructive_busy` reservation is still acquired
for the drop. This rejects scans, uploads and admin graph writes that were not
using the runtime's request counter, including requests handled by another
worker.

## Deletion

Deletion uses the storages' public `drop()` operations. It never deletes a
directory or unregisters the workspace before the attribution-carrying stores
report success.

Ordering:

1. Resolve and initialize the instance.
2. Mark the workspace deleting and wait for in-flight requests.
3. Acquire the pipeline destructive reservation.
4. Drop document, chunk, graph, vector, anchor, status and cache namespaces.
5. Remove workspace-owned input and file-backed storage directories.
6. Finalize the instance.
7. Remove registry metadata.

If a storage drop fails, the registry row is retained and the operation can be
retried. If file removal fails after all stores were cleared, the row is also
retained; a retry operates on empty stores and removes the remaining files.
Both residues keep a discoverable workspace record rather than hiding partial
destruction behind a successful delete response.

The LLM response cache is dropped only after every attribution-carrying store
has succeeded. If any earlier drop fails, the cache is preserved so a retry of
the surviving documents does not have to repay extraction calls.

The default workspace cannot be deleted. Its display name can be changed.

## Multi-Worker Boundary

Registry updates are serialized with a file lock and published by atomic file
replacement, so workers do not overwrite each other's metadata. Each worker
lazily owns its own initialized instances.

After a workspace is deleted, another worker may retain an idle in-memory
instance until that worker handles a request for the now-unregistered id. New
requests are rejected by registry lookup, so the stale instance is not
reachable. Requests that had already entered a worker before deletion are the
reason deletion waits on the shared destructive reservation and rejects admin
writes; read-only work may finish before the response returns.

Workspace ids are random and are never reused. Shared in-memory helpers such as
`pipeline_status`, ingress mailboxes and scan-job records may therefore retain
an unreachable, empty entry until process shutdown. Cleaning only the local
worker's map would be worse in a multi-worker deployment: another worker could
still hold the live entry. Process restart is the recovery path for this bounded
residue.
