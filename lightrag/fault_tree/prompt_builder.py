"""Render prompt text from ontology definitions."""

from __future__ import annotations

from typing import Any, Mapping


def render_entity_types_guidance(classes: Mapping[str, Any]) -> str:
    lines: list[str] = []
    for code, definition in classes.items():
        if not isinstance(definition, dict) or not definition.get("prompt_visible"):
            continue
        lines.append(f"- {code}: {definition.get('label', code)}")
        required = definition.get("required") or []
        if required:
            lines.append(f"  必填字段：{', '.join(map(str, required))}")
        properties = definition.get("extract_properties") or {}
        if properties:
            lines.append(f"  可抽取属性：{', '.join(properties)}")
    return "\n".join(lines)


def render_domain_extraction_rules(
    *,
    ontology_version: str,
    classes: Mapping[str, Any],
    relations: Mapping[str, Any],
    instructions: str = "",
) -> str:
    relation_lines: list[str] = []
    for code, definition in relations.items():
        if not isinstance(definition, dict) or not definition.get("prompt_visible"):
            continue
        source = definition.get("source")
        target = definition.get("target")
        source_text = ", ".join(_as_list(source))
        target_text = ", ".join(_as_list(target))
        line = (
            f"- {code}: {source_text or '任意实体'} -> "
            f"{target_text or '任意实体'}"
        )
        properties = definition.get("properties")
        if isinstance(properties, dict) and properties:
            line += f"；可选属性：{', '.join(properties)}"
        relation_lines.append(line)

    sections = [
        "---Domain Extraction Rules---",
        f"Ontology version: {ontology_version}",
        "只提取下方列出的类和关系，不要自行创造正式类型。",
        "",
        "允许抽取的关系：",
        *(relation_lines or ["- 无"]),
        "",
        "只有原文明确陈述时才生成关系。"
        "没有原文证据的关系必须省略。",
        "维修措施、检测动作和操作步骤不是故障原因。",
        "不要自行创造未列出的类型；无法归类时省略该实体或关系。",
        "",
        "因果关系使用 FaultEvent.cause_rule 字段：",
        '- 单原因：{"event_local_id": "<local-id>"}',
        '- OR：{"op": "OR", "children": [<至少两个表达式>]}',
        '- AND：{"op": "AND", "children": [<至少两个表达式>]}',
        "AND/OR 表达式可以递归嵌套。",
        "不要输出正式 UID、Gate UID、页码、Chunk ID 或审核状态。",
        "每个实体和关系必须带 evidence.quote，quote 必须是原文逐字片段。",
    ]
    instructions = instructions.strip()
    if instructions:
        sections.extend(["", instructions])
    return "\n".join(sections).strip()


def _as_list(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(item) for item in value]
    return []
