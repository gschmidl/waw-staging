"""Type keys into a DOS program through DOSBox Staging's HTTP API by filling the BIOS keyboard buffer.

    python bdakeys.py [--port 18086] [--delay 0.15] KEYS...

Each KEYS argument is literal text, or a {name} token: {enter} {esc} {space} {tab} {bs}
{up} {down} {left} {right} {f1}..{f10} {ctrl-a}..{ctrl-z}. Works for programs that read keys through INT 16h.
"""
import argparse
import http.client
import time

SCAN = {  # ASCII -> (scan code, ascii) on a US keyboard
    **{c: (s, ord(c)) for s, row in ((0x02, '1234567890'),) for s, c in zip(range(0x02, 0x0C), row)},
    **{c: (s, ord(c)) for c, s in zip('qwertyuiop', range(0x10, 0x1A))},
    **{c: (s, ord(c)) for c, s in zip('asdfghjkl', range(0x1E, 0x27))},
    **{c: (s, ord(c)) for c, s in zip('zxcvbnm', range(0x2C, 0x33))},
    ' ': (0x39, 0x20), '-': (0x0C, 0x2D), '=': (0x0D, 0x3D), ',': (0x33, 0x2C), '.': (0x34, 0x2E), '/': (0x35, 0x2F),
    ';': (0x27, 0x3B), "'": (0x28, 0x27), '[': (0x1A, 0x5B), ']': (0x1B, 0x5D), '\\': (0x2B, 0x5C), '`': (0x29, 0x60),
}
SHIFTED = dict(zip('!@#$%^&*()_+<>?:"{}|~', '1234567890-=,./;\'[]\\`'))
NAMED = {'enter': (0x1C, 0x0D), 'esc': (0x01, 0x1B), 'space': (0x39, 0x20), 'tab': (0x0F, 0x09), 'bs': (0x0E, 0x08),
         'up': (0x48, 0), 'down': (0x50, 0), 'left': (0x4B, 0), 'right': (0x4D, 0),
         **{f'f{i}': (0x3A + i, 0) for i in range(1, 11)}}


def keys_for(text):
    out, i = [], 0
    while i < len(text):
        if text[i] == '{' and '}' in text[i:]:
            j = text.index('}', i)
            name = text[i + 1:j].lower()
            if name.startswith('ctrl-') and len(name) == 6:
                out.append((SCAN[name[5]][0], ord(name[5]) - 96))
            else:
                out.append(NAMED[name])
            i = j + 1
            continue
        c = text[i]
        if c.isupper():
            out.append((SCAN[c.lower()][0], ord(c)))
        elif c in SHIFTED:
            out.append((SCAN[SHIFTED[c]][0], ord(c)))
        else:
            out.append(SCAN[c])
        i += 1
    return out


class Api:
    def __init__(self, port):
        self.conn = http.client.HTTPConnection('127.0.0.1', port, timeout=5)
        self.host = f'127.0.0.1:{port}'

    def read(self, addr, n):
        self.conn.request('GET', f'/api/v1/memory/{addr}/{n}', headers={'Host': self.host})
        r = self.conn.getresponse()
        data = r.read()
        if r.status != 200:
            raise RuntimeError(data)
        return data

    def write(self, addr, data):
        self.conn.request('PUT', f'/api/v1/memory/{addr}', body=data,
                          headers={'Host': self.host, 'Content-Type': 'application/octet-stream'})
        r = self.conn.getresponse()
        body = r.read()
        if r.status // 100 != 2:
            raise RuntimeError(body)


def push_key(api, scan, ascii_):
    """Append one key to the BDA ring buffer (0x41E..0x43D), waiting while it is full."""
    for _ in range(200):
        head, tail = (int.from_bytes(api.read(0x41A + i, 2), 'little') for i in (0, 2))
        nxt = tail + 2 if tail + 2 < 0x3E else 0x1E
        if nxt != head:
            api.write(0x400 + tail, bytes([ascii_, scan]))
            api.write(0x41C, nxt.to_bytes(2, 'little'))
            return
        time.sleep(0.02)
    raise RuntimeError('keyboard buffer stays full')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--port', type=int, default=18086)
    ap.add_argument('--delay', type=float, default=0.15)
    ap.add_argument('keys', nargs='+')
    args = ap.parse_args()
    api = Api(args.port)
    for text in args.keys:
        for scan, ascii_ in keys_for(text):
            push_key(api, scan, ascii_)
            time.sleep(args.delay)


if __name__ == '__main__':
    main()
