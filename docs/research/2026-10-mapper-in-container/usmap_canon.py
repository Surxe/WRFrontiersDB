"""Decode an uncompressed .usmap (v>=3) into a canonical, order-independent form and hash it."""
import hashlib, json, struct, sys

def canon(path):
    b = open(path, 'rb').read()
    magic, ver = struct.unpack_from('<HB', b, 0)
    assert magic == 0x30C4, hex(magic)
    has_ver, = struct.unpack_from('<i', b, 3); assert has_ver == 0
    comp, csize, dsize = struct.unpack_from('<BII', b, 7); assert comp == 0 and csize == dsize
    o = 16
    def u(fmt):
        nonlocal o; v = struct.unpack_from('<' + fmt, b, o); o += struct.calcsize('<' + fmt); return v[0]
    names = []
    for _ in range(u('I')):
        n = u('H') if ver >= 2 else u('B'); names.append(b[o:o + n].decode('utf-8', 'replace')); o += n
    nm = lambda i: None if i == 0xFFFFFFFF else names[i]
    enums = {}; enum_order = []; struct_order = []
    for _ in range(u('I')):
        en = nm(u('I')); cnt = u('H') if ver >= 3 else u('B'); ents = []
        for i in range(cnt):
            if ver >= 4: v = u('q'); ents.append((v, nm(u('I'))))
            else: ents.append((i, nm(u('I'))))
        enums[en] = sorted(ents); enum_order.append(en)
    def ptype():
        t = u('B')
        if t == 26: return ['Enum', ptype(), nm(u('I'))]
        if t == 9: return ['Struct', nm(u('I'))]
        if t in (8, 25, 28): return [t, ptype()]
        if t == 24: return ['Map', ptype(), ptype()]
        return [t]
    structs = {}
    for _ in range(u('I')):
        sn = nm(u('I')); sup = nm(u('I')); pc = u('H'); sc = u('H'); props = []
        for _ in range(sc):
            idx = u('H'); dim = u('B'); pn = nm(u('I')); props.append([idx, dim, pn, ptype()])
        structs[sn] = [sup, pc, sorted(props, key=lambda p: p[0])]; struct_order.append(sn)
    ext = {}
    if o < 16 + dsize:
        assert b[o:o + 4] == b'CEXT'; o += 4; u('B')
        for _ in range(u('I')):
            tag = b[o:o + 4].decode(); o += 4; sz = u('I'); ext[tag] = (sz, b[o:o + sz]); o += sz
    assert o == 16 + dsize, (o, dsize)
    assert len(set(enum_order)) == len(enum_order) and len(set(struct_order)) == len(struct_order)
    # PPTH / EATR (UE4SS): per-enum then per-struct records in body order; re-key them by name.
    def rd(raw):
        q = 0
        def r(fmt):
            nonlocal q; v = struct.unpack_from('<' + fmt, raw, q); q += struct.calcsize('<' + fmt); return v[0]
        return r, lambda: q
    r, pos = rd(ext['PPTH'][1]); assert r('B') == 0
    assert r('I') == len(enum_order); ppth_e = {e: names[r('i')] for e in enum_order}
    assert r('I') == len(struct_order); ppth_s = {sn: names[r('i')] for sn in struct_order}
    assert pos() == ext['PPTH'][0]
    r, pos = rd(ext['EATR'][1]); assert r('B') == 0
    assert r('I') == len(enum_order); eatr_e = {e: r('i') for e in enum_order}
    assert r('I') == len(struct_order); eatr_s = {}
    for sn in struct_order:
        kind = r('B'); flags = r('i'); eatr_s[sn] = [kind, flags, [r('Q') for _ in range(r('I'))]]
    assert pos() == ext['EATR'][0]
    doc = json.dumps({'enums': enums, 'structs': structs, 'ppth': [ppth_e, ppth_s],
                      'eatr': [eatr_e, eatr_s]}, sort_keys=True).encode()
    return (ver, len(names), len(enums), len(structs), hashlib.sha256(doc).hexdigest()[:16],
            {t: (sz, hashlib.sha256(raw).hexdigest()[:12]) for t, (sz, raw) in ext.items()})

for p in sys.argv[1:]:
    print(p.rsplit('/', 1)[-1], *canon(p))
