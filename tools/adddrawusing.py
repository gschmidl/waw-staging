"""After `using System.Drawing[.Sub];` add `using Majorsilence.Forms.Drawing[.Sub];` when it is missing."""
import os
import re
import sys

pat = re.compile(r'^using System\.Drawing(\.(?:Drawing2D|Imaging|Text))?;\r?$', re.M)
changed = 0
for dirpath, dirs, files in os.walk(sys.argv[1]):
    dirs[:] = [d for d in dirs if d not in ('bin', 'obj', '.git')]
    for f in files:
        if not f.endswith('.cs'):
            continue
        p = os.path.join(dirpath, f)
        s = open(p, encoding='utf-8-sig').read()

        def repl(m):
            ms = f'using Majorsilence.Forms.Drawing{m.group(1) or ""};'
            return m.group(0) if ms in s else m.group(0) + '\n' + ms

        t = pat.sub(repl, s)
        if t != s:
            open(p, 'w', encoding='utf-8').write(t)
            changed += 1
print('files changed:', changed)
