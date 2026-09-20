from pathlib import Path
from datetime import datetime,timezone
import json

root=Path.cwd()
candidate=root/'knowledge/candidates/KWI-INCOMPLETE-TO-CANONICAL-V1.json'
if not candidate.exists():
    raise SystemExit('candidate_missing')

data=json.loads(candidate.read_text(encoding='utf-8'))
protocol=dict()
protocol['protocol_id']='KWI-INCOMPLETE-SIGNAL-FEASIBILITY-V1'
protocol['created_at']=datetime.now(timezone.utc).isoformat()
protocol['hypothesis_id']='KWI-INCOMPLETE-TO-CANONICAL-V1'
protocol['stage']='DEVELOPMENT_FALSIFICATION'
protocol['data_source']='immutable minute manifests and hash-addressed raw payloads recorded before this scoring protocol'
protocol['unit']='city x weather-index timestamp t'
protocol['target']='later canonical complete v for the same city and t; use last observed complete v in recorder window'
protocol['predictor_primary']='arithmetic mean of all numeric temp_f values in first observed latest_incomplete snapshot for the target t'
protocol['predictor_baseline']='latest canonical complete v with t strictly earlier than target t that was already visible in the same point-in-time manifest at first incomplete observation'
protocol['no_fit']=True
protocol['station_selection']='none; include every numeric station temp_f present in first incomplete snapshot'
protocol['minimum_numeric_station_count']=1
protocol['metrics']=['MAE','RMSE','mean_signed_error','median_absolute_error']
protocol['strata']=['city','numeric_station_count']
protocol['correlation_warning']='minute observations are strongly serially correlated and are not independent statistical trials'
protocol['inference_rule']='report descriptive errors only; no p-value or independent-event claim from minute rows'
protocol['survival_rule']='primary incomplete-station-mean MAE must be lower than point-in-time previous-canonical persistence MAE overall and in at least two of the three cities'
protocol['rejection_rule']='if survival_rule fails, reject this simple incomplete-mean signal formulation rather than tuning weights or station subsets on the same data'
protocol['next_if_survives']='define temporal development-validation-holdout split before any learned model or market-price test'
protocol['market_edge_rule']='no market edge is inferred from this signal test; executable market data is a separate later gate'
protocol['revision_rule']='if target same-t revisions are observed, target remains last complete v visible within the immutable recorder window and revisions are reported separately'
protocol['missing_data_rule']='fail closed for a pair if target, prior complete persistence, or numeric incomplete station values are unavailable'
protocol['live_trading']=False
protocol['paid_actions']=False
protocol['wallet_actions']=False

outdir=root/'knowledge/candidates/protocols'
outdir.mkdir(parents=True,exist_ok=True)
out=outdir/'KWI-INCOMPLETE-SIGNAL-FEASIBILITY-V1.json'
out.write_text(json.dumps(protocol,indent=2,sort_keys=True)+chr(10),encoding='utf-8')

refs=data.get('prospective_protocols')
if not isinstance(refs,list):
    refs=list()
ref=str(out.relative_to(root))
if ref not in refs:
    refs.append(ref)
data['prospective_protocols']=refs
candidate.write_text(json.dumps(data,indent=2,sort_keys=True)+chr(10),encoding='utf-8')

print('PROTOCOL_ID',protocol.get('protocol_id'))
print('STAGE',protocol.get('stage'))
print('PRIMARY',protocol.get('predictor_primary'))
print('BASELINE',protocol.get('predictor_baseline'))
print('SURVIVAL_RULE',protocol.get('survival_rule'))
print('NO_FIT',protocol.get('no_fit'))
print('PATH',out)
print('KWI_SIGNAL_PROTOCOL_PREREG_PASS')
