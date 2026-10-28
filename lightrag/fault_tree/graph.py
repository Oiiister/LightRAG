"""Project validated fault candidates into a property-graph representation."""

from __future__ import annotations

import hashlib
from typing import Any, Callable

from pydantic import BaseModel, Field

from lightrag.fault_tree.schemas import Expression, FaultCandidateBatch


class GraphProjection(BaseModel):
    nodes: list[dict[str, Any]] = Field(default_factory=list)
    edges: list[dict[str, Any]] = Field(default_factory=list)


def project_candidate_batch(
    batch: FaultCandidateBatch,
    resolve_uid: Callable[[str, str], str] | None = None,
) -> GraphProjection:
    """Turn validated candidates into graph-shaped nodes and edges.

    ``resolve_uid`` maps ``(class_code, local_id)`` to the durable ID used by
    the target graph store. Without a resolver the local ID is retained, which
    is useful for previews and tests.
    """

    resolve_uid = resolve_uid or (lambda _class_code, local_id: local_id)
    projection = GraphProjection()
    local_to_uid: dict[str, str] = {}

    for entity in batch.entities:
        uid = resolve_uid(entity.class_name, entity.local_id)
        local_to_uid[entity.local_id] = uid
        properties = dict(entity.properties)
        for field_name, value in entity.model_extra.items():
            if field_name not in {"local_id", "class", "properties", "evidence"}:
                properties[field_name] = value
        properties["canonical_name"] = (
            properties.get("name")
            or properties.get("canonical_name")
            or entity.local_id
        )
        if entity.ontology_version:
            properties["ontology_version"] = entity.ontology_version
        properties["evidence_quotes"] = [
            item.quote for item in entity.evidence
        ]
        projection.nodes.append(
            {
                "label": entity.class_name,
                "uid": uid,
                "properties": properties,
            }
        )

    for relation in batch.relations:
        if not relation.source_local_id or not relation.target_local_id:
            continue
        projection.edges.append(
            {
                "type": relation.relation_code,
                "source_uid": local_to_uid[relation.source_local_id],
                "target_uid": local_to_uid[relation.target_local_id],
                "properties": {
                    "confidence": relation.model_confidence,
                    "ontology_version": relation.ontology_version,
                    "evidence_quotes": [
                        item.quote for item in relation.evidence
                    ],
                },
            }
        )

    for entity in batch.entities:
        if entity.cause_rule is None:
            continue
        effect_uid = local_to_uid[entity.local_id]
        rule_uid = _stable_id("rule", batch.chunk_id, entity.local_id)
        projection.nodes.append(
            {
                "label": "FaultCauseRule",
                "uid": rule_uid,
                "properties": {
                    "effect_fault_uid": effect_uid,
                    "expression": entity.cause_rule.model_dump(exclude_none=True),
                    "evidence_quotes": [
                        item.quote for item in entity.evidence
                    ],
                },
            }
        )
        projection.edges.append(
            {
                "type": "HAS_CAUSE_RULE",
                "source_uid": effect_uid,
                "target_uid": rule_uid,
                "properties": {},
            }
        )
        _append_expression(
            projection=projection,
            expression=entity.cause_rule,
            effect_uid=effect_uid,
            rule_uid=rule_uid,
            local_to_uid=local_to_uid,
            path="root",
        )

    return projection


def _append_expression(
    *,
    projection: GraphProjection,
    expression: Expression,
    effect_uid: str,
    rule_uid: str,
    local_to_uid: dict[str, str],
    path: str,
) -> str | None:
    if expression.event_local_id:
        source_uid = local_to_uid[expression.event_local_id]
        projection.edges.append(
            {
                "type": "CAUSES",
                "source_uid": source_uid,
                "target_uid": effect_uid,
                "properties": {"rule_uid": rule_uid},
            }
        )
        return source_uid

    assert expression.op is not None
    gate_uid = _stable_id("gate", rule_uid, path, expression.op)
    projection.nodes.append(
        {
            "label": "LogicGate",
            "uid": gate_uid,
            "properties": {
                "gate_type": expression.op,
                "rule_uid": rule_uid,
                "input_count": len(expression.children),
            },
        }
    )
    for index, child in enumerate(expression.children):
        child_uid = _append_expression(
            projection=projection,
            expression=child,
            effect_uid=effect_uid,
            rule_uid=rule_uid,
            local_to_uid=local_to_uid,
            path=f"{path}.{index}",
        )
        if child_uid is not None:
            projection.edges.append(
                {
                    "type": "INPUT_OF",
                    "source_uid": child_uid,
                    "target_uid": gate_uid,
                    "properties": {},
                }
            )

    if path == "root":
        projection.edges.append(
            {
                "type": "OUTPUT_TO",
                "source_uid": gate_uid,
                "target_uid": effect_uid,
                "properties": {},
            }
        )
    return gate_uid


def _stable_id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha1("\x1f".join(parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"
