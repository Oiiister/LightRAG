"""Schemas for fault-tree extraction candidates."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class EvidenceCandidate(BaseModel):
    """A verbatim source fragment supplied by the extractor."""

    quote: str = Field(min_length=1)


class Expression(BaseModel):
    """A recursive fault-cause expression.

    A leaf references another fault event in the same chunk. An internal node
    contains at least two child expressions. The effect event is not part of
    this tree; it is supplied separately by the owning rule.
    """

    op: Literal["AND", "OR"] | None = None
    event_local_id: str | None = None
    children: list["Expression"] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_shape(self) -> "Expression":
        has_event = bool(self.event_local_id and self.event_local_id.strip())
        has_operator = self.op is not None
        if has_event == has_operator:
            raise ValueError(
                "expression must contain exactly one of event_local_id or op"
            )
        if has_operator and len(self.children) < 2:
            raise ValueError("AND/OR expressions require at least two children")
        if has_event and self.children:
            raise ValueError("event leaves cannot contain children")
        return self


class FaultEntityPayload(BaseModel):
    """Domain fields emitted alongside a LightRAG JSON entity."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    local_id: str = Field(min_length=1)
    class_name: str = Field(alias="class", min_length=1)
    ontology_version: str | None = None
    aliases: list[str] = Field(default_factory=list)
    properties: dict[str, Any] = Field(default_factory=dict)
    cause_rule: Expression | None = None
    evidence: list[EvidenceCandidate] = Field(default_factory=list)


class FaultRelationPayload(BaseModel):
    """Domain fields emitted alongside a LightRAG JSON relationship."""

    local_id: str | None = None
    relation_code: str = Field(min_length=1)
    ontology_version: str | None = None
    source_ref: str | None = Field(default=None, alias="source")
    target_ref: str | None = Field(default=None, alias="target")
    source_local_id: str | None = None
    target_local_id: str | None = None
    gate_type_hint: Literal["AND", "OR"] | None = None
    gate_key: str | None = None
    evidence: list[EvidenceCandidate] = Field(default_factory=list)
    model_confidence: float | None = Field(default=None, ge=0, le=1)

    @model_validator(mode="after")
    def validate_gate_group(self) -> "FaultRelationPayload":
        if self.gate_type_hint and not (self.gate_key or "").strip():
            raise ValueError("gate_key is required when gate_type_hint is set")
        return self


class FaultCandidateBatch(BaseModel):
    """Validated candidates produced from one source chunk."""

    chunk_id: str
    entities: list[FaultEntityPayload] = Field(default_factory=list)
    relations: list[FaultRelationPayload] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


Expression.model_rebuild()
