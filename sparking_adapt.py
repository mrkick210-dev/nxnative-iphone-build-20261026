"""Build-gated FMallocBinned3 adaptation, derived from the title's vtable and callers."""
BUILD='7b53433fa04477fc8a540bd80d5ce665'
PATCHES='''# Sparking ZERO 2.0.73: UE4 FMallocBinned3 reserves 37 GiB of sparse virtual space.
# iPhone address-space workaround: use NXNative's existing UE4 host heap.
# Both lazy constructor paths hold the newly allocated 0x1c38-byte object in x19.
CUTS = {'7b53433fa04477fc8a540bd80d5ce665': [
 (0x1dd0030, 'a3740194', '1f2003d5', 'FMallocBinned3 constructor -> host allocator'),
 (0x1dd0548, '5d730194', '1f2003d5', 'FMallocBinned3 constructor -> host allocator'),
]}
OBS = {'7b53433fa04477fc8a540bd80d5ce665': [
 (0x1dd0034, 21, 'f9035293', 'Install host allocator in x19 before publishing GMalloc'),
 (0x1dd054c, 21, 'f9035293', 'Install host allocator in x19 before publishing GMalloc'),
]}
'''
def apply(repo, profile):
    (profile/'patches.py').write_text(PATCHES)
    host=repo/'dm/host/hle_uemalloc.c';text=host.read_text()
    marker='static const struct { const char *build, *what; int layout; uint64_t obj, vtable, cut; } k_ue[] = {'
    assert text.count(marker)==1
    row='\n    // UE4 21-slot layout verified: TryMalloc/TryRealloc delegate to +0x18/+0x28; slots 17/18 return true.\n    { "'+BUILD+'", "Sparking ZERO 2.0.73", UE4_27, 0, 0x8646da8, 0x1dd0030 },'
    host.write_text(text.replace(marker,marker+row))
