"""Use the stock compiler's supported partial builds, then validate a complete cached build."""
import hashlib,json,os,re,shutil,subprocess,sys,time
from pathlib import Path
mode,repo,root=sys.argv[1],Path(sys.argv[2]).resolve(),Path(sys.argv[3]).resolve()
env=dict(os.environ,DM_GAME='010035F022078000',GAME='010035F022078000',DM_GAMES_DIR=str(root/'profiles'),DM_GAMES_FIRST='1',DM_ROOT=str(root),WORK=str(root/'tmp'),IOSOUT=str(root/'ios'),DMSH_CAS=str(root/'mac-shaders/cas'),J='3',PYTHONUTF8='1',PYTHONUNBUFFERED='1')
env['PATH']=str(Path(sys.executable).parent)+os.pathsep+env['PATH']
os.environ.update(env)
(root/'tmp').mkdir(exist_ok=True)
def run(args,**kw):return subprocess.run([str(x) for x in args],env=env,check=True,**kw)
def archive(name,items):
    run(['7zz','a','-t7z','-mx=1','-mhe=on','-p'+env['INPUT_PASSWORD'],root/name,*items],cwd=root,stdout=subprocess.DEVNULL)
    draft=run(['gh','release','view',env['RELEASE_TAG'],'--repo',env['GITHUB_REPOSITORY'],'--json','isDraft','--jq','.isDraft'],capture_output=True,text=True).stdout.strip()
    assert draft=='true','Release must remain unpublished'
    run(['gh','release','upload',env['RELEASE_TAG'],root/name,'--repo',env['GITHUB_REPOSITORY'],'--clobber'])
def validate_manifest():
    for name,digest in json.loads((root/'manifest.json').read_text()).items():
        assert hashlib.file_digest((root/name).open('rb'),'sha256').hexdigest()==digest,name
validate_manifest()
run([sys.executable,repo/'dm/gfx/tools/dmsh_chain.py','--header'])
profile=root/'profiles/010035F022078000'
if mode=='prepare':
    probe=json.loads((root/'probe-result.json').read_text())
    assert probe.get('rewrite')=='passed' and probe.get('reached_nnMain') is True,probe
    # Reuse the completed code rewrite; shader packages were extracted and verified locally.
    from sparking_adapt import apply
    apply(repo,profile)
    # Only the SDK's new, build-gated node-area cuts affect its rewrite.
    # Main's four allocator instructions remain identical to the verified rewrite.
    run([sys.executable,repo/'dm/tools/patch_nso.py',root/'original/ExeFS/sdk',root/'patched','sdk'])
    sys.path.insert(0,str(repo/'dm/games'));import game
    import importlib.util
    spec=importlib.util.spec_from_file_location('stock',repo/'scripts/build_ipa_from_nsp.py')
    stock=importlib.util.module_from_spec(spec);spec.loader.exec_module(stock);stock.PROG.mode='off'
    logs=root/'logs';logs.mkdir(exist_ok=True)
    host=stock.build_mac_host(repo,root/'tools/dmhost',env,logs,game.load('010035F022078000'))
    rd=root/'tmp/compact-memory';rd.mkdir(parents=True,exist_ok=True)
    for d in ['save','temp','msl']:(rd/d).mkdir(exist_ok=True)
    henv=dict(env,DM_ROMFS=str(root/'data/RomFS'),DM_SAVE=str(rd/'save'),DM_TEMP=str(rd/'temp'),DM_MSL_DIR=str(rd/'msl'))
    log=logs/'compact-memory.log'
    stock.boot_mac(host,root/'patched',henv,rd,log,15)
    text=log.read_text(errors='replace')
    peaks=[float(v) for v in re.findall(r'alias region mapped up to \+([0-9.]+) GB',text)]
    assert '>>> nnMain' in text and "Unreal\'s allocator" in text and 'host malloc zone' in text,text[-3000:]
    print('Compact memory peak values:',peaks,flush=True)
    assert peaks and max(peaks)<=3.135,f'Compact alias peak: {peaks}; log: {text[-3000:]}'
    print(f'Compact memory validation reached nnMain; alias peak {max(peaks):.2f} GiB. Empty game assets prevent a gameplay test.',flush=True)
    assert len([v for v in (profile/'shader_map.tsv').read_text().splitlines() if v and not v.startswith(('#','package'))])==13599

    rows=[ln.split('\t') for ln in (profile/'shader_map.tsv').read_text().splitlines() if ln and not ln.startswith('#')]
    keys=sorted({r[3] for r in rows if len(r)>3 and re.fullmatch('[0-9a-f]{16}',r[3])})
    dependencies={}
    for ln in (profile/'shader_pairs.tsv').read_text().splitlines():
        c=ln.split('\t')
        if len(c)>=2 and all(re.fullmatch('[0-9a-f]{16}',x) for x in c[:2]):dependencies.setdefault(c[0],set()).add(c[1])
    for i in range(4):
        own=set(keys[i::4]);wanted=own|{p for k in own for p in dependencies.get(k,())}
        (root/f'shard-{i}.json').write_text(json.dumps(sorted(wanted)))
        print(f'Shard {i}: {len(own)} assigned shaders; {len(wanted)} including pixel dependencies.',flush=True)
    for p in (root/'data/RomFS').rglob('*'):
        if p.is_file():p.unlink()
    (root/'data/RomFS/SparkingZERO/Content/Paks').mkdir(parents=True,exist_ok=True)
    (root/'data/RomFS/SparkingZERO/Content/Paks/pakchunk0-Switch.pak').touch()
    items=['profiles','patched','data','aoc','shader','logs',*[f'shard-{i}.json' for i in range(4)]]
    manifest={p.relative_to(root).as_posix():hashlib.file_digest(p.open('rb'),'sha256').hexdigest() for item in items for p in ([root/item] if (root/item).is_file() else (root/item).rglob('*')) if p.is_file()}
    (root/'manifest.json').write_text(json.dumps(manifest));archive('parallel-inputs.7z',items+['manifest.json'])
elif mode=='shard':
    i=int(sys.argv[4]);keys=json.loads((root/f'shard-{i}.json').read_text());start=time.monotonic()
    run([sys.executable,repo/'dm/gfx/tools/own_compilers.py',root/'shader/pkg',root/'mac-shaders',*keys])
    reports=list((root/'mac-shaders').glob('b-*/_b_build.json'));assert len(reports)==1
    report=json.loads(reports[0].read_text());assert len(report)>=len(keys) and all(r['st']=='ok' for r in report),'Partial shader build failed'
    print(f'Shard {i}: all {len(report)} shaders compiled in {time.monotonic()-start:.1f} seconds.',flush=True)
    archive(f'shard-{i}.7z',['mac-shaders','ios'])
elif mode=='merge':
    from sparking_adapt import apply
    apply(repo,profile)
    for i in range(4):
        run(['gh','release','download',env['RELEASE_TAG'],'--repo',env['GITHUB_REPOSITORY'],'--pattern',f'shard-{i}.7z','--dir',root,'--clobber'])
        run(['7zz','x','-y','-aoa','-p'+env['INPUT_PASSWORD'],'-o'+str(root),root/f'shard-{i}.7z'],stdout=subprocess.DEVNULL)
    # A stock full pass verifies every cached shader and generates the final stamps and host tables.
    run([sys.executable,repo/'dm/gfx/tools/own_compilers.py',root/'shader/pkg',root/'mac-shaders'])
    report=json.loads(next((root/'mac-shaders').glob('b-*/_b_build.json')).read_text());assert len(report)==13599 and all(r['st']=='ok' for r in report)
    env.update(W=str(root/'ipa-work'),PATCHED=str(root/'patched'),ROMFS=str(root/'data/RomFS'),MSL_IOS=str(root/'ios'),GFXAPI='nvn',FONT_PY=sys.executable,AOC=str(root/'aoc'),DM_DISPLAY_NAME='DRAGON BALL Sparking ZERO',DM_APP_VERSION='2.0.73',DM_BUNDLE_ID='org.nxnative.010035f022078000',DM_ICON=str(root/'data/icon.jpg'),DM_LANG='en-US',DM_SHOW_FPS='1',DM_PSO_GPUS='none')
    run(['bash',repo/'dm/ios/tools/build_ipa.sh',root/'Shell.ipa'])
    (root/'Shell.sha256').write_text(hashlib.file_digest((root/'Shell.ipa').open('rb'),'sha256').hexdigest()+'  Shell.ipa\n')
    run([sys.executable,Path(__file__).with_name('memory_request.py'),root])
    archive('result-parallel.7z',['MemoryRequest.ipa','MemoryRequest.sha256','logs'])
else:raise ValueError(mode)
