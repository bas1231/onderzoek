"""Pure deterministic preregistered shadow deathchecks; no network or executor."""
import hashlib,json,pathlib,datetime
from decimal import Decimal
P=pathlib.Path
EXPECTED={'DC1_FALSE_POSITIVE_FILL','DC2_NO_HINDSIGHT','DC3_NO_LIVE_OR_COST_PATH'}

def validate_protocol(candidate,protocol):
    if protocol.get('schema')!='PVA_PROSPECTIVE_SHADOW_PROTOCOL_V1' or protocol.get('candidate_id')!=candidate.get('candidate_id'):raise ValueError('PROTOCOL_IDENTITY_MISMATCH')
    safety=protocol.get('safety')
    if not isinstance(safety,dict) or any(safety.get(k) is not False for k in ('live_trading','order_placement','cancel_or_amend','wallet_actions','paid_actions','openai_api','cloud_or_vps')):raise ValueError('UNSAFE_PROTOCOL')
    gates=protocol.get('mandatory_deathchecks_before_activation')
    if not isinstance(gates,list) or {x.get('id') for x in gates if isinstance(x,dict)}!=EXPECTED:raise ValueError('DEATHCHECK_SET_MISMATCH')
    if protocol.get('historical_regression_only',{}).get('miami_case',{}).get('role')!='proof-of-mechanism regression fixture only; never validation evidence':raise ValueError('HISTORICAL_FIXTURE_ROLE_MISMATCH')
    return True

def conservative_fill(queue_ahead,executions,cancellations=0,ambiguous=False):
    if ambiguous:return {'status':'UNPROVEN_FILL','quantity':0}
    q=max(0,int(queue_ahead));e=max(0,int(executions));c=max(0,int(cancellations))
    # Cancellation has no depletion credit. Executed volume must consume queue ahead first.
    qty=max(0,e-q)
    return {'status':'PROVEN_PARTIAL' if qty else 'UNPROVEN_FILL','quantity':qty,'cancellation_credit':0,'ignored_cancellations':c}

def preclose_order(book_time,decision_time,close_time,frozen):
    b=datetime.datetime.fromisoformat(book_time);d=datetime.datetime.fromisoformat(decision_time);c=datetime.datetime.fromisoformat(close_time)
    if any(x.tzinfo is None for x in (b,d,c)) or not b<=d<c:raise ValueError('NO_HINDSIGHT')
    allowed={'maker_bid_cents','t_minus_minutes','size_contracts','side'}
    if set(frozen)-allowed:raise ValueError('UNFROZEN_ORDER_PARAMETER')
    return dict(frozen)

def run_deathchecks(candidate,protocol,source_hashes,code_commit):
    validate_protocol(candidate,protocol);checks=[]
    # DC1: touch/cancel cannot fill; only executions after price-time queue drain count.
    a=conservative_fill(5,0,cancellations=10);b=conservative_fill(5,7);c=conservative_fill(0,4,ambiguous=True)
    checks.append({'id':'DC1_FALSE_POSITIVE_FILL','pass':a['quantity']==0 and a['cancellation_credit']==0 and b['quantity']==2 and c['status']=='UNPROVEN_FILL'})
    # DC2 uses only timestamps/parameters frozen before close; post-close fails closed.
    good=preclose_order('2026-09-26T10:00:00+00:00','2026-09-26T10:01:00+00:00','2026-09-26T10:05:00+00:00',{'maker_bid_cents':89,'t_minus_minutes':5,'size_contracts':5,'side':'NO'})
    try:preclose_order('2026-09-26T10:00:00+00:00','2026-09-26T10:06:00+00:00','2026-09-26T10:05:00+00:00',good);hindsight=True
    except ValueError:hindsight=False
    try:preclose_order('2026-09-26T10:00:00+00:00','2026-09-26T10:01:00+00:00','2026-09-26T10:05:00+00:00',{**good,'price_from_settlement':True});future_parameter=True
    except ValueError:future_parameter=False
    checks.append({'id':'DC2_NO_HINDSIGHT','pass':not hindsight and not future_parameter})
    # DC3 is structural: pure stdlib functions, no subprocess/network/order API; protocol has all action flags false.
    safety=protocol['safety'];checks.append({'id':'DC3_NO_LIVE_OR_COST_PATH','pass':all(safety[k] is False for k in ('live_trading','order_placement','cancel_or_amend','wallet_actions','paid_actions','openai_api','cloud_or_vps'))})
    miami={'fixture_only':True,'cost':str(Decimal(5)*Decimal('0.89')),'payout':'5.00','profit':str(Decimal('5.00')-Decimal(5)*Decimal('0.89')),'roi_pct':str((Decimal('5.00')-Decimal(5)*Decimal('0.89'))/(Decimal(5)*Decimal('0.89'))*100)}
    miami['pass']=miami['cost']=='4.45' and miami['profit']=='0.55' and Decimal(miami['roi_pct']).quantize(Decimal('0.01'))==Decimal('12.36')
    return {'protocol_id':protocol['protocol_id'],'candidate_id':candidate['candidate_id'],'source_hashes':source_hashes,'code_commit':code_commit,'deathchecks':checks,'all_deathchecks_pass':all(x['pass'] for x in checks),'checks_pass':all(x['pass'] for x in checks),'miami_regression_fixture':miami,'prospective_evidence':False,'activation_authorized':False,'activation_blockers':['READ_ONLY_RAW_ORDERBOOK_ARCHIVE_AND_SEQUENCE_COLLECTOR_NOT_IMPLEMENTED','NO_PROSPECTIVE_RUNS'],'live_trading':False,'paid_actions':False,'wallet_actions':False,'remote_push':False,'scientific_status':'NO_PROVEN_EDGE'}
