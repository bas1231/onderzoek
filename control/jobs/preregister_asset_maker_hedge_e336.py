from pathlib import Path
from datetime import datetime,timezone
import json

root=Path.cwd()
schema_path=root/'control/edge_hunter/candidate_schema.json'
if not schema_path.exists():
    raise SystemExit('schema_missing')
schema=json.loads(schema_path.read_text(encoding='utf-8'))
now=datetime.now(timezone.utc).isoformat()

candidate=dict(
    candidate_id='ASSET-RANK-MAKER-HEDGE-V1',
    created_at=now,
    updated_at=now,
    lane='microstructure',
    hypothesis='For Polymarket event 106981, a passive YES maker fill on one leg followed by immediate taker purchases of the other two YES legs may lock a positive fee-adjusted complete-set payout.',
    mechanism='The three outcomes are a proven one-hot partition. A maker fill can improve one leg by one spread tick while maker fees are zero under the observed taker-only schedule. After a confirmed passive fill, buying the other two YES legs can complete a payout-one portfolio.',
    disconfirming_evidence=[
        'Prospective conservative shadow orders do not fill after accounting for queue ahead.',
        'Observed maker fills are followed by hedge deterioration that removes the fee-adjusted margin.',
        'The first executable hedge after a shadow fill has non-positive net value after exact taker fees.',
        'A one-tick adverse hedge buffer makes the prospective episode non-positive.',
        'Rules, negative-risk grouping, fee schedule, or one-hot settlement proof changes.',
        'Required public trade or order-book evidence is insufficient to prove queue depletion without counting cancellations as fills.',
        'The candidate only appears in discovery data and does not reproduce prospectively.'
    ],
    point_in_time_requirements=[
        'Only observations strictly after this preregistration timestamp count as prospective evidence.',
        'Rules, fee schedule, bid, ask, depth, and public fill evidence must be archived with retrieval timestamps.',
        'Discovery observations E327 through E334 may not be counted as validation or holdout evidence.',
        'Later settlement interpretation may not be backfilled into earlier decisions.',
        'Unknown fee, rule, queue, or hedge state fails closed.'
    ],
    signal_metric='Conservative shadow fill rate plus realized fee-adjusted locked value per filled 5-contract episode.',
    market_edge_test='For a prospectively confirmed passive fill, use the first executable asks with sufficient depth on the other two YES legs and exact market fee schedule. Net locked payout must remain positive after a one-tick adverse hedge buffer.',
    execution_reality_test='Size is fixed at 5 contracts. A hypothetical maker order joins behind displayed best-bid quantity. Cancellations never count as fills. Fill requires public executed-volume evidence sufficient to consume queue ahead and the shadow order. After fill, hedge using the first point-in-time executable asks with enough depth; missing hedge data is a failed episode.',
    phase='MECHANISM_DEFINED',
    decision='UNPROVEN',
    live_trading=False,
    paid_actions=False,
    wallet_actions=False,
    origin_candidate='PAYOFF-IDENTITY-MINING-V1',
    discovery_event_id='106981',
    discovery_cutoff='2026-09-20T02:07:42.741552+00:00',
    prospective_cutoff=now,
    fixed_parameters=dict(
        event_id='106981',
        shadow_size=5.0,
        maker_side='YES',
        maker_price_rule='current_best_bid',
        maker_queue_rule='join_behind_full_displayed_best_bid_quantity',
        qualifying_conditional_net_per_set_min=0.01,
        adverse_hedge_buffer_ticks=1,
        require_positive_after_buffer=True,
        maker_fee_assumption='zero_only_when_current_fee_schedule_is_takerOnly_true',
        taker_fee_source='point_in_time_market_fee_schedule',
        hedge_rule='first_executable_asks_on_other_two_YES_legs_with_sufficient_depth',
        cancellation_fill_credit=False
    ),
    discovery_evidence=[
        'E327 found a 0.98 all-YES executable ask sum on event 106981.',
        'E328 proved one-hot settlement including deterministic alphabetical tie-breaking and observed a 4 percent taker-only fee schedule.',
        'E332 showed the pure taker complete set is negative after fees.',
        'E333 found conditional maker-then-taker arithmetic of about 0.0132 to 0.0165 net per set at size 5, with one adverse tick still positive.',
        'E334 reproduced the same price structure and conditional arithmetic at a second timepoint about 29 minutes later.'
    ],
    evidence=[],
    negative_evidence=[],
    gates=dict(
        mechanism='PASS',
        prebuild_killer='PASS_DISCOVERY_ONLY',
        point_in_time='PENDING_PROSPECTIVE',
        data_ready='PENDING',
        development='DISCOVERY_COMPLETE',
        validation='PENDING',
        holdout='PENDING',
        independent_reproduction='PENDING',
        signal_edge='PENDING',
        market_edge='PENDING',
        execution_reality='PENDING',
        shadow='PENDING'
    )
)

required=schema.get('required_fields') or tuple()
missing=list()
for field in required:
    if field not in candidate:
        missing.append(field)
if missing:
    print('MISSING',missing)
    raise SystemExit('required_fields_missing')
if candidate.get('phase') not in (schema.get('allowed_phases') or tuple()):
    raise SystemExit('phase_invalid')
if candidate.get('decision') not in (schema.get('allowed_decisions') or tuple()):
    raise SystemExit('decision_invalid')

outdir=root/'knowledge/candidates'
outdir.mkdir(parents=True,exist_ok=True)
out=outdir/'ASSET-RANK-MAKER-HEDGE-V1.json'
if out.exists():
    raise SystemExit('candidate_already_exists')
out.write_text(json.dumps(candidate,indent=2,sort_keys=True)+chr(10),encoding='utf-8')
print('CANDIDATE_ID',candidate.get('candidate_id'))
print('PHASE',candidate.get('phase'))
print('DECISION',candidate.get('decision'))
print('DISCOVERY_CUTOFF',candidate.get('discovery_cutoff'))
print('PROSPECTIVE_CUTOFF',candidate.get('prospective_cutoff'))
print('SHADOW_SIZE',candidate.get('fixed_parameters').get('shadow_size'))
print('MIN_CONDITIONAL_NET',candidate.get('fixed_parameters').get('qualifying_conditional_net_per_set_min'))
print('ADVERSE_BUFFER_TICKS',candidate.get('fixed_parameters').get('adverse_hedge_buffer_ticks'))
print('PATH',out)
print('ASSET_MAKER_HEDGE_PREREGISTRATION_PASS')
