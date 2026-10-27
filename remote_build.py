import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

repo, root = map(lambda p: Path(p).resolve(), sys.argv[1:3])
manifest = json.loads((root / 'manifest.json').read_text())
for name, expected in manifest.items():
    actual = hashlib.sha256((root / name).read_bytes()).hexdigest()
    if actual != expected:
        raise SystemExit(f'Input verification failed: {name}')
print(f'Verified {len(manifest)} input files.', flush=True)
env = dict(os.environ, DM_GAME='010018E011D92000', GAME='010018E011D92000',
           DM_GAMES_DIR=str(root / 'profiles'), DM_GAMES_FIRST='1',
           DM_ROOT=str(root), WORK=str(root / 'tmp'),
           IOSOUT=str(root / 'ios'), J='6',
           PYTHONUTF8='1', PYTHONUNBUFFERED='1')
env['PATH'] = str(Path(sys.executable).parent) + os.pathsep + env['PATH']
(root / 'tmp').mkdir(exist_ok=True)
subprocess.run([sys.executable, str(repo / 'dm/gfx/tools/dmsh_chain.py'), '--header'], env=env, check=True)
subprocess.run([sys.executable, str(repo / 'dm/gfx/tools/own_compilers.py'),
                str(root / 'shader/pkg'), str(root / 'mac-shaders')], env=env, check=True)
env.update(W=str(root / 'ipa-work'), PATCHED=str(root / 'patched'),
           ROMFS=str(root / 'data/RomFS'), MSL_IOS=str(root / 'ios'),
           GFXAPI='nvn', FONT_PY=sys.executable, AOC='',
           DM_DISPLAY_NAME='Pokémon Shining Pearl', DM_APP_VERSION='1.0.0',
           DM_BUNDLE_ID='org.nxnative.010018e011d92000',
           DM_ICON=str(root / 'data/icon.jpg'), DM_LANG='en-US',
           DM_SHOW_FPS='1', DM_PSO_GPUS='none')
subprocess.run(['bash', str(repo / 'dm/ios/tools/build_ipa.sh'), str(root / 'Shell.ipa')], env=env, check=True)
print('Unsigned shell compiled. Full game assets will be added locally.', flush=True)
