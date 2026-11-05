from pathlib import Path
import os, plistlib, subprocess, zipfile
root = Path(os.environ['RUNNER_TEMP']) / 'tv-gpu-probe'
app = root / 'Payload/Probe.app'
app.mkdir(parents=True, exist_ok=True)
plist = {
    'CFBundleIdentifier':'org.nxnative.tv.0100b99019412000',
    'CFBundleName':'Probe','CFBundleDisplayName':'Mario vs. Donkey Kong',
    'CFBundleExecutable':'Probe','CFBundleVersion':'1','CFBundleShortVersionString':'0.1',
    'CFBundlePackageType':'APPL','CFBundleSupportedPlatforms':['AppleTVOS'],
    'UIDeviceFamily':[3],'MinimumOSVersion':'18.0','LSRequiresIPhoneOS':True,
    'UILaunchStoryboardName':'','UIFileSharingEnabled':True,
    'GCSupportsControllerUserInteraction':True,
}
(app/'Info.plist').write_bytes(plistlib.dumps(plist))
sdk = subprocess.check_output(['xcrun','--sdk','appletvos','--show-sdk-path'], text=True).strip()
subprocess.run(['xcrun','--sdk','appletvos','clang','-target','arm64-apple-tvos18.0','-isysroot',sdk,
    '-fobjc-arc','-O2','-framework','UIKit','-framework','Metal','-framework','Foundation',
    'gpu_probe.m','-o',str(app/'Probe')],check=True)
ipa = root/'TVGraphicsProbe.ipa'
with zipfile.ZipFile(ipa,'w',zipfile.ZIP_DEFLATED) as archive:
    for file in app.iterdir(): archive.write(file,file.relative_to(root).as_posix())
print(ipa)
