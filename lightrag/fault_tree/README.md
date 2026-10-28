# Fault-tree ontology integration

This package adds a fault-tree profile on top of the existing LightRAG JSON
entity extraction pipeline. It does not replace `extract_entities`,
`merge_nodes_and_edges`, the LLM cache, or the graph storage backends.

## Components

- `../../prompts/entity_type/industrial_fault.yml`: ontology classes,
  prompt-visible properties and relations, plus JSON extraction examples.
- `schemas.py`: Pydantic contracts used to validate domain payloads.
- `ontology.py`: loads the profile and validates relation domains and ranges.
- `validator.py`: consumes the parser payload, verifies evidence and relation
  endpoints, and optionally emits a normalized candidate batch.
- `graph.py`: projects validated candidates into `Equipment`, `FaultEvent`,
  `FaultCauseRule`, and `LogicGate` graph records.

## Configuration

```python
from lightrag import LightRAG
from lightrag.fault_tree import FaultCandidateValidator

validator = FaultCandidateValidator.from_prompt_profile(
    "industrial_fault.yml"
)

rag = LightRAG(
    ...,
    entity_extraction_use_json=True,
    addon_params={"entity_type_prompt_file": "industrial_fault.yml"},
    kg_extraction_validator=validator,
)
```

`PROMPT_DIR` defaults to `./prompts`, so the profile is resolved from
`prompts/entity_type/industrial_fault.yml`.

## Extraction payload

The existing JSON extraction format remains unchanged. Domain fields are
preserved in a scalar `_fault_payload` on each entity or relationship:

```json
{
  "local_id": "e2",
  "class": "FaultEvent",
  "cause_rule": {"event_local_id": "e1"},
  "evidence": [{"quote": "过滤器堵塞会造成出口压力不足"}]
}
```

The validator removes invalid entities or relations, verifies that evidence
quotes occur verbatim in the chunk, and checks relation endpoint classes.
Valid relation codes are prepended to the existing edge ``keywords`` field, so
the current WebUI graph can display values such as
``HAS_FAULT, 设备故障``.

``CAUSES`` relations may include ``gate_type_hint`` and ``gate_key``. The
validator projects them into a deterministic ``LogicGate`` node plus
``INPUT_OF`` and ``OUTPUT_TO`` edges. The gate name is derived from the target
fault and gate key, not the chunk ID, so branches discovered in different
chunks accumulate on the same gate in the current graph.

## Graph projection

```python
from lightrag.fault_tree import project_candidate_batch

graph = project_candidate_batch(candidate_batch)
```

The result contains property-graph-shaped nodes and edges, including nested
gates for expressions such as:

```text
(A OR B) AND (C OR D) -> E
```

The projection is a pure data transformation. A deployment adapter remains
responsible for writing it to PostgreSQL or a graph database.

## WebUI projections

The persisted workspace graph is exposed as four bounded views:

- `department-files` (`OWNS_FILE`)
- `department-equipment` (`HAS_EQUIPMENT`)
- `equipment-faults` (`HAS_FAULT`, one hop)
- `fault-causes` (`CAUSES`, `HAS_CAUSE_RULE`, `INPUT_OF`, `OUTPUT_TO`, lazy causal
  expansion from one selected fault)

The full contract is
[`docs/design/GraphViewProjectionContract.md`](../../docs/design/GraphViewProjectionContract.md).
Domain classes and relations stay in the ontology profile; colors, layouts and
the active view stay in the WebUI.

Validated entity and relation properties are persisted as
`domain_properties_json` / `relation_properties_json` plus `class_code`,
`canonical_name`, `relation_code` and `ontology_version`. This keeps graph
backends on scalar properties while allowing the projection API to expose the
decoded maps for node and edge detail panels.
