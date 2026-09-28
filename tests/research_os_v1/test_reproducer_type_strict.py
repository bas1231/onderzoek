import pytest

from control.research_os_v1.reproducer import build_packet, source_independence


def test_reproducer_rejects_non_string_candidate_id():
    with pytest.raises(ValueError, match="candidate_id_required"):
        build_packet({"candidate_id": 123}, "question")


def test_reproducer_rejects_string_where_evidence_list_required():
    with pytest.raises(ValueError, match="supporting_evidence_must_be_list"):
        build_packet(
            {
                "candidate_id": "C1",
                "supporting_evidence": "raw/a.json",
            },
            "question",
        )


def test_reproducer_rejects_malformed_lineage_value():
    with pytest.raises(ValueError, match="invalid_evidence_lineage"):
        build_packet(
            {
                "candidate_id": "C1",
                "supporting_evidence": [
                    {
                        "ref": "raw/a.json",
                        "upstream_source_ids": ["official:a", 42],
                    }
                ],
            },
            "question",
        )


def test_reproducer_rejects_non_object_required_gates():
    with pytest.raises(ValueError, match="required_gates_must_be_object"):
        build_packet(
            {"candidate_id": "C1", "required_gates": ["PASS"]},
            "question",
        )


def test_source_independence_rejects_non_reference_items():
    with pytest.raises(ValueError, match="source_reference_must_be_string_or_object"):
        source_independence([123], [{"ref": "b", "upstream_source_ids": ["u:b"]}])


def test_shared_primary_source_is_not_independent_even_with_different_refs():
    origin = [
        {
            "ref": "derived:a",
            "source_id": "official:shared",
            "is_primary_source": True,
        }
    ]
    reproduction = [
        {
            "ref": "derived:b",
            "source_id": "official:shared",
            "is_primary_source": True,
        }
    ]
    result = source_independence(origin, reproduction)
    assert result["status"] == "SHARED_UPSTREAM"
    assert result["counts_as_independent_reproduction"] is False
