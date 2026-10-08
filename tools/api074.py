"""Serve DOSBox Staging's memory API on top of a running DOSBox 0.74 process (Windows, test tool).

    python api074.py PID [--port 18087]

Finds the emulated RAM in the process (the committed region whose BIOS date string sits at F000:FFF5),
then answers GET /api/v1/memory/{off}/{len}, PUT /api/v1/memory/{off}, GET /api/v1/dosbox/info and
GET /api/v1/dos/internals like Staging does, so the port and the test tools can run against DOSBox 0.74
side by side with the original Where Are We?.
"""
import argparse
import ctypes
import json
import re
import sys
from ctypes import wintypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

k32 = ctypes.WinDLL('kernel32', use_last_error=True)
PROCESS_ALL = 0x0010 | 0x0020 | 0x0008 | 0x0400  # VM_READ | VM_WRITE | VM_OPERATION | QUERY_INFORMATION


class MBI(ctypes.Structure):
    _fields_ = [('BaseAddress', ctypes.c_void_p), ('AllocationBase', ctypes.c_void_p), ('AllocationProtect', wintypes.DWORD),
                ('PartitionId', wintypes.WORD), ('RegionSize', ctypes.c_size_t), ('State', wintypes.DWORD),
                ('Protect', wintypes.DWORD), ('Type', wintypes.DWORD)]


k32.OpenProcess.restype = wintypes.HANDLE
k32.VirtualQueryEx.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.POINTER(MBI), ctypes.c_size_t]
k32.VirtualQueryEx.restype = ctypes.c_size_t
k32.ReadProcessMemory.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
k32.WriteProcessMemory.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]


class Proc:
    def __init__(self, pid):
        self.h = k32.OpenProcess(PROCESS_ALL, False, pid)
        if not self.h:
            raise SystemExit(f'OpenProcess failed: {ctypes.get_last_error()}')

    def read(self, addr, n):
        buf = ctypes.create_string_buffer(n)
        got = ctypes.c_size_t()
        if not k32.ReadProcessMemory(self.h, addr, buf, n, ctypes.byref(got)) or got.value != n:
            return None
        return buf.raw

    def write(self, addr, data):
        got = ctypes.c_size_t()
        return bool(k32.WriteProcessMemory(self.h, addr, data, len(data), ctypes.byref(got))) and got.value == len(data)

    def regions(self):
        addr, mbi = 0, MBI()
        while k32.VirtualQueryEx(self.h, addr, ctypes.byref(mbi), ctypes.sizeof(mbi)):
            yield (mbi.BaseAddress or 0), mbi.RegionSize, mbi.State
            addr = (mbi.BaseAddress or 0) + mbi.RegionSize
            if addr >= 1 << 47:
                break


def find_ram(proc):
    """Emulated RAM: a committed region with DOSBox's BIOS date at linear F000:FFF5."""
    for base, size, state in proc.regions():
        if state != 0x1000 or size < 0x110000:
            continue
        for skew in range(0, 0x100, 8):
            if proc.read(base + skew + 0xFFFF5, 8) == b'01/01/92':
                return base + skew, size - skew
    raise SystemExit('emulated RAM not found')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('pid', type=int)
    ap.add_argument('--port', type=int, default=18087)
    a = ap.parse_args()
    proc = Proc(a.pid)
    ram, region = find_ram(proc)
    # memsize: the largest power-of-2-ish size whose last byte reads; DOSBox allocates memsize MB (+ padding)
    ramsize = region - region % 0x100000
    print(f'RAM at {ram:#x}, {ramsize} bytes (region {region})', flush=True)

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
                if off + n > ramsize:
                    return self.send(500, json.dumps({'error': f'Failed to execute command: memory region exceeds emulated memory size ({ramsize} bytes)'}))
                data = proc.read(ram + off, n)
                return self.send(200, data, 'application/octet-stream') if data is not None else self.send(500, '{"error":"read failed"}')
            if self.path == '/api/v1/dosbox/info':
                return self.send(200, json.dumps({'version': '0.74 (api074 bridge)', 'configHome': '', 'configWebserver': ''}))
            if self.path == '/api/v1/dos/internals':  # DOSBox 0.74: DOS_INFOBLOCK_SEG 0x80 (+0x26), DOS_SDA_SEG 0xb2, DOS_FIRST_SHELL 0x118
                return self.send(200, json.dumps({'listOfLists': 0x826, 'dosSwappableArea': 0xB20, 'firstShell': 0x1180}))
            self.send(404, '{"error":"not found"}')

        def do_PUT(self):
            m = re.match(r'^/api/v1/memory/(\d+)$', self.path)
            n = int(self.headers.get('Content-Length', '0'))
            data = self.rfile.read(n)
            if not m:
                return self.send(404, '{"error":"not found"}')
            off = int(m.group(1))
            if off + n > ramsize:
                return self.send(500, json.dumps({'error': 'memory region exceeds emulated memory size'}))
            return self.send(200, '{}') if proc.write(ram + off, data) else self.send(500, '{"error":"write failed"}')

    ThreadingHTTPServer(('127.0.0.1', a.port), H).serve_forever()


if __name__ == '__main__':
    sys.exit(main())
