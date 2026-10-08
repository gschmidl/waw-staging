"""Search eXoDOS game zips for the memory signatures Where Are We? looks for."""
import base64, os, re, sys, zipfile

SIGS = {  # from tools/sigdump (WhereAreWe 1.2.0.0)
    'BT1': 'Tm90IGVub3VnaCBnb2xk', 'BT2': 'b24gdGhlIGRpc2s=', 'BT3': 'cmVmdWdlZSBjYW1w',
    'EOB1': 'AQBDOlxFT0IuRVhFAA==', 'EOB2': 'AQBDOlxTVEFSVC5FWEUA',
    'MM1': 'Tk8gU1BFTEwgUE9JTlRTAFNQRUxMIEZBSUxFRAA=', 'MM2': 'UC1Qcm90IFEtUXVpY2sA',
    'MM3': 'MDA3JXMgaXMgbm90', 'MM45': None, 'U1': 'QzpcVUxUSU1BLkVYRQ==',
    'Wiz1': 'V0laMS5EU0sgaXMgbWlzc2luZw==', 'Wiz1Old': 'b3JpZ2luYWwgV2l6YXJkcnk=',
    'Wiz2': 'V0laMi5EU0sgaXMgbWlzc2luZw==', 'Wiz3': 'V0laMy5EU0sgaXMgbWlzc2luZw==',
    'Wiz4': 'V0laNC5EU0sgaXMgbWlzc2luZw==', 'Wiz5': 'V0laNS5EU0sgaXMgbWlzc2luZw==',
}
pats = {k: base64.b64decode(v) for k, v in SIGS.items() if v}
pats['MM45'] = bytes([255, 203, 86, 150, 146, 133, 192, 116, 2, 247, 227, 227, 5, 145, 247, 230])
# EOB/Ultima signatures are the program path in the environment; also look for the bare name
pats['EOB1-name'] = b'EOB.EXE'; pats['EOB2-name'] = b'START.EXE'; pats['U1-name'] = b'ULTIMA.EXE'

root = sys.argv[1]
want = re.compile(sys.argv[2], re.I)
for name in sorted(os.listdir(root)):
    if not name.lower().endswith('.zip') or not want.search(name):
        continue
    hits = []
    with zipfile.ZipFile(os.path.join(root, name)) as z:
        for info in z.infolist():
            if info.is_dir() or info.file_size > 64 << 20:
                continue
            data = z.read(info)
            for k, p in pats.items():
                i = data.find(p)
                if i >= 0:
                    hits.append(f'{k}@{info.filename}+{i:#x}')
    print(f'{name}: ' + (', '.join(hits) if hits else '-'))
