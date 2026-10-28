import json

import pytest

from lightrag.operate import (
    SOURCE_IDS_LIMIT_METHOD_KEEP,
    _merge_edges_then_upsert,
    _merge_nodes_then_upsert,
)
from lightrag.fault_tree.persistence import (
    DOMAIN_PROPERTIES_JSON,
    RELATION_PROPERTIES_JSON,
    entity_storage_fields,
    relation_storage_fields,
)
from lightrag.fault_tree.ontology import OntologyRegistry
from lightrag.fault_tree.views import build_graph_view
from lightrag.utils import Tokenizer, TokenizerInterface


class _CharTokenizer(TokenizerInterface):
    def encode(self, content: str):
        return [ord(char) for char in content]

    def decode(self, tokens):
        return "".join(chr(token) for token in tokens)


class _MemoryGraph:
    def __init__(self):
        self.nodes = {}
        self.edges = {}

    async def get_node(self, name):
        return self.nodes.get(name)

    async def upsert_node(self, name, node_data):
        self.nodes[name] = dict(node_data)

    async def has_edge(self, source, target):
        return (source, target) in self.edges

    async def get_edge(self, source, target):
        return self.edges.get((source, target))

    async def upsert_edge(self, source, target, edge_data):
        self.edges[(source, target)] = dict(edge_data)


def _merge_config():
    return {
        "tokenizer": Tokenizer("dummy", _CharTokenizer()),
        "summary_context_size": 1_000_000,
        "summary_max_tokens": 1_000_000,
        "force_llm_summary_on_merge": 6,
        "source_ids_limit_method": SOURCE_IDS_LIMIT_METHOD_KEEP,
        "max_source_ids_per_entity": 100,
        "max_source_ids_per_relation": 100,
        "max_file_paths": 100,
        "file_path_more_placeholder": "...",
    }


def test_ontology_validates_parent_references_and_cycles(tmp_path):
    profile = tmp_path / "ontology.yml"
    profile.write_text(
        """
ontology_version: test-v1
classes:
  Asset:
    label: Asset
    prompt_visible: false
  Equipment:
    label: Equipment
    parent: Missing
    prompt_visible: true
relations:
  HAS_FAULT:
    source: Equipment
    target: Equipment
""",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="unknown parent"):
        OntologyRegistry.from_file(profile)

    profile.write_text(
        """
ontology_version: test-v1
classes:
  A:
    label: A
    parent: B
    prompt_visible: true
  B:
    label: B
    parent: A
    prompt_visible: true
relations:
  RELATED:
    source: A
    target: B
""",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="contains a cycle"):
        OntologyRegistry.from_file(profile)


def _node(node_id: str, class_code: str, **properties):
    return {
        "id": node_id,
        "entity_id": node_id,
        "entity_type": class_code,
        "class_code": class_code,
        **properties,
    }


def _edge(source: str, relation_code: str, target: str, **properties):
    return {
        "id": f"{source}-{relation_code}-{target}",
        "source": source,
        "target": target,
        "relation_code": relation_code,
        "keywords": relation_code,
        **properties,
    }


def test_entity_and_relation_payloads_become_stable_storage_fields():
    entity_payload = {
        "class": "Equipment",
        "ontology_version": "industrial-fault-v0.2",
        "name": "冷却水泵",
        "equipment_tag": "P-101A",
        "aliases": ["循环泵"],
        "evidence": [{"quote": "冷却水泵 P-101A"}],
    }
    fields = entity_storage_fields(
        [{"_fault_payload": json.dumps(entity_payload, ensure_ascii=False)}]
    )

    assert fields["class_code"] == "Equipment"
    assert fields["canonical_name"] == "冷却水泵"
    assert fields["ontology_version"] == "industrial-fault-v0.2"
    properties = json.loads(fields[DOMAIN_PROPERTIES_JSON])
    assert properties["equipment_tag"] == "P-101A"
    assert properties["aliases"] == ["循环泵"]
    assert properties["evidence_quotes"] == ["冷却水泵 P-101A"]

    relation_fields = relation_storage_fields(
        [
            {
                "_fault_payload": json.dumps(
                    {
                        "relation_code": "HAS_FAULT",
                        "ontology_version": "industrial-fault-v0.2",
                        "model_confidence": 0.9,
                        "evidence": [{"quote": "发生出口压力不足"}],
                    }
                )
            }
        ]
    )
    assert relation_fields["relation_code"] == "HAS_FAULT"
    relation_properties = json.loads(
        relation_fields[RELATION_PROPERTIES_JSON]
    )
    assert relation_properties["confidence"] == 0.9
    assert relation_properties["evidence_quotes"] == ["发生出口压力不足"]


@pytest.mark.offline
@pytest.mark.asyncio
async def test_merge_persists_domain_fields_on_nodes_and_edges():
    graph = _MemoryGraph()
    cfg = _merge_config()
    entity_payload = {
        "class": "Equipment",
        "ontology_version": "industrial-fault-v0.2",
        "name": "冷却水泵",
        "equipment_tag": "P-101A",
        "evidence": [{"quote": "冷却水泵 P-101A"}],
    }
    await _merge_nodes_then_upsert(
        "P-101A",
        [
            {
                "entity_name": "P-101A",
                "entity_type": "Equipment",
                "description": "冷却水泵",
                "source_id": "chunk-1",
                "file_path": "manual.md",
                "timestamp": 1,
                "_fault_payload": json.dumps(
                    entity_payload, ensure_ascii=False
                ),
            }
        ],
        graph,
        None,
        cfg,
    )
    await _merge_nodes_then_upsert(
        "出口压力不足",
        [
            {
                "entity_name": "出口压力不足",
                "entity_type": "FaultEvent",
                "description": "出口压力不足",
                "source_id": "chunk-1",
                "file_path": "manual.md",
                "timestamp": 1,
            }
        ],
        graph,
        None,
        cfg,
    )
    await _merge_edges_then_upsert(
        "P-101A",
        "出口压力不足",
        [
            {
                "weight": 1.0,
                "source_id": "chunk-1",
                "description": "设备发生出口压力不足",
                "keywords": "HAS_FAULT",
                "file_path": "manual.md",
                "timestamp": 1,
                "_fault_payload": json.dumps(
                    {
                        "relation_code": "HAS_FAULT",
                        "ontology_version": "industrial-fault-v0.2",
                        "model_confidence": 0.9,
                    }
                ),
            }
        ],
        graph,
        None,
        None,
        cfg,
    )

    stored_node = graph.nodes["P-101A"]
    assert stored_node["class_code"] == "Equipment"
    assert stored_node["canonical_name"] == "冷却水泵"
    assert json.loads(stored_node[DOMAIN_PROPERTIES_JSON])["equipment_tag"] == (
        "P-101A"
    )
    stored_edge = graph.edges[("P-101A", "出口压力不足")]
    assert stored_edge["relation_code"] == "HAS_FAULT"
    assert json.loads(stored_edge[RELATION_PROPERTIES_JSON])["confidence"] == 0.9


def test_workspace_views_synthesize_department_without_persisting_edges():
    nodes = [
        _node("D1", "Department"),
        _node("E1", "Equipment"),
        _node("F1", "FaultEvent"),
        _node("FILE1", "File"),
    ]
    edges = [
        # The storage layer may return an edge in either physical orientation.
        _edge("E1", "HAS_EQUIPMENT", "D1"),
        _edge("E1", "HAS_FAULT", "F1"),
        _edge("F1", "CAUSES", "F1"),
        _edge("D1", "OWNS_FILE", "FILE1"),
    ]

    equipment_view = build_graph_view(
        nodes,
        edges,
        view_id="department-equipment",
        max_nodes=100,
        workspace="dept_utility",
    )
    assert {node["id"] for node in equipment_view["nodes"]} == {
        "department:dept_utility",
        "E1",
    }
    assert [edge["type"] for edge in equipment_view["edges"]] == ["HAS_EQUIPMENT"]
    assert equipment_view["edges"][0]["source"] == "department:dept_utility"
    assert equipment_view["edges"][0]["target"] == "E1"

    equipment_faults = build_graph_view(
        nodes,
        edges,
        view_id="equipment-faults",
        root="E1",
        max_nodes=100,
    )
    assert {node["id"] for node in equipment_faults["nodes"]} == {"E1", "F1"}
    assert {edge["type"] for edge in equipment_faults["edges"]} == {"HAS_FAULT"}

    files_view = build_graph_view(
        [],
        [],
        documents=[
            {
                "id": "doc-1",
                "file_path": "manual.md",
                "status": "processed",
                "chunks_count": 4,
            }
        ],
        view_id="department-files",
        max_nodes=100,
        workspace="dept_utility",
    )
    assert {node["id"] for node in files_view["nodes"]} == {
        "department:dept_utility",
        "file:doc-1",
    }
    assert files_view["edges"][0]["type"] == "OWNS_FILE"


def test_fault_causes_expands_only_causal_edges_to_the_requested_depth():
    nodes = [
        _node("CAUSE", "FaultEvent"),
        _node("GATE", "LogicGate"),
        _node("EFFECT", "FaultEvent"),
        _node("RULE", "FaultCauseRule"),
        _node("UNRELATED", "FaultEvent"),
    ]
    edges = [
        _edge("CAUSE", "INPUT_OF", "GATE"),
        _edge("GATE", "OUTPUT_TO", "EFFECT"),
        _edge("EFFECT", "HAS_CAUSE_RULE", "RULE"),
        _edge("EFFECT", "HAS_FAULT", "UNRELATED"),
    ]

    depth_one = build_graph_view(
        nodes,
        edges,
        view_id="fault-causes",
        root="EFFECT",
        max_depth=1,
        max_nodes=100,
    )
    assert {node["id"] for node in depth_one["nodes"]} == {
        "EFFECT",
        "GATE",
        "RULE",
    }
    assert depth_one["is_truncated"] is True

    depth_two = build_graph_view(
        nodes,
        edges,
        view_id="fault-causes",
        root="EFFECT",
        max_depth=2,
        max_nodes=100,
    )
    assert {node["id"] for node in depth_two["nodes"]} == {
        "CAUSE",
        "EFFECT",
        "GATE",
        "RULE",
    }
    assert "UNRELATED" not in {node["id"] for node in depth_two["nodes"]}
    assert {edge["type"] for edge in depth_two["edges"]} == {
        "HAS_CAUSE_RULE",
        "INPUT_OF",
        "OUTPUT_TO",
    }
