from pathlib import Path
import json,re,sys
root=Path(__file__).resolve().parents[1];v=sys.argv[1]
build=sys.argv[2] if len(sys.argv)>2 else json.loads((root/'public/manifest.webmanifest').read_text()).get('build','')
if build and not re.fullmatch(r'[A-Za-z0-9.-]+',build):raise ValueError('invalid build')
if not re.fullmatch(r'\d+\.\d+\.\d+(?:-[a-z]+\.\d+)?',v):raise ValueError('invalid version')
p=root/'public/js/app.js';s=p.read_text();s=re.sub(r"const APP_VERSION='[^']+'",f"const APP_VERSION='{v}'",s);p.write_text(s)
p=root/'public/service-worker.js';s=p.read_text();s=re.sub(r"const VERSION='[^']+'",f"const VERSION='{v}'",s);p.write_text(s)
p=root/'worker.js';s=p.read_text();s=re.sub(r"const VERSION='[^']+'",f"const VERSION='{v}'",s);p.write_text(s)
p=root/'public/index.html';s=p.read_text();s=re.sub(r'(<span id="version-label">)[^<]+',lambda m:m[1]+f'TEST · v{v} · build {build}',s);p.write_text(s)
for f in ['package.json','public/manifest.webmanifest']:
 p=root/f;d=json.loads(p.read_text());d['version']=v;d['build']=build;p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
if (root/'package-lock.json').exists():
 p=root/'package-lock.json';d=json.loads(p.read_text());d['version']=v;d['packages']['']['version']=v;p.write_text(json.dumps(d,indent=2)+'\n')
if len(sys.argv)>2:
 build=sys.argv[2]
 if not re.fullmatch(r'[A-Za-z0-9.-]+',build):raise ValueError('invalid build')
 for file,key in [('public/js/app.js','BUILD_ID'),('worker.js','BUILD')]:
  p=root/file;s=p.read_text();s=re.sub(r"const "+key+r"='[^']+'",f"const {key}='{build}'",s);p.write_text(s)
 print('build',build)
print(v)

p=root/'public/service-worker.js';s=p.read_text();s=re.sub(r"const CACHE='[^']+'",f"const CACHE='my-asset-hub-v{v}-{build}'",s);s=re.sub(r'/\* My Asset Hub TEST .*?\*/',f'/* My Asset Hub TEST v{v} · build {build} */',s);p.write_text(s)
