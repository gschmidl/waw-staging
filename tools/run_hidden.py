"""Run a program on a private Windows desktop: its windows never reach the user's screen or take focus.

    python run_hidden.py [--timeout SECONDS] [--desktop NAME] -- PROGRAM [ARGS...]
Prints the program's exit code; kills it (by its own PID) after the timeout.
"""
import argparse
import ctypes
import subprocess
import sys
from ctypes import wintypes

user32 = ctypes.WinDLL('user32', use_last_error=True)
kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
user32.CreateDesktopW.restype = wintypes.HANDLE
user32.CreateDesktopW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR, ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p]
GENERIC_ALL = 0x10000000


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
    ap.add_argument('--timeout', type=float, default=120)
    ap.add_argument('--desktop', default='waw-test')
    ap.add_argument('cmd', nargs=argparse.REMAINDER)
    a = ap.parse_args()
    cmd = a.cmd[1:] if a.cmd and a.cmd[0] == '--' else a.cmd
    desk = user32.CreateDesktopW(a.desktop, None, None, 0, GENERIC_ALL, None)
    if not desk:
        raise SystemExit(f'CreateDesktop failed: {ctypes.get_last_error()}')
    si = STARTUPINFO()
    si.cb = ctypes.sizeof(si)
    si.lpDesktop = a.desktop
    pi = PROCESS_INFORMATION()
    cmdline = subprocess.list2cmdline(cmd)
    ok = kernel32.CreateProcessW(None, ctypes.create_unicode_buffer(cmdline), None, None, False, 0, None, None,
                                 ctypes.byref(si), ctypes.byref(pi))
    if not ok:
        raise SystemExit(f'CreateProcess failed: {ctypes.get_last_error()}')
    print(f'PID {pi.dwProcessId} on desktop {a.desktop}', flush=True)
    r = kernel32.WaitForSingleObject(pi.hProcess, int(a.timeout * 1000))
    if r != 0:
        kernel32.TerminateProcess(pi.hProcess, 99)
        print('timeout: killed PID', pi.dwProcessId)
    code = wintypes.DWORD()
    kernel32.GetExitCodeProcess(pi.hProcess, ctypes.byref(code))
    kernel32.CloseHandle(pi.hThread)
    kernel32.CloseHandle(pi.hProcess)
    user32.CloseDesktop(desk)
    print('exit code', code.value)
    sys.exit(0 if code.value == 0 else 1)


if __name__ == '__main__':
    main()
