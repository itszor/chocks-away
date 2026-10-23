#!/usr/bin/env python3
"""The translated machine code of Chocks Away, and how it's made.

    images.py assemble  the blobs !Chocks.SETUP and the BASIC *LOAD at fixed
                        addresses -> unpacked/core, the memory from &11170
    images.py analyse   SuperSpider (analyse --full) on core, its roots the
                        addresses the BASIC CALLs (from !Chocks.Variables and
                        Variables2) -> analysis/core.json; on each module and
                        on Mix -> analysis/<name>.json
    images.py gen       their C translations -> recomp/gen/<name>/, plus
                        recomp/gen/modules.inc (game.c's module list)
    images.py roots LOG...   gap entries from --trace-gaps runs -> analysis/*.roots

game/ (!Chocks, !Maps: libroger's appdir) comes from the original discs:
$SS/tools/weave.py extract, as recipe.json says (../build.sh). From the
Compendium (Mark 2, 1991) Code, Code2, Variables, Variables2 and the BASIC
are in !Chocks.<160>, the directory ZFiler served them from (chocks()):
the same Code, Code2 and Variables, so the same translation. From the
Compendium's RISC OS 4 + StrongARM release (2000) too, one disc: there
!Chocks holds the maps as well (!Chocks.Maps), and nearly every file is
packed by the Fourth Dimension's DeComp module (its *CLoad unpacks them;
unpack() here): unpacked, Code, Code2 and the tables are the 1990 ones.

The BASIC (!Chocks.ChocksAway, translated by $SS/tools/bas2c.py into
recomp/basic.c) starts with DIM C% 549000, and every address in Variables
(the code, tables, buffers) lies inside that block: the code expects BASIC's
heap to start at TOP (PAGE &8F00 + the program's 29696 bytes = &10300).
The BASIC runtime's heap (BAS_LOMEM, written to recomp/gen/modules.inc for
game.c) starts there too, so Mix is where it was translated for: lomem()
and mix_address() read them from the BASIC, which is shorter in the later
releases (the 2000 one's also has DIM C% 526000).
"""
import os
import re
import shutil
import struct
import subprocess
import sys

TOP = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
SS = os.environ.get('SUPERSPIDER', os.path.expanduser('~/stuff/superspider'))
SSBIN = os.path.join(SS, '_build/default/bin/main.exe')
GAME = os.path.join(TOP, 'game')
UNP = os.path.join(TOP, 'unpacked')
AN = os.path.join(TOP, 'analysis')
CHOCKS = os.path.join(GAME, '!Chocks')
HIDDEN = os.path.join(CHOCKS, '\u00a0')    # !Chocks.<160>: the Mark 2's ZFiler files

BASE = 0x11170
PAGE = 0x8F00


def var(name, k):
    """word k of !Chocks.Variables (or Variables2)"""
    return struct.unpack_from('<I', data(name), k * 4)[0]


def packed():
    """the 2000 release: its files are DeComp's (the BASIC *CLoads them)"""
    try:
        return bool(find(os.path.join(CHOCKS, 'Sounds'), 'DeComp'))
    except FileNotFoundError:
        return False


def data(name):
    """a file of !Chocks as the BASIC loads it (unpacked, from the 2000 release)"""
    d = open(chocks(name), 'rb').read()
    return unpack(d) if packed() else d


def unpack(d):
    """a file packed for DeComp's *CLoad (the Fourth Dimension, 1993): its
    length (a word), then bits, least significant first: 0 and 8 bits, a
    byte; 1 and 9 bits, a match - an offset into the 512 bytes before
    (bytes before the start are 0) and its length, 9 bits for an offset
    below 256, 8 otherwise. It ends at the end of the file."""
    n = struct.unpack_from('<I', d)[0]
    bits = iter(b >> k & 1 for b in d[4:] for k in range(8))
    num = lambda w: sum(next(bits) << k for k in range(w))
    out = bytearray()
    try:
        while len(out) < n:
            if not next(bits):
                out.append(num(8))
                continue
            off = num(9)
            src = len(out) - 512 + off
            for k in range(num(9) if off < 256 else num(8)):
                out.append(out[src + k] if src + k >= 0 else 0)
    except StopIteration:
        pass
    return bytes(out[:n])


def chocks(name):
    """a file of !Chocks; the Mark 2's Code, Code2, Variables and BASIC are in !Chocks.<160>"""
    try:
        return find(CHOCKS, name)
    except FileNotFoundError:
        if os.path.isdir(HIDDEN):
            return find(HIDDEN, name)
        raise


def blobs():
    """(file in !Chocks, address): SETUP's *LOADs and the BASIC's, lines 710-780
    (the Mark 2's BASIC loads Code and Code2 itself, at the same addresses)"""
    v = lambda k: var('Variables', k)
    return [('Code2', 0x11170), ('Code', 0x1ADB0),             # SETUP: *LOAD ... 11170 / 1ADB0
            ('Cosine', v(39) - 2000), ('Sine', v(38) - 2000),   # CO-2000, SI-2000
            ('Atn', v(37)), ('Rand', v(2)), ('Dots2', v(3)),    # TAG, RAND, GANG
            ('Divide', v(13) - 1000), ('!Bicode', v(1))]        # DIIVDATA-1000, GRAPHIC


def lomem():
    """TOP, word-aligned: PAGE + the BASIC's length (&10300 in 1990)"""
    return (PAGE + os.path.getsize(chocks('ChocksAway')) + 3) & ~3


def mix_address():
    """MIX: the BASIC's DIMs in order from LOMEM, as the BASIC runtime makes them
    (DIM x n takes n+1 bytes, rounded up to a word): C% (549000 in 1990,
    526000 in 2000), SPARE 100, HIGHSCORES 2400"""
    c = int(re.search(rb'\xde C% (\d+)', open(chocks('ChocksAway'), 'rb').read()).group(1))
    a = lomem()
    for n in (c, 100, 2400):
        a = (a + n + 1 + 3) & ~3
    return a


# CALL targets: CODE% (VR!0), CODE2% (70000), JOYSTICK (VR!80), CONTINUE
# (VR!120), CONTINUE2 (Variables2!56)
def call_roots():
    return sorted({var('Variables', 0), 70000, var('Variables', 20), var('Variables', 30),
                   var('Variables2', 14)})


# the modules the !Setup loader RMLOADs (the 2000 release's !Run), in its
# order, each in its own 64K of RMA from &1840000; and the 2000 release's
# DeComp, whose *CLoad loads its files
MODULES = ['Joystick', 'GUNMD2', 'WHEELMD', 'EXPLODEMD2', 'EXPLODEMD3', 'ENGINE', 'DeComp']


def modules():
    """(name, path in game/, base)"""
    return [(m.lower(), os.path.relpath(find(os.path.join(CHOCKS, 'Sounds'), m), GAME), 0x1840000 + k * 0x10000)
            for k, m in enumerate(MODULES) if m != 'DeComp' or packed()]


def find(d, name):
    """a RISC OS file in a host directory: any case, any ,load-exec suffix"""
    for f in os.listdir(d):
        if f.split(',')[0].lower() == name.lower():
            return os.path.join(d, f)
    raise FileNotFoundError(os.path.join(d, name))


def run(cmd, **kw):
    print('+', ' '.join(cmd))
    subprocess.run(cmd, check=True, **kw)


# --- assemble, analyse, gen, roots
def assemble():
    os.makedirs(UNP, exist_ok=True)
    bl = [(n, a, data(n)) for n, a in blobs()]
    end = max(a + len(d) for _, a, d in bl)
    core = bytearray(end - BASE)
    for n, a, d in sorted(bl, key=lambda b: b[1]):
        core[a - BASE:a - BASE + len(d)] = d
        print('  %-8s &%05X-&%05X' % (n, a, a + len(d)))
    open(os.path.join(UNP, 'core'), 'wb').write(core)
    open(os.path.join(UNP, 'mix'), 'wb').write(data('Mix'))
    print('core: &%X-&%X; Mix at &%X' % (BASE, end, mix_address()))


def analyse():
    os.makedirs(AN, exist_ok=True)
    roots = os.path.join(AN, 'core.roots')
    calls = os.path.join(AN, 'calls.roots')
    with open(calls, 'w') as f:
        f.write('# the addresses the BASIC CALLs (images.py call_roots)\n')
        f.writelines('%x\n' % a for a in call_roots())
    if not os.path.exists(roots):
        open(roots, 'w').write('# gap entries from --trace-gaps runs (images.py roots)\n')
    merged = os.path.join(AN, 'all.roots')
    open(merged, 'w').write(open(calls).read() + open(roots).read())
    run(['dune', 'build'], cwd=SS)
    run([SSBIN, 'analyse', os.path.join(UNP, 'core'), '%x' % BASE, '--full', '--roots', merged,
         '-o', os.path.join(AN, 'core.json')])
    run([SSBIN, 'analyse', os.path.join(UNP, 'mix'), '%x' % mix_address(), '--full',
         '-o', os.path.join(AN, 'mix.json')])
    for name, path, base in modules():
        rf = os.path.join(AN, name + '.roots')
        run([SSBIN, 'analyse', os.path.join(GAME, path), '%x' % base, '--module', '--full',
             '-o', os.path.join(AN, name + '.json')] + (['--roots', rf] if os.path.exists(rf) else []))


def gen():
    rc = os.path.join(TOP, 'recomp')
    shutil.rmtree(os.path.join(rc, 'gen'), ignore_errors=True)
    run([SSBIN, 'gen', os.path.join(UNP, 'core'), '%x' % BASE, os.path.join(AN, 'core.json'),
         '--c', os.path.join(rc, 'gen', 'core')])
    run([SSBIN, 'gen', os.path.join(UNP, 'mix'), '%x' % mix_address(), os.path.join(AN, 'mix.json'),
         '--c', os.path.join(rc, 'gen', 'mix'), '--prefix', 'X', '--tabprefix', 'recomp_mix', '--files', '1'])
    for k, (name, path, base) in enumerate(modules()):
        run([SSBIN, 'gen', os.path.join(GAME, path), '%x' % base, os.path.join(AN, name + '.json'),
             '--c', os.path.join(rc, 'gen', name), '--prefix', 'M%d' % k, '--tabprefix', 'recomp_' + name,
             '--files', '1', '--covtag', chr(ord('a') + k)])
    with open(os.path.join(rc, 'gen', 'modules.inc'), 'w') as f:
        f.write('/* generated by ../tools/images.py - the modules and Mix, for game.c */\n')
        for name, _, _ in modules():
            f.write('extern const struct roger_image recomp_%s_image;\n' % name)
        f.write('static const struct roger_module modules[] = {\n')
        for name, path, _ in modules():
            f.write('    {"../game/%s", &recomp_%s_image, 1},\n' % (path, name))
        f.write('    {NULL, NULL, 0}};\n')
        f.write('#define MIX_ADDRESS 0x%X\n' % mix_address())
        f.write('#define BAS_LOMEM 0x%X\n' % lomem())


def roots(logs):
    run([sys.executable, os.path.join(SS, 'tools/gap_roots.py'), os.path.join(UNP, 'core'), '%x' % BASE,
         os.path.join(AN, 'core.roots')] + logs)
    for name, path, base in modules():
        run([sys.executable, os.path.join(SS, 'tools/gap_roots.py'), os.path.join(GAME, path), '%x' % base,
             os.path.join(AN, name + '.roots')] + logs)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    if sys.argv[1] == 'roots':
        roots(sys.argv[2:])
    else:
        for step in sys.argv[1:]:
            {'assemble': assemble, 'analyse': analyse, 'gen': gen}[step]()
