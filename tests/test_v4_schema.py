from __future__ import annotations

import copy

import pytest
from jsonschema import FormatChecker
from jsonschema.validators import validator_for

from runtime.models import RuntimeEventType
from runtime.validators import (
    RuntimeContractValidationError,
    validate_cross_references,
    validate_schema,
)


def make_validator(schema):
    cls = validator_for(schema)
    cls.check_schema(schema)
    return cls(schema, format_checker=FormatChecker())


def test_runtime_contract_positive_fixtures_validate(read_json):
    schema = read_json("schema/skill-runtime-contract.schema.json")
    validator = make_validator(schema)
    for name in [
        "examples/runtime-contract.read-only.json",
        "examples/runtime-contract.auto-rollback.json",
        "examples/runtime-contract.manual-approval.json",
    ]:
        errors = list(validator.iter_errors(read_json(name)))
        assert errors == [], [error.message for error in errors]


def test_runtime_contract_negative_fixtures_are_rejected(root, read_json):
    schema = read_json("schema/skill-runtime-contract.schema.json")
    validator = make_validator(schema)
    fixtures = sorted((root / "examples").glob("runtime-contract.*.invalid.json"))
    assert fixtures, "negative fixtures must exist"
    for path in fixtures:
        document = read_json(str(path.relative_to(root)))
        errors = list(validator.iter_errors(document))
        assert errors, f"expected invalid fixture to be rejected: {path.name}"


def test_supporting_schema_fixtures_validate(read_json):
    pairs = [
        ("schema/runtime-event.schema.json", "examples/runtime-event.valid.json"),
        ("schema/evidence-summary.schema.json", "examples/evidence-summary.valid.json"),
        (
            "schema/runtime-run-evidence.schema.json",
            "examples/runtime-run-evidence.valid.json",
        ),
        ("schema/prompt-manifest.schema.json", "examples/prompt-manifest.valid.json"),
    ]
    for schema_name, fixture_name in pairs:
        validate_schema(read_json(fixture_name), read_json(schema_name))


def test_action_id_is_role_based_not_suffix_based(read_json):
    schema = read_json("schema/skill-runtime-contract.schema.json")
    document = read_json("examples/runtime-contract.auto-rollback.json")
    # a_002 is valid because role=compensation carries the semantics; a suffix
    # convention is optional and must not be baked into the identifier grammar.
    assert list(make_validator(schema).iter_errors(document)) == []
    assert document["action_bindings"][1]["action_id"] == "a_002"
    assert document["action_bindings"][1]["role"] == "compensation"


def test_destructive_write_requires_true_approval_flag(read_json):
    schema = read_json("schema/skill-runtime-contract.schema.json")
    document = read_json("examples/runtime-contract.manual-approval.json")
    del document["action_bindings"][0]["risk"]["approval_required"]
    assert list(make_validator(schema).iter_errors(document))


def test_cross_reference_validation_accepts_complete_read_only_contract(read_json):
    contract = read_json("examples/runtime-contract.read-only.json")
    skill = {
        "decomposition": {
            "actions": [{"id": "a_001"}],
            "rules": [{"id": "r_001"}],
            "directives": [{"id": "d_001"}],
        }
    }
    validate_cross_references(skill, contract)


def test_cross_reference_rejects_missing_compensation_binding(read_json):
    contract = read_json("examples/runtime-contract.auto-rollback.json")
    contract["action_bindings"] = [contract["action_bindings"][0]]
    skill = {
        "decomposition": {
            "actions": [{"id": "a_001"}, {"id": "a_002"}],
            "rules": [{"id": "r_001"}, {"id": "r_002"}],
            "directives": [{"id": "d_001"}, {"id": "d_002"}],
        }
    }
    with pytest.raises(RuntimeContractValidationError, match="no runtime binding"):
        validate_cross_references(skill, contract)


def test_cross_reference_requires_compensation_role(read_json):
    contract = read_json("examples/runtime-contract.auto-rollback.json")
    contract["action_bindings"][1]["role"] = "primary"
    skill = {
        "decomposition": {
            "actions": [{"id": "a_001"}, {"id": "a_002"}],
            "rules": [{"id": "r_001"}, {"id": "r_002"}],
            "directives": [{"id": "d_001"}, {"id": "d_002"}],
        }
    }
    with pytest.raises(RuntimeContractValidationError, match="role=compensation"):
        validate_cross_references(skill, contract)


def test_cross_reference_rejects_duplicate_binding_and_manifest_overlap(read_json):
    contract = read_json("examples/runtime-contract.read-only.json")
    contract["action_bindings"].append(copy.deepcopy(contract["action_bindings"][0]))
    contract["directive_manifest"]["exclude"] = ["d_001"]
    skill = {
        "decomposition": {
            "actions": [{"id": "a_001"}],
            "rules": [{"id": "r_001"}],
            "directives": [{"id": "d_001"}],
        }
    }
    with pytest.raises(RuntimeContractValidationError) as error:
        validate_cross_references(skill, contract)
    assert "Duplicate Action bindings" in str(error.value)
    assert "both include and exclude" in str(error.value)


def test_runtime_event_schema_enum_matches_runtime_model(read_json):
    schema = read_json("schema/runtime-event.schema.json")
    schema_events = set(schema["properties"]["event_type"]["enum"])
    model_events = {event.value for event in RuntimeEventType}
    assert schema_events == model_events
