from control.lib.settlement_partition_gate import audit_settlement_partition


def check(name, condition):
    if not condition:
        raise AssertionError(name)
    print('PASS', name)


# Exact three-way partition.
a = audit_settlement_partition(
    states={'A', 'B', 'NONE'},
    outcome_states={'A': {'A'}, 'B': {'B'}, 'NONE': {'NONE'}},
    required_outcomes=('A', 'B', 'NONE'),
)
check('exact_partition_proven', a.proven)

# E441-style failure: explicit allowed NONE state but no payout outcome covers it.
b = audit_settlement_partition(
    states={'A', 'B', 'NONE'},
    outcome_states={'A': {'A'}, 'B': {'B'}},
    required_outcomes=('A', 'B'),
)
check('all_false_state_blocks_proof', (not b.proven) and b.uncovered_states == ('NONE',))

# Overlap must fail closed.
c = audit_settlement_partition(
    states={1, 2},
    outcome_states={'LEFT': {1, 2}, 'RIGHT': {2}},
)
check('overlap_blocks_proof', (not c.proven) and c.overlapping_states == (2,))

# State outside declared universe must fail closed.
d = audit_settlement_partition(
    states={1},
    outcome_states={'ONLY': {1, 2}},
)
check('out_of_universe_blocks_proof', (not d.proven) and d.unknown_outcomes == ('ONLY',))

print('SETTLEMENT_PARTITION_GATE_E442_PASS')
