"""Allow local SSL context ownership while network I/O remains offline."""
def apply(repo):
    p=repo/'dm/host/hle_net.c';s=p.read_text()
    old='SSF("_ZN2nn3ssl7Context6CreateENS1_10SslVersionE", h_ssl_CtxCreate, void *self, int v) { (void)self; (void)v; return RES_FAIL; }'
    new='''// Context construction is a local resource operation, independent of network
// availability. Sparking ZERO's SpNet startup treats its failure as fatal.
// SDK 14 Context is one uint64_t (C1 zeros it; D1 is empty). A context's own
// address is its unique opaque offline ID; all transport/handshake calls below
// continue to fail, so this does not create a connection or bypass TLS checks.
HLE_FORCE("_ZN2nn3ssl7Context6CreateENS1_10SslVersionE", "local offline SSL context allocation", Result, h_ssl_CtxCreate, void *self, int v) {
    (void)v;
    if (!v || !self || *(uint64_t *)self) return RES_FAIL;
    *(uint64_t *)self = (uint64_t)(uintptr_t)self;
    LOG("ssl: created local offline context");
    return RES_OK;
}'''
    assert old in s;s=s.replace(old,new)
    old='SSF("_ZN2nn3ssl7Context7DestroyEv", h_ssl_CtxDestroy, void *self) { (void)self; return RES_FAIL; }'
    new='''HLE_FORCE("_ZN2nn3ssl7Context7DestroyEv", "release local offline SSL context", Result, h_ssl_CtxDestroy, void *self) {
    if (!self || *(uint64_t *)self != (uint64_t)(uintptr_t)self) return RES_FAIL;
    *(uint64_t *)self = 0;
    return RES_OK;
}'''
    assert old in s;s=s.replace(old,new);p.write_text(s)
