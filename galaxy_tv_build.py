"""Build a TVPort Galaxy app from verified, minimally extracted game inputs."""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import plistlib
import shutil
import subprocess
import sys

repo, root = (Path(p).resolve() for p in sys.argv[1:3])
title = '010099C022B96000'
manifest = json.loads((root / 'manifest.json').read_text())
for name, expected in manifest.items():
    with (root / name).open('rb') as handle:
        assert hashlib.file_digest(handle, 'sha256').hexdigest() == expected, name
print(f'Input verification passed: {len(manifest)} files.', flush=True)

env = dict(os.environ, DM_GAME=title, GAME=title, DM_GAMES_DIR=str(root / 'profiles'),
           DM_GAMES_FIRST='1', DM_ROOT=str(root), WORK=str(root / 'tmp'),
           DM_REWRITE_J='2', J='3', PYTHONUNBUFFERED='1', PYTHONUTF8='1',
           SPIRV_CROSS=shutil.which('spirv-cross') or '')
env['PATH'] = str(Path(sys.executable).parent) + os.pathsep + env['PATH']
os.environ.update(env)
for name in ('tmp', 'logs'):
    (root / name).mkdir(exist_ok=True)
spec = importlib.util.spec_from_file_location('galaxy_builder', repo / 'scripts/build_ipa_from_nsp.py')
b = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = b
spec.loader.exec_module(b)
sys.path.insert(0, str(repo / 'dm/games'))
from game import Game
g = Game(root / 'profiles' / title)
b.PROG = b.Progress('lines')
b.PROG.plan(4)
b.chain_header(sys.executable, repo, env, root / 'logs')
source_revision = subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip()
manifest_digest = hashlib.sha256((root / 'manifest.json').read_bytes()).hexdigest()
checkpoint_file = root / 'galaxy-checkpoint.json'
checkpoint = json.loads(checkpoint_file.read_text()) if checkpoint_file.exists() else {}
reuse = (checkpoint.get('source_revision') == source_revision and checkpoint.get('manifest_digest') == manifest_digest
         and all((root / 'patched' / f'{m}.patched.bin').is_file() for m in g.words('modules'))
         and (root / 'shaders/ios/vk/vk_shaders.metallib').is_file())
if reuse:
    count = checkpoint['shader_modules']
    ios = root / 'shaders/ios'
    print(f'Reusing verified code and all {count} captured shaders.', flush=True)
else:
    g = b.rewrite(sys.executable, repo, root / 'data/ExeFS', root / 'patched', env, root / 'logs', g)
    capture = b.capture_shaders(repo, root / 'data', root / 'patched', root, env, root / 'logs', g, 'vk')
    count = len(list(capture.glob('*.spv')))
    assert count > 3000, f'Incomplete shader capture: {count}'
    print(f'Base-game shader capture complete: {count} modules.', flush=True)
    ios = b.build_vk_shaders(sys.executable, repo, [capture], root / 'shaders', env, root / 'logs', g, reuse=False)
    checkpoint_file.write_text(json.dumps({'source_revision': source_revision, 'manifest_digest': manifest_digest,
                                         'shader_modules': count}, indent=2))
    encrypted = root.parent / 'galaxy-tv-compiled.7z'
    subprocess.run(['7zz', 'a', '-t7z', '-mx=1', '-mhe=on', '-p' + env['INPUT_PASSWORD'], str(encrypted),
                    'patched', 'shaders', 'data/vk_capture', 'galaxy-checkpoint.json'], cwd=root,
                   check=True, stdout=subprocess.DEVNULL)
    draft = subprocess.check_output(['gh', 'release', 'view', env['RELEASE_TAG'], '--repo', env['GITHUB_REPOSITORY'],
                                    '--json', 'isDraft', '--jq', '.isDraft'], text=True).strip()
    assert draft == 'true'
    subprocess.run(['gh', 'release', 'upload', env['RELEASE_TAG'], str(encrypted), '--repo',
                    env['GITHUB_REPOSITORY'], '--clobber'], check=True)

project = root / 'tvport-xcode'
derived = root / 'tvport-derived'
environment = root / 'game-env.txt'
# Docked mode enables the gyro pointer on a motion-capable controller.
environment.write_text('DM_OPMODE=1\nDM_GUEST_FILE=1\n')
env.update(W=str(root / 'tv-work'), PATCHED=str(root / 'patched'), ROMFS=str(root / 'data/RomFS'),
           MSL_IOS=str(ios), GFXAPI='vulkan', FONT_PY=sys.executable, AOC='',
           DM_TVOS='1', DM_COPY_ROMFS='NO', DM_DISPLAY_NAME='Super Mario Galaxy',
           DM_APP_VERSION='1.0.0', DM_BUNDLE_ID='org.nxnative.tv.010099c022b96000',
           DM_ICON=str(root / 'data/icon.jpg'), DM_SHOW_FPS='1', DM_PSO_GPUS='none',
           DM_LANG='en-US', DM_ENTITLEMENTS='', DM_ENV_FILE=str(environment),
           DM_XCODE_PROJECT_DIR=str(project), DM_XCODE_DERIVED_DATA=str(derived))
subprocess.run(['bash', str(repo / 'dm/ios/tools/build_ipa.sh'), '--prepare-xcode'], env=env, check=True)
schemes = sorted((project / 'DmIOS.xcodeproj/xcshareddata/xcschemes').glob('*.xcscheme'))
assert len(schemes) == 1, 'Expected one generated game scheme'
command = ['xcodebuild', '-project', str(project / 'DmIOS.xcodeproj'), '-scheme', schemes[0].stem,
           '-configuration', 'Release', '-destination', 'generic/platform=tvOS',
           '-derivedDataPath', str(derived), 'CODE_SIGNING_ALLOWED=NO',
           'CODE_SIGNING_REQUIRED=NO', 'CODE_SIGN_IDENTITY=', 'DM_COPY_GAME_RESOURCES=NO',
           f'DM_XCODE_OUTPUT_ROOT={derived}', 'build']
with (root / 'logs/tvos-build.log').open('w') as log:
    result = subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT)
if result.returncode:
    lines = (root / 'logs/tvos-build.log').read_text(errors='replace').splitlines()
    print('\n'.join(line for line in lines if 'error:' in line)[-10000:], flush=True)
    raise SystemExit(result.returncode)
app = derived / 'Build/Products/Release-appletvos/DmIOS.app'
info = plistlib.loads((app / 'Info.plist').read_bytes())
assert info['CFBundleSupportedPlatforms'] == ['AppleTVOS'], info['CFBundleSupportedPlatforms']
assert info['UIDeviceFamily'] == [3], info['UIDeviceFamily']
subprocess.run(['xcrun', 'vtool', '-show-build', str(app / info['CFBundleExecutable'])], check=True)
subprocess.run([sys.executable, str(repo / 'dm/ios/tools/pack_ipa.py'), str(root / 'GalaxyTV.ipa'),
                '--skip', 'Payload/DmIOS.app/_CodeSignature', '--skip', 'Payload/DmIOS.app/embedded.mobileprovision',
                f'Payload/DmIOS.app/msl/vk={ios / "vk"}', f'Payload/DmIOS.app={app}'], env=env, check=True)
summary = {'title_id': title, 'version': '1.0.0', 'shader_modules': count,
           'bundle_id': info['CFBundleIdentifier'], 'platform': info['CFBundleSupportedPlatforms'],
           'device_family': info['UIDeviceFamily'], 'full_assets_included': False}
(root / 'build-verification.json').write_text(json.dumps(summary, indent=2))
print(json.dumps(summary, indent=2), flush=True)
