from pathlib import Path
import json,re,sys
root=Path(__file__).resolve().parents[1];v=sys.argv[1]
if not re.fullmatch(r'\d+\.\d+\.\d+(?:-[a-z]+\.\d+)?',v):raise ValueError('invalid version')
p=root/'public/js/app.js';s=p.read_text();s=re.sub(r"const APP_VERSION='[^']+'",f"const APP_VERSION='{v}'",s);p.write_text(s)
p=root/'public/service-worker.js';s=p.read_text();s=re.sub(r"const VERSION='[^']+'",f"const VERSION='{v}'",s);p.write_text(s)
p=root/'worker.js';s=p.read_text();s=re.sub(r"const VERSION='[^']+'",f"const VERSION='{v}'",s);p.write_text(s)
p=root/'public/index.html';s=p.read_text();s=re.sub(r'My Asset Hub · v[\d.a-z-]+',f'My Asset Hub · v{v}',s);p.write_text(s)
for f in ['package.json','public/manifest.webmanifest']:
 p=root/f;d=json.loads(p.read_text());d['version']=v;p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
if (root/'package-lock.json').exists():
 p=root/'package-lock.json';d=json.loads(p.read_text());d['version']=v;d['packages']['']['version']=v;p.write_text(json.dumps(d,indent=2)+'\n')
print(v)
