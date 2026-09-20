from pathlib import Path
from datetime import datetime,timezone,timedelta
import json

root=Path.cwd()
old_path=root/'knowledge/candidates/KWI-INCOMPLETE-TO-CANONICAL-V1.json'
if not old_path.exists():
    raise SystemExit('old_candidate_missing')
old=json.loads(old_path.read_text(encoding='utf-8'))
results=old.get('test_results')
if not isinstance(results,list):
    results=list()
result=dict()
result['test_id']='KWI-INCOMPLETE-SIGNAL-FEASIBILITY-V1'
result['stage']='DEVELOPMENT_FALSIFICATION'
result['scorable_pairs']=459
result['primary_mae']=0.20416744475568097
result['baseline_mae']=0.08481481481481465
result['city_wins']=2
result['overall_win']=False
result['survival_rule_pass']=False
result['conclusion']='simple unweighted incomplete station mean rejected; do not tune station subsets or weights on same data'
result['evidence']='local state analysis kwi-signal-feasibility-e367.json'
if not any(isinstance(x,dict) and x.get('test_id')==result.get('test_id') for x in results):
    results.append(result)
old['test_results']=results
old['simple_incomplete_mean_status']='REJECTED_IN_DEVELOPMENT'
old_path.write_text(json.dumps(old,indent=2,sort_keys=True)+chr(10),encoding='utf-8')

now=datetime.now(timezone.utc)
end=now+timedelta(hours=24)
new_id='KWI-FULL-STATION-PRECANONICAL-V1'
new_path=root/'knowledge/candidates'/str(new_id+'.json')

candidate=dict()
candidate['candidate_id']=new_id
candidate['lane']='weather'
candidate['hypothesis']='When an incomplete KWI point already contains the full expected set of numeric station temperatures, their arithmetic mean may predict the later canonical value before the status becomes complete.'
candidate['mechanism']='Possible publication or completion-status lag after all expected station observations are already present.'
candidate['origin']='post-hoc mechanism discovered in KWI-INCOMPLETE-SIGNAL-FEASIBILITY-V1 development data; all pre-cutoff evidence is discovery only'
candidate['discovery_evidence']=dict(station_count_5_n=143,station_count_5_mae=0.004965034965035021,station_count_8_n=143,station_count_8_mae=0.0027972027972061166)
candidate['phase']='MECHANISM_DEFINED'
candidate['decision']='UNPROVEN'
candidate['point_in_time_requirements']=['first observed incomplete snapshot for target city and t','config_version visible at observation time','previous complete point visible at observation time','expected station count derived only from previous complete contributors for same city and config','later complete v for same city and t used only as target','no pre-cutoff rows count as prospective evidence']
candidate['signal_metric']='MAE and RMSE of full-station incomplete arithmetic mean versus later canonical v'
candidate['market_edge_test']='not started; signal edge must survive first'
candidate['execution_reality_test']='not started'
candidate['live_trading']=False
candidate['paid_actions']=False
candidate['wallet_actions']=False

protocol=dict()
protocol['protocol_id']='KWI-FULL-STATION-PRECANONICAL-24H-V1'
protocol['created_at']=now.isoformat()
protocol['prospective_cutoff']=now.isoformat()
protocol['window_start']=now.isoformat()
protocol['window_end']=end.isoformat()
protocol['duration_hours']=24
protocol['data_source']='existing immutable minute KWI recorder manifests and hash-addressed raw payloads'
protocol['eligibility_rule']='At first observation of an incomplete city x t point, numeric station count must equal contributors from the latest earlier complete point already visible for the same city and config_version.'
protocol['predictor']='arithmetic mean of all numeric temp_f values in that first eligible incomplete snapshot'
protocol['baseline']='latest earlier complete v already visible at prediction time'
protocol['target']='later complete v for identical city and t'
protocol['no_fit']=True
protocol['no_station_subset_selection']=True
protocol['no_pre_cutoff_credit']=True
protocol['minimum_eligible_pairs_per_city']=30
protocol['minimum_eligible_cities']=2
protocol['metrics']=['MAE','RMSE','mean_signed_error','median_absolute_error','lead_seconds_to_first_complete']
protocol['survival_rule']='At least two cities must each have at least 30 eligible prospective pairs, and predictor MAE must beat persistence MAE overall and in every city meeting the minimum sample threshold.'
protocol['rejection_rule']='If survival rule fails, reject this full-station pre-canonical signal formulation without tuning on the same prospective window.'
protocol['correlation_warning']='minute rows are serially correlated and are not independent statistical trials'
protocol['market_edge_rule']='No market edge is inferred from this signal test.'
protocol['live_trading']=False
protocol['paid_actions']=False
protocol['wallet_actions']=False

protocol_dir=root/'knowledge/candidates/protocols'
protocol_dir.mkdir(parents=True,exist_ok=True)
protocol_path=protocol_dir/'KWI-FULL-STATION-PRECANONICAL-24H-V1.json'
protocol_path.write_text(json.dumps(protocol,indent=2,sort_keys=True)+chr(10),encoding='utf-8')
candidate['prospective_protocols']=[str(protocol_path.relative_to(root))]
new_path.write_text(json.dumps(candidate,indent=2,sort_keys=True)+chr(10),encoding='utf-8')

print('OLD_CANDIDATE',old.get('candidate_id'))
print('OLD_SIMPLE_STATUS',old.get('simple_incomplete_mean_status'))
print('NEW_CANDIDATE',candidate.get('candidate_id'))
print('NEW_PHASE',candidate.get('phase'))
print('NEW_DECISION',candidate.get('decision'))
print('PROSPECTIVE_CUTOFF',protocol.get('prospective_cutoff'))
print('WINDOW_END',protocol.get('window_end'))
print('MIN_PAIRS_PER_CITY',protocol.get('minimum_eligible_pairs_per_city'))
print('MIN_CITIES',protocol.get('minimum_eligible_cities'))
print('KWI_FULL_STATION_PREREG_PASS')
