from control.research_os_v1.governor import classify


def test_truthy_integer_cannot_impersonate_provenance_boolean():
    result = classify({
        "kind": "free_public_read_only_research",
        "provenance": 1,
        "point_in_time": True,
    })
    assert result.admissible is False
    assert "provenance" in result.reason


def test_truthy_integer_cannot_impersonate_point_in_time_boolean():
    result = classify({
        "kind": "free_public_read_only_research",
        "provenance": True,
        "point_in_time": 1,
    })
    assert result.admissible is False
    assert "point_in_time" in result.reason


def test_numeric_action_kind_is_invalid_not_stringified():
    result = classify({"kind": 123})
    assert result.admissible is False
    assert result.reason == "missing_or_invalid_action_kind"


def test_numeric_branch_cannot_satisfy_non_main_branch_requirement():
    result = classify({
        "kind": "git_write_to_shadow_spec_branch_without_secrets",
        "branch": 123,
        "contains_secrets": False,
    })
    assert result.admissible is False
    assert "branch_is_not_main" in result.reason


def test_valid_read_only_research_remains_allowed():
    result = classify({
        "kind": "free_public_read_only_research",
        "provenance": True,
        "point_in_time": True,
    })
    assert result.admissible is True
