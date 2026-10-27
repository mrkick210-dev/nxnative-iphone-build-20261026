"""Build an unsigned Legends Z-A iPhone shell from encrypted code/shader inputs."""
import hashlib, json, os, subprocess, sys
from pathlib import Path
repo,root=map(lambda p:Path(p).resolve(),sys.argv[1:3])
for name,digest in json.loads((root/'manifest.json').read_text()).items():
    if hashlib.file_digest((root/name).open('rb'),'sha256').hexdigest()!=digest: raise RuntimeError('Input hash mismatch: '+name)
print('Input hashes verified.',flush=True)
env=dict(os.environ,DM_GAME='0100F43008C44000',GAME='0100F43008C44000',DM_GAMES_DIR=str(root/'profiles'),DM_GAMES_FIRST='1',DM_ROOT=str(root),WORK=str(root/'tmp'),IOSOUT=str(root/'ios'),J='3',PYTHONUTF8='1',PYTHONUNBUFFERED='1')
env['PATH']=str(Path(sys.executable).parent)+os.pathsep+env['PATH']
(root/'tmp').mkdir(exist_ok=True)
def run(args): subprocess.run([str(x) for x in args],env=env,check=True)
run([sys.executable,repo/'dm/gfx/tools/dmsh_chain.py','--header'])
run(['make','-C',repo/'dm/host','-j3','GAME=0100F43008C44000','dmhost'])
env.update(DM_OODLE_HOST=str(repo/'dm/host/dmhost'),DM_OODLE_MODULES=str(root/'patched'))
run([sys.executable,Path(__file__).with_name('selected_split.py'),repo,root])
run([sys.executable,repo/'dm/gfx/tools/own_compilers.py',root/'shader/pkg',root/'mac-shaders'])
# The installed app reads the full game from Documents. Do not package partial shader inputs as game assets.
for path in (root/'data/RomFS').rglob('*'):
    if path.is_file(): path.unlink()
(root/'data/RomFS/arc/data.trpfs').touch()
env.update(W=str(root/'ipa-work'),PATCHED=str(root/'patched'),ROMFS=str(root/'data/RomFS'),MSL_IOS=str(root/'ios'),GFXAPI='nvn',FONT_PY=sys.executable,AOC=str(root/'aoc'),DM_DISPLAY_NAME='Pokémon Legends: Z-A',DM_APP_VERSION='2.0.2',DM_BUNDLE_ID='org.nxnative.0100f43008c44000',DM_ICON=str(root/'data/icon.jpg'),DM_LANG='en-US',DM_SHOW_FPS='1',DM_PSO_GPUS='none')
run(['bash',repo/'dm/ios/tools/build_ipa.sh',root/'Shell.ipa'])
print('Unsigned 2.0.2 shell compiled with DLC index 2. Full assets remain on the PC.',flush=True)
