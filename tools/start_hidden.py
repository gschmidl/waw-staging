"""Start a program on a private Windows desktop and return at once (its PID goes to a file).

    python start_hidden.py [--desktop waw-test] [--pidfile FILE] [--env NAME=VALUE ...] -- PROGRAM [ARGS...]
The program's windows never appear on the user's screen; the desktop lives as long as programs use it.
"""
import argparse
import ctypes
import os
import subprocess
from ctypes import wintypes

user32 = ctypes.WinDLL('user32', use_last_error=True)
kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
user32.CreateDesktopW.restype = wintypes.HANDLE
user32.CreateDesktopW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR, ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p]
GENERIC_ALL = 0x10000000
CREATE_UNICODE_ENVIRONMENT = 0x400


class STARTUPINFO(ctypes.Structure):
    _fields_ = [('cb', wintypes.DWORD), ('lpReserved', wintypes.LPWSTR), ('lpDesktop', wintypes.LPWSTR),
                ('lpTitle', wintypes.LPWSTR), ('dwX', wintypes.DWORD), ('dwY', wintypes.DWORD), ('dwXSize', wintypes.DWORD),
                ('dwYSize', wintypes.DWORD), ('dwXCountChars', wintypes.DWORD), ('dwYCountChars', wintypes.DWORD),
                ('dwFillAttribute', wintypes.DWORD), ('dwFlags', wintypes.DWORD), ('wShowWindow', wintypes.WORD),
                ('cbReserved2', wintypes.WORD), ('lpReserved2', ctypes.c_void_p), ('hStdInput', wintypes.HANDLE),
                ('hStdOutput', wintypes.HANDLE), ('hStdError', wintypes.HANDLE)]


class PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [('hProcess', wintypes.HANDLE), ('hThread', wintypes.HANDLE), ('dwProcessId', wintypes.DWORD), ('dwThreadId', wintypes.DWORD)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--desktop', default='waw-test')
    ap.add_argument('--pidfile')
    ap.add_argument('--cwd')
    ap.add_argument('--env', action='append', default=[])
    ap.add_argument('cmd', nargs=argparse.REMAINDER)
    a = ap.parse_args()
    cmd = a.cmd[1:] if a.cmd and a.cmd[0] == '--' else a.cmd
    if not user32.CreateDesktopW(a.desktop, None, None, 0, GENERIC_ALL, None):
        raise SystemExit(f'CreateDesktop failed: {ctypes.get_last_error()}')
    env = dict(os.environ)
    for item in a.env:
        k, _, v = item.partition('=')
        env[k] = v
    block = ''.join(f'{k}={v}\0' for k, v in env.items()) + '\0'
    si = STARTUPINFO()
    si.cb = ctypes.sizeof(si)
    si.lpDesktop = a.desktop
    pi = PROCESS_INFORMATION()
    env_arg = ctypes.create_unicode_buffer(block) if a.env else None
    if not kernel32.CreateProcessW(None, ctypes.create_unicode_buffer(subprocess.list2cmdline(cmd)), None, None, False,
                                   CREATE_UNICODE_ENVIRONMENT if a.env else 0, env_arg, a.cwd,
                                   ctypes.byref(si), ctypes.byref(pi)):
        raise SystemExit(f'CreateProcess failed: {ctypes.get_last_error()}')
    if a.pidfile:
        open(a.pidfile, 'w').write(str(pi.dwProcessId))
    # The desktop goes away with its last handle: hold ours until the program has a window on it.
    pid = pi.dwProcessId
    found = []
    proc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def cb(hwnd, _):
        p = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(p))
        if p.value == pid:
            found.append(hwnd)
            return False
        return True

    callback = proc(cb)
    user32.OpenDesktopW.restype = wintypes.HANDLE
    for _ in range(300):
        desk = user32.OpenDesktopW(a.desktop, 0, False, 0x0041)
        user32.EnumDesktopWindows(wintypes.HANDLE(desk), callback, 0)
        user32.CloseDesktop(wintypes.HANDLE(desk))
        if found or kernel32.WaitForSingleObject(pi.hProcess, 100) == 0:
            break
    alive = kernel32.WaitForSingleObject(pi.hProcess, 0) != 0
    print(f'PID {pid} on desktop {a.desktop}' + ('' if alive else ' (already exited)'))


if __name__ == '__main__':
    main()
