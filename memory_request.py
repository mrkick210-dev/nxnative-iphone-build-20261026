"""Add the app's standard memory entitlement request; no personal signing keys are used."""
from pathlib import Path
import hashlib,os,plistlib,subprocess,sys,zipfile
root=Path(sys.argv[1]).resolve()
expected=(root/'Shell.sha256').read_text().split()[0]
assert hashlib.file_digest((root/'Shell.ipa').open('rb'),'sha256').hexdigest()==expected
folder=root/'request';folder.mkdir()
with zipfile.ZipFile(root/'Shell.ipa') as z:
    assert z.testzip() is None
    for item in z.infolist():
        target=Path(z.extract(item,folder));mode=(item.external_attr>>16)&0o7777
        if mode:target.chmod(mode)
app=next((folder/'Payload').glob('*.app'))
ent=root/'request.plist';ent.write_bytes(plistlib.dumps({'com.apple.developer.kernel.increased-memory-limit':True}))
subprocess.run(['codesign','--force','--sign','-','--entitlements',str(ent),'--generate-entitlement-der',str(app)],check=True)
subprocess.run(['codesign','--verify','--deep','--strict',str(app)],check=True)
actual=subprocess.run(['codesign','--display','--entitlements',':-',str(app)],check=True,capture_output=True).stdout
assert plistlib.loads(actual)['com.apple.developer.kernel.increased-memory-limit'] is True
output=root/'MemoryRequest.ipa'
with zipfile.ZipFile(output,'w',allowZip64=True) as z:
    for p in sorted(folder.rglob('*')):
        if p.is_file():z.write(p,p.relative_to(folder).as_posix(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=1)
with zipfile.ZipFile(output) as z:assert z.testzip() is None
(root/'MemoryRequest.sha256').write_text(hashlib.file_digest(output.open('rb'),'sha256').hexdigest()+'  MemoryRequest.ipa\n')
print('Standard increased-memory request embedded and ad-hoc signature verified. No developer credentials used.',flush=True)
