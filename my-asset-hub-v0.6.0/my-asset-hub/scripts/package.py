from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
import sys
root=Path(__file__).resolve().parents[1];target=Path(sys.argv[1]).resolve();target.parent.mkdir(exist_ok=True,parents=True)
include=['public','scripts','tests','test-evidence','licenses','worker.js','wrangler.jsonc','package.json','package-lock.json','README.md','CHANGELOG.md','TEST_REPORT.md','FEATURE_COMPARISON.md','.gitignore','.github','THIRD_PARTY_NOTICES.md']
with ZipFile(target,'w',ZIP_DEFLATED) as z:
 for name in include:
  p=root/name
  for f in sorted(p.rglob('*')) if p.is_dir() else [p]:
   if f.is_file() and '__pycache__' not in f.parts and f.name not in ['catalog-cache.json'] and not f.name.endswith('.tmp'):
    z.write(f,Path('my-asset-hub')/f.relative_to(root))
print(target)
