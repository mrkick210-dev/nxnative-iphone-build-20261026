"""Scan only packs that supply shaders in the registered, matching game build."""
import json, os, sys
from pathlib import Path

if __name__ == '__main__':
    repo, root = map(lambda x: Path(x).resolve(),sys.argv[1:3])
    sys.path.insert(0,str(repo/'dm/gfx/tools'))
    import shader_split
    packs=json.loads((root/'selected-packs.json').read_text())
    path=str(root/'data/RomFS/arc/data.trpfs')
    def selected(files,parts=64):
        step=max(1,(len(packs)+parts-1)//parts)
        return [(path,'arc/data.trpfs',tuple(tuple(p) for p in packs[i:i+step])) for i in range(0,len(packs),step)],{path,path[:-1]+'d'}
    shader_split.trpfs_jobs=selected
    profile=root/'profiles/0100F43008C44000'
    wanted={ln.split('\t')[3] for ln in (profile/'shader_map.tsv').read_text().splitlines() if ln and not ln.startswith('#') and not ln.startswith('package\t')}
    sys.argv=['shader_split.py',str(root/'data/RomFS'),str(root/'data/ExeFS/main'),str(root/'shader/pkg'),str(profile/'shader_map.tsv'),str(profile/'shader_facts.tsv'),str(profile/'shader_pairs.tsv'),str(profile/'pso_pairs.tsv'),str(root/'aoc/2')]
    shader_split.main()
    actual={ln.split('\t')[3] for ln in (profile/'shader_map.tsv').read_text().splitlines() if ln and not ln.startswith('#') and not ln.startswith('package\t')}
    if not wanted <= actual: raise RuntimeError(f'Shader scan missing {len(wanted-actual)} registered keys')
    print(f'All {len(wanted)} registered shader keys verified; {len(actual)} shaders extracted.',flush=True)
