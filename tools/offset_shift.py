"""Measure where a game's memory offsets moved between two builds, from RAM dumps in the same game state.

    python offset_shift.py REF.bin REF_SIG NEW.bin NEW_SIG OFFSETS.json [--window 4096] [--len 16]
For each named offset (relative to the signature), takes LEN bytes at REF_SIG+offset in the reference dump
and looks for them near NEW_SIG+offset in the other; prints the shift when the match is unique.
"""
import argparse
import json


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('ref')
    ap.add_argument('ref_sig', type=lambda s: int(s, 0))
    ap.add_argument('new')
    ap.add_argument('new_sig', type=lambda s: int(s, 0))
    ap.add_argument('offsets')
    ap.add_argument('--window', type=int, default=4096)
    ap.add_argument('--len', type=int, default=16)
    a = ap.parse_args()
    ref, new = open(a.ref, 'rb').read(), open(a.new, 'rb').read()
    offs = json.load(open(a.offsets))
    for name, off in sorted(offs.items(), key=lambda kv: kv[1]):
        p = a.ref_sig + off
        if p < 0 or p + a.len > len(ref):
            continue
        pat = ref[p:p + a.len]
        if len(set(pat)) < 3:
            print(f'{name:28s} {off:8d}  (too uniform: {pat.hex()})')
            continue
        q0 = a.new_sig + off - a.window
        hits = []
        i = new.find(pat, max(0, q0), a.new_sig + off + a.window + a.len)
        while i >= 0:
            hits.append(i - (a.new_sig + off))
            i = new.find(pat, i + 1, a.new_sig + off + a.window + a.len)
        print(f'{name:28s} {off:8d}  shift {hits if len(hits) != 1 else hits[0]}')


if __name__ == '__main__':
    main()
