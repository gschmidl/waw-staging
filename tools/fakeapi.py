"""Serve DOSBox Staging's memory API from a RAM dump (test tool: UI work without a running DOSBox).

    python fakeapi.py RAM.bin [--port 18099]

Answers GET /api/v1/memory/{off}/{len}, PUT /api/v1/memory/{off} (kept in memory only), GET /api/v1/dosbox/info
and GET /api/v1/dos/internals with Staging 0.84's DOS addresses, like tools/api074.py does for a DOSBox 0.74
process. Dumps come from `wawprobe dump` (tools/gamecheck.sh saves one per game).
"""
import argparse
import json
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('dump')
    ap.add_argument('--port', type=int, default=18099)
    a = ap.parse_args()
    ram = bytearray(open(a.dump, 'rb').read())
    print(f'{a.dump}: {len(ram)} bytes on port {a.port}', flush=True)

    class H(BaseHTTPRequestHandler):
        protocol_version = 'HTTP/1.1'

        def log_message(self, *args):
            pass

        def send(self, code, body, ctype='application/json'):
            if isinstance(body, str):
                body = body.encode()
            self.send_response(code)
            self.send_header('Content-Type', ctype)
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            m = re.match(r'^/api/v1/memory/(\d+)/(\d+)$', self.path)
            if m:
                off, n = int(m.group(1)), int(m.group(2))
                if off + n > len(ram):
                    return self.send(500, json.dumps({'error': 'Failed to execute command: memory region exceeds '
                                                               f'emulated memory size ({len(ram)} bytes)'}))
                return self.send(200, bytes(ram[off:off + n]), 'application/octet-stream')
            if self.path == '/api/v1/dosbox/info':
                return self.send(200, json.dumps({'version': '0.84.0 (fakeapi ' + a.dump.replace('\\', '/').split('/')[-1] + ')',
                                                  'configHome': '', 'configWebserver': ''}))
            if self.path == '/api/v1/dos/internals':
                return self.send(200, json.dumps({'listOfLists': 0x826, 'dosSwappableArea': 0xB20}))
            self.send(404, '{"error":"not found"}')

        def do_PUT(self):
            m = re.match(r'^/api/v1/memory/(\d+)$', self.path)
            n = int(self.headers.get('Content-Length', '0'))
            data = self.rfile.read(n)
            if not m:
                return self.send(404, '{"error":"not found"}')
            off = int(m.group(1))
            if off + n > len(ram):
                return self.send(500, json.dumps({'error': 'memory region exceeds emulated memory size'}))
            ram[off:off + n] = data
            return self.send(200, '{}')

    # no SO_REUSEADDR: on Windows it lets a second server bind a port that is in use, and the old one kept answering
    ThreadingHTTPServer.allow_reuse_address = False
    ThreadingHTTPServer(('127.0.0.1', a.port), H).serve_forever()


if __name__ == '__main__':
    sys.exit(main())
