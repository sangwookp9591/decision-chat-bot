from pathlib import Path
import shutil
root=Path.cwd(); dest=root/'artifacts/review/completeness/scratch/suite';shutil.copytree(root/'frontend/e2e',dest,dirs_exist_ok=True)
for p in dest.rglob('*.ts'):
 s=p.read_text().replace('@t-alpha.dev','@t-audit-e2e-1005.dev')
 if p.name=='rem-ui.spec.ts':s=s.replace("new URL('../../artifacts/review/rem-ui/', import.meta.url).pathname",repr(str(root/'artifacts/review/completeness/e2e/rem-ui')))
 p.write_text(s)
node=root/'artifacts/review/completeness/scratch/node_modules'
if not node.exists():node.symlink_to(root/'frontend/node_modules',target_is_directory=True)
