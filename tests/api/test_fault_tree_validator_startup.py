from pathlib import Path
from types import SimpleNamespace

import pytest

from lightrag.fault_tree import (
    FaultCandidateValidator,
    configure_fault_tree_validator,
)


def _prompt_root() -> Path:
    return Path(__file__).resolve().parents[2] / "prompts"


@pytest.mark.offline
def test_domain_profile_enables_fault_validator(monkeypatch):
    monkeypatch.setenv("PROMPT_DIR", str(_prompt_root()))
    rag = SimpleNamespace(
        addon_params={"entity_type_prompt_file": "industrial_fault.yml"},
        entity_extraction_use_json=True,
        kg_extraction_validator=None,
    )

    validator = configure_fault_tree_validator(rag)

    assert isinstance(validator, FaultCandidateValidator)
    assert rag.kg_extraction_validator is validator


@pytest.mark.offline
def test_generic_profile_does_not_enable_fault_validator(
    monkeypatch,
    tmp_path,
):
    profile_dir = tmp_path / "entity_type"
    profile_dir.mkdir()
    (profile_dir / "generic.yml").write_text(
        "entity_types_guidance: |\n"
        "  - Thing: generic\n"
        "entity_extraction_json_examples:\n"
        "  - |\n"
        '    {"entities": [], "relationships": []}\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("PROMPT_DIR", str(tmp_path))
    rag = SimpleNamespace(
        addon_params={"entity_type_prompt_file": "generic.yml"},
        entity_extraction_use_json=True,
        kg_extraction_validator=None,
    )

    assert configure_fault_tree_validator(rag) is None
    assert rag.kg_extraction_validator is None


@pytest.mark.offline
def test_domain_profile_requires_json_extraction(monkeypatch):
    monkeypatch.setenv("PROMPT_DIR", str(_prompt_root()))
    rag = SimpleNamespace(
        addon_params={"entity_type_prompt_file": "industrial_fault.yml"},
        entity_extraction_use_json=False,
        kg_extraction_validator=None,
    )

    with pytest.raises(SystemExit, match="ENTITY_EXTRACTION_USE_JSON"):
        configure_fault_tree_validator(rag)
