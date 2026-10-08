"""Render a DOSBox Staging guest's 320x200 256-colour screen (mode 13h, A0000) to a PNG through the API,
with the standard VGA palette (good enough to read text and menus when the window isn't visible).

    python vgashot.py OUT.png [--port 18086]
"""
import argparse
import http.client
import zlib
import struct


def vga_palette():
    pal = []
    base16 = [(0, 0, 0), (0, 0, 170), (0, 170, 0), (0, 170, 170), (170, 0, 0), (170, 0, 170), (170, 85, 0),
              (170, 170, 170), (85, 85, 85), (85, 85, 255), (85, 255, 85), (85, 255, 255), (255, 85, 85),
              (255, 85, 255), (255, 255, 85), (255, 255, 255)]
    pal += base16
    for i in range(16):
        v = i * 17
        pal.append((v, v, v))
    while len(pal) < 256:
        i = len(pal)
        pal.append(((i * 53) % 256, (i * 97) % 256, (i * 151) % 256))
    return pal


def png(path, w, h, rgb):
    raw = b''.join(b'\0' + rgb[y * w * 3:(y + 1) * w * 3] for y in range(h))

    def chunk(t, d):
        return struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d))
    with open(path, 'wb') as f:
        f.write(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0))
                + chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b''))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('out')
    ap.add_argument('--port', type=int, default=18086)
    a = ap.parse_args()
    c = http.client.HTTPConnection('127.0.0.1', a.port, timeout=5)
    c.request('GET', f'/api/v1/memory/{0xA0000}/{64000}', headers={'Host': f'127.0.0.1:{a.port}'})
    vram = c.getresponse().read()
    pal = vga_palette()
    rgb = bytes(v for p in vram for v in pal[p])
    png(a.out, 320, 200, rgb)
    print(a.out)


if __name__ == '__main__':
    main()
