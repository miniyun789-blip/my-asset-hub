"""Development-only public security master. No personal holdings or credentials."""
import sys, json, os
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from catalog_source import MarketService
root=Path(__file__).resolve().parents[1]
service=MarketService(root/'scripts'/'catalog-cache.json')
if "--krx" in sys.argv:
 import catalog_source
 catalog_source.MARKETS=("KRX",)
if "--retry-failed" in sys.argv:
 import catalog_source
 catalog_source.MARKETS=tuple(m for m in catalog_source.MARKETS if not service.catalog.get(m) or service.status.get(m,{}).get("error"))
service.refreshing=True
service._refresh()
rows={}
for group,items in service.catalog.items():
 for row in items:
  code=row['ticker'];market=row['market'];symbol=code
  if row['currency']=='KRW' and not code.startswith('KRW-'):
   symbol=code+('.KQ' if market=='KOSDAQ' else '.KS')
  elif row['currency']=='USD':symbol=code.replace('.','-')
  rows[(code,row['currency'])]={'ticker':code,'symbol':symbol,'name':row['name'],'market':market,'currency':row['currency'],**({'englishName':row['englishName']} if 'englishName'in row else {})}
required=('KRX','ETF/KR','NASDAQ','NYSE','AMEX','NYSEARCA','CRYPTO')
failed=[x for x in required if not service.catalog.get(x)]
if failed:
 print('ABORT: Required catalog missing; previous public catalog preserved:',failed,flush=True);os._exit(1)
from datetime import datetime,timezone
output={'schemaVersion':1,'generatedAt':datetime.now(timezone.utc).isoformat(),'coverage':service.status,'instruments':list(rows.values())}
target=root/'public'/'data'/'catalog.json';target.parent.mkdir(parents=True,exist_ok=True)
tmp=target.with_suffix('.tmp');tmp.write_text(json.dumps(output,ensure_ascii=False,separators=(',',':')),encoding='utf-8');tmp.replace(target)
print(json.dumps({'count':len(rows),'coverage':service.status},ensure_ascii=False),flush=True)
os._exit(0)
