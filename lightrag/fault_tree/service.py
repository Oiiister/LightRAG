"""Service-layer configuration for fault-tree extraction."""

from __future__ import annotations

from lightrag.fault_tree.ontology import OntologyRegistry
from lightrag.fault_tree.validator import FaultCandidateValidator
from lightrag.prompt import resolve_entity_type_prompt_path
from lightrag.utils import logger


def configure_fault_tree_validator(rag):
    """Enable domain validation when the selected prompt profile defines one.

    A profile that only overrides entity labels/examples keeps the existing
    extraction behaviour. A profile containing ``classes`` and ``relations``
    opts into the fault-tree validator, which requires JSON extraction so the
    structured payload is available.
    """

    profile_name = str(
        (getattr(rag, "addon_params", None) or {}).get(
            "entity_type_prompt_file", ""
        )
    ).strip()
    if not profile_name:
        return None

    profile_path = resolve_entity_type_prompt_path(profile_name)
    if not OntologyRegistry.has_ontology_definition(profile_path):
        return None
    if not rag.entity_extraction_use_json:
        raise SystemExit(
            f"ENTITY_TYPE_PROMPT_FILE '{profile_name}' defines ontology classes "
            "and relations; ENTITY_EXTRACTION_USE_JSON must be true for "
            "fault-tree extraction."
        )

    validator = FaultCandidateValidator.from_prompt_profile(profile_name)
    rag.kg_extraction_validator = validator
    logger.info(
        "Fault-tree extraction enabled with ontology profile '%s'",
        profile_name,
    )
    return validator
