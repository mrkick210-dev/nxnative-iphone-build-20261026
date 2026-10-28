"""Use stock NXNative tools for the new title's code-only Mac bring-up check."""
from pathlib import Path
import importlib.util,json,os,sys,traceback
repo=Path(sys.argv[1]).resolve();root=Path(sys.argv[2]).resolve();gameid='010035F022078000'
logs=root/'logs';logs.mkdir(exist_ok=True);data=root/'data';data.mkdir(exist_ok=True)
import shutil
shutil.move(str(root/'ExeFS'),str(data/'ExeFS'))
for name in ['control.nacp','romfs_manifest.tsv']:shutil.copy2(root/name,data/name)
(data/'RomFS').mkdir(exist_ok=True)
profiles=root/'profiles';profile=profiles/gameid
env=dict(os.environ,DM_GAME=gameid,GAME=gameid,DM_GAMES_DIR=str(profiles),DM_GAMES_FIRST='1',PYTHONUTF8='1',PYTHONUNBUFFERED='1',J='3')
os.environ.update(env)
sys.path[:0]=[str(repo/'dm/games'),str(repo/'dm/tools')]
import profile_guess as pg
import game as gamemod
spec=importlib.util.spec_from_file_location('stock_build',repo/'scripts/build_ipa_from_nsp.py');stock=importlib.util.module_from_spec(spec);spec.loader.exec_module(stock);stock.pg=pg
stock.PROG.mode='off'
F=pg.facts_of(data/'ExeFS',data/'romfs_manifest.tsv')
stock.write_profile(profile,int(gameid,16),{'F':F,'name':'DRAGON BALL: Sparking! ZERO','survey':'code-only compatibility check','version':'v0','display':'2.0.73'})
g=gamemod.load(gameid);patched=root/'patched'
report={'title_id':gameid,'display_version':'2.0.73','source_commit':os.environ.get('NX_SOURCE_COMMIT'),'full_game_assets_present':False}
try:
    g=stock.rewrite(sys.executable,repo,data/'ExeFS',patched,env,logs,g,provisional=True)
    report['rewrite']='passed'
    (root/'tools').mkdir(exist_ok=True);(root/'tmp').mkdir(exist_ok=True)
    g=stock.heap_check(repo,data,patched,root,env,logs,g)
    report['heap_check_completed']=True
    text=(logs/'heap_check.log').read_text(errors='replace')
    report['reached_nnMain']='>>> nnMain' in text
    report['heap_log_tail']=text.splitlines()[-35:]
    report['memory_profile']={k:g.get(k) for k in ['mem_reserve','mem_alias','mem_stack','app_pool','game_args']}
except Exception as exc:
    report['error']=str(exc);traceback.print_exc()
(root/'probe-result.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
