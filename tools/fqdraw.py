"""Rewrite fully-qualified System.Drawing.X (GDI+ types) to Majorsilence.Forms.Drawing.X in a source tree.

Types in System.Drawing.Primitives (cross-platform in .NET) are left alone.
"""
import os
import re
import sys

PRIMITIVES = {'Point', 'PointF', 'Size', 'SizeF', 'Rectangle', 'RectangleF', 'Color', 'KnownColor',
              'SystemColors', 'ColorTranslator'}
pat = re.compile(r'(?<![\w.])(?:global::)?System\.Drawing\.((?:Drawing2D|Imaging|Text)\.)?([A-Z]\w*)')


def repl(m):
    sub, name = m.group(1) or '', m.group(2)
    if not sub and name in PRIMITIVES:
        return m.group(0)
    return f'Majorsilence.Forms.Drawing.{sub}{name}'


changed = 0
for dirpath, dirs, files in os.walk(sys.argv[1]):
    dirs[:] = [d for d in dirs if d not in ('bin', 'obj', '.git')]
    for f in files:
        if not f.endswith('.cs'):
            continue
        p = os.path.join(dirpath, f)
        s = open(p, encoding='utf-8-sig').read()
        t = pat.sub(repl, s)
        if t != s:
            open(p, 'w', encoding='utf-8').write(t)
            changed += 1
print('files changed:', changed)
