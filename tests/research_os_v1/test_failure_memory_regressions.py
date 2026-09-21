import pytest

from control.research_os_v1.failure_memory import pattern_index, required_checks


def valid_memory():
    return {
        "schema_version": 1,
        "patterns": [{
            "id": "FP-X",
            "name": "TEST",
            "gate": "PROCESS",
            "trigger": "trigger",
            "required_check": "check",
            "default_effect": "BLOCK",
        }],
    }


def test_malformed_pattern_is_not_silently_skipped():
    obj = valid_memory()
    del obj["patterns"][0]["required_check"]
    with pytest.raises(ValueError, match="failure_pattern_fields_missing"):
        pattern_index(obj)


def test_wrong_failure_memory_schema_fails_closed():
    obj = valid_memory()
    obj["schema_version"] = 999
    with pytest.raises(ValueError, match="unsupported_failure_memory_schema_version"):
        pattern_index(obj)


def test_failure_pattern_ids_must_be_list_not_string():
    with pytest.raises(ValueError, match="failure_pattern_ids_must_be_list"):
        required_checks("FP-X", valid_memory())


def test_blank_failure_pattern_id_is_rejected():
    with pytest.raises(ValueError, match="failure_pattern_id_invalid"):
        required_checks([""], valid_memory())
