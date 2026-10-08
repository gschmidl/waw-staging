"""Put the WinForms and Majorsilence captures of the same window side by side (one PNG per window).

    python sidebyside.py WIN_DIR MSF_DIR OUT_DIR [--prefix 08_] [--scale 0.6]
"""
import argparse
import os

from PIL import Image, ImageDraw


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('win')
    ap.add_argument('msf')
    ap.add_argument('out')
    ap.add_argument('--prefix', default='')
    ap.add_argument('--scale', type=float, default=0.6)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    for name in sorted(os.listdir(a.win)):
        if not name.endswith('.png') or not name.startswith(a.prefix):
            continue
        p2 = os.path.join(a.msf, name)
        if not os.path.exists(p2):
            continue
        im1 = Image.open(os.path.join(a.win, name)).convert('RGB')
        im2 = Image.open(p2).convert('RGB')
        im1 = im1.resize((int(im1.width * a.scale), int(im1.height * a.scale)), Image.LANCZOS)
        im2 = im2.resize((int(im2.width * a.scale), int(im2.height * a.scale)), Image.LANCZOS)
        out = Image.new('RGB', (im1.width + im2.width + 12, max(im1.height, im2.height) + 18), 'white')
        out.paste(im1, (0, 18))
        out.paste(im2, (im1.width + 12, 18))
        d = ImageDraw.Draw(out)
        d.text((4, 2), 'WinForms', fill='black')
        d.text((im1.width + 16, 2), 'Majorsilence', fill='black')
        out.save(os.path.join(a.out, name))
        print(name, out.size)


if __name__ == '__main__':
    main()
