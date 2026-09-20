from urllib.request import Request,urlopen
from urllib.error import HTTPError

agent='PredictionEdgeHunter/1.0'
base='https:'+chr(47)+chr(47)+'gamma-api.polymarket.com/events?active=true&closed=false&limit=100&offset='

for off in [1400,1499,1500,1501,1600]:
    url=base+str(off)
    req=Request(url,headers={'User-Agent':agent})
    try:
        with urlopen(req,timeout=30) as response:
            body=response.read()
            print('OFFSET',off)
            print('STATUS',response.status)
            print('BODY_PREFIX',body[:1200].decode('utf-8',errors='replace'))
    except HTTPError as exc:
        body=exc.read()
        print('OFFSET',off)
        print('STATUS',exc.code)
        print('REASON',str(exc.reason))
        print('BODY_PREFIX',body[:1200].decode('utf-8',errors='replace'))
    except Exception as exc:
        print('OFFSET',off)
        print('ERROR',type(exc).name,str(exc))
    print('---')
print('GAMMA_OFFSET_BOUNDARY_DIAG_PASS')
