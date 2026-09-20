from dataclasses import dataclass
from typing import Hashable, Iterable, Mapping, Sequence


@dataclass(frozen=True)
class PartitionAudit:
    proven: bool
    uncovered_states: tuple[Hashable, ...]
    overlapping_states: tuple[Hashable, ...]
    unknown_outcomes: tuple[str, ...]


def audit_settlement_partition(
    states: Iterable[Hashable],
    outcome_states: Mapping[str, Iterable[Hashable]],
    *,
    required_outcomes: Sequence[str] | None = None,
) -> PartitionAudit:
    """Fail-closed proof that every allowed settlement state maps to exactly one outcome."""
    state_set = set(states)
    memberships: dict[Hashable, int] = {state: 0 for state in state_set}
    unknown: set[str] = set()

    if required_outcomes is not None:
        unknown.update(set(outcome_states) - set(required_outcomes))
        unknown.update(set(required_outcomes) - set(outcome_states))

    for outcome, covered in outcome_states.items():
        for state in set(covered):
            if state not in state_set:
                unknown.add(outcome)
                continue
            memberships[state] += 1

    uncovered = tuple(sorted((s for s, n in memberships.items() if n == 0), key=repr))
    overlapping = tuple(sorted((s for s, n in memberships.items() if n > 1), key=repr))
    unknown_outcomes = tuple(sorted(unknown))
    return PartitionAudit(
        proven=not uncovered and not overlapping and not unknown_outcomes,
        uncovered_states=uncovered,
        overlapping_states=overlapping,
        unknown_outcomes=unknown_outcomes,
    )
