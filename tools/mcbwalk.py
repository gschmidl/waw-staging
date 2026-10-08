"""Walk the DOS memory control block chain of a running DOSBox Staging (or a RAM dump plus LoL address).

    python mcbwalk.py --port 18086
    python mcbwalk.py --dump ram.bin --lol 0x...     (listOfLists linear address from /api/v1/dos/internals)
Prints each MCB: segment, owner PSP, size, name, and the program path for PSP-owned environment blocks.
"""
import argparse
import http.client
import json


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--port', type=int, default=18086)
    ap.add_argument('--dump')
    ap.add_argument('--lol', type=lambda s: int(s, 0))
    a = ap.parse_args()
    if a.dump:
        ram = open(a.dump, 'rb').read()
        lol = a.lol
        rd = lambda addr, n: ram[addr:addr + n]
    else:
        c = http.client.HTTPConnection('127.0.0.1', a.port, timeout=5)
        host = {'Host': f'127.0.0.1:{a.port}'}

        def rd(addr, n):
            c.request('GET', f'/api/v1/memory/{addr}/{n}', headers=host)
            return c.getresponse().read()
        c.request('GET', '/api/v1/dos/internals', headers=host)
        info = json.loads(c.getresponse().read())
        lol = info['listOfLists']
        sda = info['dosSwappableArea']
        print('LoL', hex(lol), 'SDA', hex(sda), 'current PSP', hex(int.from_bytes(rd(sda + 0x10, 2), 'little')))
    seg = int.from_bytes(rd(lol - 2, 2), 'little')
    for _ in range(200):
        hdr = rd(seg * 16, 16)
        kind, owner, size = chr(hdr[0]), int.from_bytes(hdr[1:3], 'little'), int.from_bytes(hdr[3:5], 'little')
        name = bytes(b for b in hdr[8:16] if 32 <= b < 127).decode()
        extra = ''
        if owner and owner == seg + 1:
            env = int.from_bytes(rd((seg + 1) * 16 + 0x2C, 2), 'little')
            extra = f' PSP, env seg {env:04X}'
        print(f'{kind} seg {seg:04X} (lin {seg * 16:6X}) owner {owner:04X} size {size:5X} paras ({size * 16:7d} B) {name:8s}{extra}')
        if kind == 'Z':
            break
        seg += size + 1


if __name__ == '__main__':
    main()
