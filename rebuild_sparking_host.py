"""Reuse final compiled libraries; rebuild only the iPhone host with the startup fix."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys,zipfile
repo,root=map(lambda x:Path(x).resolve(),sys.argv[1:3])
profile=root/'profiles/010035F022078000'
env=dict(os.environ,DM_GAME='010035F022078000',GAME='010035F022078000',DM_GAMES_DIR=str(root/'profiles'),DM_GAMES_FIRST='1',PYTHONUTF8='1',PYTHONUNBUFFERED='1',J='3')
env['PATH']=str(Path(sys.executable).parent)+os.pathsep+env['PATH'];os.environ.update(env)
def run(args,**kw):return subprocess.run([str(x) for x in args],env=env,check=True,**kw)
assert hashlib.file_digest((root/'MemoryRequest.ipa').open('rb'),'sha256').hexdigest()==(root/'MemoryRequest.sha256').read_text().split()[0]
with zipfile.ZipFile(root/'MemoryRequest.ipa') as z:
    assert z.testzip() is None
    app=next(n.rsplit('/',1)[0] for n in z.namelist() if n.count('/')==2 and n.endswith('/Info.plist'))
    shaders=[]
    for n in z.namelist():
        if n.startswith(app+'/msl/') and not n.endswith('/'):
            dest=root/'ios'/n[len(app+'/msl/'):];dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(z.read(n));shaders.append(dest)
    for name in ['c1_full.tsv','cb_extent.tsv','shader_map.tsv','shader_pairs.tsv','pso_pairs.tsv']:
        (profile/name).write_bytes(z.read(app+'/dm/'+name))
assert len([p for p in shaders if p.name.endswith('_b.json')])==13599
assert len([p for p in shaders if p.name.endswith('.metallib')])==16120
from sparking_adapt import apply as memory_adapt
from sparking_ssl_fix import apply as ssl_adapt
memory_adapt(repo,profile);ssl_adapt(repo)
run([sys.executable,repo/'dm/gfx/tools/dmsh_chain.py','--header'])
# Exercise the exact modified context functions before building the app.
source=(repo/'dm/host/hle_net.c').read_text();functions=[]
for symbol in ['_ZN2nn3ssl7Context6CreateENS1_10SslVersionE','_ZN2nn3ssl7Context7DestroyEv']:
    start=source.index('HLE_FORCE("'+symbol+'"');end=source.index('\n}',start)+2;functions.append(source[start:end])
test=root/'ssl_context_test.c'
test.write_text('''#include <stdint.h>
#include <assert.h>
typedef uint32_t Result;
#define RES_OK 0u
#define RES_FAIL 674u
#define LOG(...) ((void)0)
#define HLE_FORCE(m,w,r,n,...) static r n(__VA_ARGS__)
'''+ '\n'.join(functions)+'''
int main(void) {
 uint64_t a=0,b=0;
 assert(h_ssl_CtxCreate(0,1)==RES_FAIL);
 assert(h_ssl_CtxCreate(&a,0)==RES_FAIL && a==0);
 assert(h_ssl_CtxCreate(&a,1)==RES_OK && a!=0);
 assert(h_ssl_CtxCreate(&b,1)==RES_OK && b!=0 && a!=b);
 assert(h_ssl_CtxCreate(&a,1)==RES_FAIL);
 assert(h_ssl_CtxDestroy(&a)==RES_OK && a==0);
 assert(h_ssl_CtxDestroy(&a)==RES_FAIL);
 assert(h_ssl_CtxCreate(&a,1)==RES_OK);
 assert(h_ssl_CtxDestroy(&a)==RES_OK && h_ssl_CtxDestroy(&b)==RES_OK);
 return 0;
}
''')
run(['clang','-std=c11','-Wall','-Wextra','-Werror',test,'-o',root/'ssl_context_test'])
run([root/'ssl_context_test'])
print('Offline SSL context ownership/lifecycle checks passed.',flush=True)
print('Reused all 13,599 compiled shader libraries; restored final host tables.',flush=True)
env.update(W=str(root/'ipa-work'),PATCHED=str(root/'patched'),ROMFS=str(root/'data/RomFS'),MSL_IOS=str(root/'ios'),GFXAPI='nvn',FONT_PY=sys.executable,AOC=str(root/'aoc'),DM_DISPLAY_NAME='DRAGON BALL Sparking ZERO',DM_APP_VERSION='2.0.73',DM_BUNDLE_ID='org.nxnative.010035f022078000',DM_ICON=str(root/'data/icon.jpg'),DM_LANG='en-US',DM_SHOW_FPS='1',DM_PSO_GPUS='none')
run(['bash',repo/'dm/ios/tools/build_ipa.sh',root/'Shell.ipa'])
(root/'Shell.sha256').write_text(hashlib.file_digest((root/'Shell.ipa').open('rb'),'sha256').hexdigest()+'  Shell.ipa\n')
run([sys.executable,Path(__file__).with_name('memory_request.py'),root])
run(['7zz','a','-t7z','-mx=1','-mhe=on','-p'+env['INPUT_PASSWORD'],root/'ssl-startup-result.7z','MemoryRequest.ipa','MemoryRequest.sha256'],cwd=root,stdout=subprocess.DEVNULL)
run(['gh','release','upload','sparking-build-input',root/'ssl-startup-result.7z','--repo',env['GITHUB_REPOSITORY'],'--clobber'])
