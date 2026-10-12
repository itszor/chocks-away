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
$SS/tools/weave.py extract, as recipe.json says (../build.sh).

The BASIC (!Chocks.ChocksAway, translated by $SS/tools/bas2c.py into
recomp/basic.c) starts with DIM C% 549000, and every address in Variables
(the code, tables, buffers) lies inside that block: the code expects BASIC's
heap to start at TOP (PAGE &8F00 + the program's 29696 bytes = &10300).
recomp/bas.c's heap starts there too.
"""
import os
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

BASE = 0x11170
LOMEM = 0x10300                  # TOP: BASIC's heap, where DIM C% 549000 starts


def var(name, k):
    """word k of !Chocks.Variables (or Variables2)"""
    return struct.unpack_from('<I', open(find(CHOCKS, name), 'rb').read(), k * 4)[0]


def blobs():
    """(file in !Chocks, address): SETUP's *LOADs and the BASIC's, lines 710-780"""
    v = lambda k: var('Variables', k)
    return [('Code2', 0x11170), ('Code', 0x1ADB0),             # SETUP: *LOAD ... 11170 / 1ADB0
            ('Cosine', v(39) - 2000), ('Sine', v(38) - 2000),   # CO-2000, SI-2000
            ('Atn', v(37)), ('Rand', v(2)), ('Dots2', v(3)),    # TAG, RAND, GANG
            ('Divide', v(13) - 1000), ('!Bicode', v(1))]        # DIIVDATA-1000, GRAPHIC


def mix_address():
    """MIX: the BASIC's DIMs in order from LOMEM, as recomp/bas.c makes them
    (DIM x n takes n+1 bytes, rounded up to a word)"""
    a = LOMEM
    for n in (549000, 100, 2400):                # C%, SPARE, HIGHSCORES
        a = (a + n + 1 + 3) & ~3
    return a


# CALL targets: CODE% (VR!0), CODE2% (70000), JOYSTICK (VR!80), CONTINUE
# (VR!120), CONTINUE2 (Variables2!56)
def call_roots():
    return sorted({var('Variables', 0), 70000, var('Variables', 20), var('Variables', 30),
                   var('Variables2', 14)})


# the modules the !Setup loader RMLOADs, in its order, each in its own 64K
# of RMA from &1840000
MODULES = ['Joystick', 'GUNMD2', 'WHEELMD', 'EXPLODEMD2', 'EXPLODEMD3', 'ENGINE']


def modules():
    """(name, path in game/, base)"""
    return [(m.lower(), os.path.relpath(find(os.path.join(CHOCKS, 'Sounds'), m), GAME), 0x1840000 + k * 0x10000)
            for k, m in enumerate(MODULES)]


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
    bl = [(n, a, open(find(CHOCKS, n), 'rb').read()) for n, a in blobs()]
    end = max(a + len(d) for _, a, d in bl)
    core = bytearray(end - BASE)
    for n, a, d in sorted(bl, key=lambda b: b[1]):
        core[a - BASE:a - BASE + len(d)] = d
        print('  %-8s &%05X-&%05X' % (n, a, a + len(d)))
    open(os.path.join(UNP, 'core'), 'wb').write(core)
    shutil.copy(find(CHOCKS, 'Mix'), os.path.join(UNP, 'mix'))
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
