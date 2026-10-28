# Graph view projection contract

The fault-tree WebUI does not render the whole workspace graph as one network.
It exposes four ontology-bounded projections over the same department
workspace:

| View id | Root | Allowed relations | Purpose |
| --- | --- | --- | --- |
| `department-files` | Department | `OWNS_FILE` | Department-to-file overview |
| `department-equipment` | Department | `HAS_EQUIPMENT` | Department-to-equipment overview |
| `equipment-faults` | Equipment | `HAS_FAULT` | Direct equipment-to-fault incidence |
| `fault-causes` | FaultEvent | `CAUSES`, `HAS_CAUSE_RULE`, `INPUT_OF`, `OUTPUT_TO` | Lazy causal expansion |

`equipment-faults` is deliberately one relation wide. Expanding a selected
fault is a transition to `fault-causes`, not a deeper walk through the generic
graph. `fault-causes` walks only toward causes of its root: `OUTPUT_TO` enters a
gate, `INPUT_OF` enters that gate's inputs, and direct `CAUSES` edges enter
their effect. Rules reachable from the root through `HAS_CAUSE_RULE` are
included as metadata; they do not make the traversal leave the causal edge
set.

`max_depth` has a lower bound of 1 but no separate upper bound. Every view is
bounded by `max_nodes`, so increasing traversal depth cannot bypass the
projection's work and response limits.

The Department node in the first two views is the workspace anchor
(`department:<workspace>`). It is synthesized by the projection instead of
being written as an ordinary entity. G1 derives File nodes from the workspace's
`doc_status` rows, so deleting a document removes it from the next projection
without leaving a separate system edge for purge to clean up. G2 derives its
Equipment nodes from graph nodes whose `class_code`/`entity_type` is
`Equipment`. Neither view trusts an LLM to emit the structural Department edge.

## Presentation boundary

The ontology YAML contains classes, properties, relation domains/ranges,
direction, cardinality and constraints. It does not contain colors, icons,
grouping, layout or which graph tab is open. The four view ids are query
profiles because each one enforces a different relation filter; visual
configuration and layout live in the WebUI.

The `fault-causes` WebUI layout is a deterministic layered tree. A node on
deeper depth is attached to its connected `LogicGate` on the preceding depth
when one exists, so all of that gate's inputs occupy one adjacent horizontal
group and the gate is centred above the group. Nodes that feed several gates
cannot be adjacent to every parent; the layout makes a stable best-effort
choice by node id.

## Storage fields

Validated domain payloads are persisted as backend-safe scalar fields:

- `class_code`
- `canonical_name`
- `instance_uid` when the source supplies one
- `ontology_version`
- `domain_properties_json`
- edges: `relation_code`, `ontology_version`, `relation_properties_json`

Nested domain values use JSON strings because graph backends do not share one
nested-property model. The projection API decodes them into
`domain_properties` and `relation_properties` for the UI. Missing or malformed
JSON is treated as an empty map and does not change graph topology.

## Workspace boundary

A projection loads nodes and edges from one `LightRAG` workspace only. A
department deployed with its own `WORKSPACE` therefore gets its own four views
and cannot traverse into another department's files, equipment, faults or
evidence. A tenant-level department directory, if added later, must remain
separate from these graph projections.

## Current implementation limit

The common graph-storage interface has no typed-edge or class-filter query, so
the MVP calls `get_all_nodes` and `get_all_edges` and filters in one deterministic
projection. This is bounded by `max_nodes`, but the initial storage read is not.
A backend-native query can replace those reads without changing the API shape.
