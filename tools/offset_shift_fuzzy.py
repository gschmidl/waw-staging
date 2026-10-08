"""Estimate the shift of individual offsets between two builds by window similarity (for data that changes a
little between the dumps or has no unique 16-byte pattern).

    python offset_shift_fuzzy.py REF.bin REF_SIG NEW.bin NEW_SIG OFFSET [OFFSET...] [--range -2500 600] [--win 128]
Prints the best few shifts with their equal-byte counts over a window centred on each offset.
"""
import argparse


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('ref')
    ap.add_argument('ref_sig', type=lambda s: int(s, 0))
    ap.add_argument('new')
    ap.add_argument('new_sig', type=lambda s: int(s, 0))
    ap.add_argument('offsets', nargs='+', type=int)
    ap.add_argument('--range', nargs=2, type=int, default=[-2500, 600])
    ap.add_argument('--win', type=int, default=128)
    a = ap.parse_args()
    ref, new = open(a.ref, 'rb').read(), open(a.new, 'rb').read()
    for off in a.offsets:
        p = a.ref_sig + off - a.win // 2
        w = ref[p:p + a.win]
        scores = []
        for s in range(a.range[0], a.range[1] + 1):
            q = a.new_sig + off + s - a.win // 2
            v = new[q:q + a.win]
            eq = sum(1 for x, y in zip(w, v) if x == y and x != 0)
            scores.append((eq, s))
        scores.sort(reverse=True)
        nonzero = sum(1 for x in w if x)
        print(f'{off:7d} nonzero={nonzero:3d} best: ' + ', '.join(f'{s:+d}({e})' for e, s in scores[:5]))


if __name__ == '__main__':
    main()
