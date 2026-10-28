"""Fault-tree ontology and extraction support."""

from lightrag.fault_tree.ontology import OntologyRegistry
from lightrag.fault_tree.graph import GraphProjection, project_candidate_batch
from lightrag.fault_tree.schemas import (
    EvidenceCandidate,
    Expression,
    FaultCandidateBatch,
    FaultEntityPayload,
    FaultRelationPayload,
)
from lightrag.fault_tree.service import configure_fault_tree_validator
from lightrag.fault_tree.validator import FaultCandidateValidator
from lightrag.fault_tree.views import (
    GRAPH_VIEW_IDS,
    GraphViewError,
    build_graph_view,
    get_graph_view,
)

__all__ = [
    "EvidenceCandidate",
    "Expression",
    "FaultCandidateBatch",
    "FaultCandidateValidator",
    "FaultEntityPayload",
    "FaultRelationPayload",
    "GRAPH_VIEW_IDS",
    "GraphViewError",
    "GraphProjection",
    "OntologyRegistry",
    "configure_fault_tree_validator",
    "build_graph_view",
    "get_graph_view",
    "project_candidate_batch",
]
