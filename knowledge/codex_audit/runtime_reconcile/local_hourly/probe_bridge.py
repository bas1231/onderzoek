import http.client,json,pathlib,datetime
root=pathlib.Path(__file__).resolve().parent
token=(pathlib.Path.home()/'.config/prediction-chat-bridge/token').read_text().strip()
rows=[]
for port in (8765,8766,8767):
 c=http.client.HTTPConnection('127.0.0.1',port,timeout=3);row={'port':port,'timestamp':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 try:
  c.request('GET','/health',headers={'Authorization':'Bearer '+token});r=c.getresponse();row['http_status']=r.status;data=json.loads(r.read(65536));row['health']={k:v for k,v in data.items() if k in ('ok','service','version','allowed_actions','actions','consumer_routing','upstream_port','live_trading','paid_actions','wallet_actions','openai_api')}
 except Exception as e:row['error_type']=type(e).__name__
 finally:c.close()
 rows.append(row)
(root/'bridge_health.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(rows,indent=2))
