"""Honor BGRA/BGRX client textures when copying RGBA-decoded movie frames."""
HELPER='''static void md_copy_bgra(uint8_t *dst, size_t dst_row, const uint8_t *src, size_t src_row, int w, int h, int opaque) {
    for (int y = 0; y < h; y++) {
        const uint8_t *s = src + (size_t)y * src_row;
        uint8_t *t = dst + (size_t)y * dst_row;
        for (int x = 0; x < w; x++) {
            t[4*x] = s[4*x+2]; t[4*x+1] = s[4*x+1];
            t[4*x+2] = s[4*x]; t[4*x+3] = opaque ? 255 : s[4*x+3];
        }
    }
}
'''
def apply(repo):
    p=repo/'dm/host/hle_movie.c';s=p.read_text()
    marker='static int md_out_tex(mdec_t *d, int i, void *buf) {'
    assert s.count(marker)==1;s=s.replace(marker,HELPER+marker)
    old='if (f != 0x25 && f != 0x38 && f != 0x6d && f != 0x37 && !d->red_img++)'
    new='int bgra = f == 0x99 || f == 0x9a || f == 0x9b || f == 0x9c;\n    if (!bgra && f != 0x25 && f != 0x38 && f != 0x6d && f != 0x37 && !d->red_img++)'
    assert old in s;s=s.replace(old,new)
    old='if (d->out[i].pic && d->out[i].frm) nvn_host_write_texture(tex, d->out[i].frm, w, h, (size_t)d->w * 4, NULL, NULL);'
    new='''if (d->out[i].pic && d->out[i].frm) {
        if (bgra) {
            size_t row = (size_t)w * 4;
            uint8_t *converted = malloc(row * (size_t)h);
            if (!converted) return 0x1000;
            md_copy_bgra(converted, row, d->out[i].frm, (size_t)d->w * 4, w, h, f == 0x99 || f == 0x9b);
            nvn_host_write_texture(tex, converted, w, h, row, NULL, NULL);
            free(converted);
        } else nvn_host_write_texture(tex, d->out[i].frm, w, h, (size_t)d->w * 4, NULL, NULL);
    }'''
    assert old in s;s=s.replace(old,new);p.write_text(s)
