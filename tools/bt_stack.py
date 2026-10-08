"""Print the Bard's Tale stack window Where Are We? classifies game states with (BT1 offsets by default).

    python bt_stack.py --port 18086 --sig 0x25FCE [--stack 54874] [--indicator 54758]
--sig is the linear address of the game's memory signature (wawprobe scan prints it).
"""
import argparse
import http.client
import struct


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--port', type=int, default=18086)
    ap.add_argument('--sig', type=lambda s: int(s, 0), required=True)
    ap.add_argument('--stack', type=int, default=54874)
    ap.add_argument('--indicator', type=int, default=54758)
    a = ap.parse_args()
    c = http.client.HTTPConnection('127.0.0.1', a.port, timeout=5)

    def rd(addr, n):
        c.request('GET', f'/api/v1/memory/{addr}/{n}', headers={'Host': f'127.0.0.1:{a.port}'})
        return c.getresponse().read()

    stack = rd(a.sig + a.stack - 512, 512)
    ind = struct.unpack('<H', rd(a.sig + a.indicator, 2))[0]
    print(f'indicator {ind} ({ind:#06x}), address adjust {1290 - ind}')
    for depth in range(120, 300, 2):
        v = struct.unpack_from('<h', stack, 512 - depth)[0]
        print(f'{depth:4d} {v:7d} {v + 1290 - ind:7d}')


if __name__ == '__main__':
    main()
