"""Project validated fault-tree payloads into graph-storage scalar fields."""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from typing import Any

DOMAIN_PROPERTIES_JSON = "domain_properties_json"
RELATION_PROPERTIES_JSON = "relation_properties_json"

_ENTITY_RESERVED_FIELDS = {
    "local_id",
    "class",
    "type",
    "name",
    "description",
    "evidence",
}
_RELATION_RESERVED_FIELDS = {
    "local_id",
    "relation_code",
    "source",
    "target",
    "source_local_id",
    "target_local_id",
    "evidence",
    "model_confidence",
}
_LIST_MERGE_FIELDS = {
    "aliases",
    "symptoms",
    "maintenance_measures",
    "evidence_quotes",
}


def entity_storage_fields(
    records: Iterable[Mapping[str, Any]],
    *,
    existing: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return scalar graph fields for one merged entity.

    The ontology payload is LLM-authored data, so nested domain values are
    stored as one JSON string. Every graph backend accepts a string property;
    keeping nested maps out of the graph property itself avoids backend-specific
    property constraints. Later records win for scalar fields, while
    list-valued fields are unioned.
    """

    properties = _decode_properties(existing, DOMAIN_PROPERTIES_JSON)
    class_code = _string_value((existing or {}).get("class_code"))
    ontology_version = _string_value((existing or {}).get("ontology_version"))
    canonical_name = _string_value((existing or {}).get("canonical_name"))
    instance_uid = _string_value((existing or {}).get("instance_uid"))

    for record in records:
        payload = _payload_from_record(record)
        if not payload:
            continue

        class_code = _string_value(payload.get("class")) or class_code
        ontology_version = (
            _string_value(payload.get("ontology_version")) or ontology_version
        )
        canonical_name = (
            _string_value(payload.get("name"))
            or _string_value(payload.get("canonical_name"))
            or canonical_name
        )
        instance_uid = _string_value(payload.get("uid")) or instance_uid

        nested = payload.get("properties")
        if isinstance(nested, Mapping):
            properties = _merge_properties(properties, nested)

        for key, value in payload.items():
            if key in _ENTITY_RESERVED_FIELDS or key in {
                "properties",
                "ontology_version",
                "uid",
                "canonical_name",
            }:
                continue
            properties = _merge_property(properties, key, value)

        evidence_quotes = [
            quote
            for item in payload.get("evidence", [])
            if isinstance(item, Mapping)
            and isinstance(quote := item.get("quote"), str)
            and quote
        ]
        if evidence_quotes:
            properties = _merge_property(
                properties, "evidence_quotes", evidence_quotes
            )

    fields: dict[str, Any] = {}
    if class_code:
        fields["class_code"] = class_code
    if ontology_version:
        fields["ontology_version"] = ontology_version
    if canonical_name:
        fields["canonical_name"] = canonical_name
    if instance_uid:
        fields["instance_uid"] = instance_uid
    if properties:
        fields[DOMAIN_PROPERTIES_JSON] = _dump_json(properties)
    return fields


def relation_storage_fields(
    records: Iterable[Mapping[str, Any]],
    *,
    existing: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return scalar graph fields for one merged relationship."""

    properties = _decode_properties(existing, RELATION_PROPERTIES_JSON)
    relation_code = _string_value((existing or {}).get("relation_code"))
    ontology_version = _string_value((existing or {}).get("ontology_version"))

    for record in records:
        payload = _payload_from_record(record)
        if not payload:
            continue

        relation_code = (
            _string_value(payload.get("relation_code")) or relation_code
        )
        ontology_version = (
            _string_value(payload.get("ontology_version")) or ontology_version
        )

        confidence = payload.get("model_confidence")
        if isinstance(confidence, (int, float)) and not isinstance(confidence, bool):
            properties = _merge_property(properties, "confidence", confidence)

        for key, value in payload.items():
            if key not in _RELATION_RESERVED_FIELDS:
                properties = _merge_property(properties, key, value)

        evidence_quotes = [
            quote
            for item in payload.get("evidence", [])
            if isinstance(item, Mapping)
            and isinstance(quote := item.get("quote"), str)
            and quote
        ]
        if evidence_quotes:
            properties = _merge_property(
                properties, "evidence_quotes", evidence_quotes
            )

    fields: dict[str, Any] = {}
    if relation_code:
        fields["relation_code"] = relation_code
    if ontology_version:
        fields["ontology_version"] = ontology_version
    if properties:
        fields[RELATION_PROPERTIES_JSON] = _dump_json(properties)
    return fields


def decode_json_property(value: Any) -> dict[str, Any]:
    """Decode a persisted JSON property, returning an empty map on bad data."""

    if isinstance(value, Mapping):
        return dict(value)
    if not isinstance(value, str) or not value:
        return {}
    try:
        decoded = json.loads(value)
    except (TypeError, ValueError):
        return {}
    return dict(decoded) if isinstance(decoded, Mapping) else {}


def _payload_from_record(record: Mapping[str, Any]) -> dict[str, Any]:
    value = record.get("_fault_payload")
    if isinstance(value, Mapping):
        return dict(value)
    return decode_json_property(value)


def _decode_properties(
    existing: Mapping[str, Any] | None, key: str
) -> dict[str, Any]:
    if not existing:
        return {}
    return decode_json_property(existing.get(key))


def _merge_properties(
    current: Mapping[str, Any], updates: Mapping[str, Any]
) -> dict[str, Any]:
    merged = dict(current)
    for key, value in updates.items():
        merged = _merge_property(merged, str(key), value)
    return merged


def _merge_property(
    current: Mapping[str, Any], key: str, value: Any
) -> dict[str, Any]:
    merged = dict(current)
    if key in _LIST_MERGE_FIELDS and isinstance(value, list):
        previous = merged.get(key)
        values = list(previous) if isinstance(previous, list) else []
        for item in value:
            if item not in values:
                values.append(item)
        merged[key] = values
    elif _is_storable(value):
        merged[key] = value
    return merged


def _is_storable(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, (str, int, float, bool)):
        return True
    if isinstance(value, list):
        return all(isinstance(item, (str, int, float, bool)) for item in value)
    if isinstance(value, Mapping):
        return all(isinstance(key, str) for key in value)
    return False


def _string_value(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value or None


def _dump_json(value: Mapping[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
