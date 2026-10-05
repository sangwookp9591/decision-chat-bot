"""Compress actual @2x PNG screenshots without altering their content."""
import json
import subprocess
import sys
from pathlib import Path
from PIL import Image
ROOT = Path(__file__).resolve().parents[2]
OUT = Path(sys.argv[1])
DEST = ROOT/'docs/readme'
DEST.mkdir(exist_ok=True)
scenes = ['hero','judgment','review','tasks','map','learning','evaluation','monitoring','policy','dark','mobile-chat','mobile-review']
manifest=[]
for scene in scenes:
    source, target = OUT/f'{scene}.png', DEST/f'{scene}.webp'
    expected = (750,1800) if scene.startswith('mobile-') else (2880,1800)
    with Image.open(source) as image:
        assert image.size == expected, (scene, image.size, expected)
    subprocess.run(['cwebp','-quiet','-q','82','-m','6',str(source),'-o',str(target)],check=True)
    assert target.stat().st_size <= 400_000, scene
    manifest.append({'file':target.name,'width':expected[0],'height':expected[1],'bytes':target.stat().st_size})
frames=[]
for scene in ['progress-typing','progress-provisional','judgment']:
    with Image.open(OUT/f'{scene}.png') as image:
        image = image.convert('RGB').resize((960,600),Image.Resampling.LANCZOS)
        frames.append(image.quantize(colors=128,method=Image.Quantize.MEDIANCUT))
gif=DEST/'progressive.gif'
frames[0].save(gif,save_all=True,append_images=frames[1:],duration=1500,loop=0,optimize=True,disposal=2)
assert gif.stat().st_size <= 1_000_000
manifest.append({'file':gif.name,'width':960,'height':600,'bytes':gif.stat().st_size,'duration_ms':4500,'frames':3})
assert sum(x['bytes'] for x in manifest) <= 6_000_000
(DEST/'images.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(manifest,indent=2))
