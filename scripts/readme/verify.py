"""README contract: relative links, required scenes, dimensions and payload budget."""
import re
from pathlib import Path
from PIL import Image
ROOT = Path(__file__).resolve().parents[2]
text = (ROOT / 'README.md').read_text()
scenes = ['hero', 'judgment', 'review', 'tasks', 'map', 'learning', 'evaluation', 'monitoring', 'policy', 'dark', 'mobile-chat', 'mobile-review']
errors = []
for link in re.findall(r'(?:\]\(|(?:src|href)=["\'])([^\s)"\']+)', text):
    if '://' in link or link.startswith('#'):
        continue
    target = ROOT / link.split('#')[0]
    if not target.exists():
        errors.append(f'missing link: {link}')
for scene in scenes:
    path = ROOT / 'docs/readme' / f'{scene}.webp'
    if not path.exists():
        errors.append(f'missing scene: {scene}')
    else:
        if path.stat().st_size > 400_000:
            errors.append(f'oversized: {scene}')
        with Image.open(path) as image:
            expected = (750, 1800) if scene.startswith('mobile-') else (2880, 1800)
            if image.size != expected:
                errors.append(f'wrong dimensions: {scene} {image.size}')
anim = ROOT / 'docs/readme/progressive.gif'
if not anim.exists() or anim.stat().st_size > 1_000_000:
    errors.append('missing/oversized progressive.gif')
if anim.exists():
    with Image.open(anim) as image:
        duration = 0
        for frame in range(image.n_frames):
            image.seek(frame)
            duration += image.info.get('duration', 0)
        if not 3000 <= duration <= 6000:
            errors.append(f'GIF duration: {duration}')
images = list((ROOT / 'docs/readme').glob('*.webp')) + list((ROOT / 'docs/readme').glob('*.gif'))
if sum(p.stat().st_size for p in images) > 6_000_000:
    errors.append('total image budget > 6 MB')
for needle in ['```mermaid', 'OrbStack', 'G10', 'G12', 'G13', '운영 배포 승인 아님']:
    if needle not in text:
        errors.append(f'missing README contract: {needle}')
if errors:
    raise SystemExit('\n'.join(errors))
print(f'PASS: links, 12 scenes + animation; {sum(p.stat().st_size for p in images):,} bytes')
