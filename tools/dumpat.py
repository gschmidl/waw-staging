"""List the controls of a wawshot control-tree dump (ControlDump.cs) that contain a client point, with
absolute bounds; or with --name, the controls whose path contains a string.

    python dumpat.py DUMP.txt X Y
    python dumpat.py DUMP.txt --name labelSpellbook
"""
import re
import sys

LINE = re.compile(r'^(\S+) (\S+) (-?\d+),(-?\d+) (-?\d+)x(-?\d+) (.*)$')


def load(path):
    origin = {'': (0, 0)}
    out = []
    for line in open(path, encoding='utf-8'):
        m = LINE.match(line.rstrip('\n'))
        if not m:
            continue
        p, typ = m.group(1), m.group(2)
        x, y, w, h = (int(m.group(i)) for i in range(3, 7))
        parent = p.rsplit('/', 1)[0]
        ox, oy = origin.get(parent, (0, 0))
        ax, ay = ox + x, oy + y
        origin[p] = (ax, ay)
        out.append((p, typ, ax, ay, w, h, m.group(7)))
    return out


def main():
    rows = load(sys.argv[1])
    if sys.argv[2] == '--name':
        sel = [r for r in rows if sys.argv[3] in r[0]]
    else:
        px, py = int(sys.argv[2]), int(sys.argv[3])
        sel = [r for r in rows if r[2] <= px < r[2] + r[4] and r[3] <= py < r[3] + r[5] and 'hidden' not in r[6]]
    for p, typ, x, y, w, h, rest in sel:
        print(f'{x},{y} {w}x{h} {typ} {p.rsplit("/", 1)[-1]} {rest[:80]}')


if __name__ == '__main__':
    main()
