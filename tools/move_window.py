"""Move a process's top-level window to the given screen position (e.g. the left monitor) and keep it there.

    python move_window.py PID X Y [--timeout 30]
Waits for the window to appear, then moves it (without activating it) until its position sticks.
"""
import argparse
import ctypes
import time
from ctypes import wintypes

user32 = ctypes.WinDLL('user32', use_last_error=True)
SWP_NOSIZE, SWP_NOZORDER, SWP_NOACTIVATE = 0x1, 0x4, 0x10


def find_window(pid):
    found = []
    proc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def cb(hwnd, _):
        p = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(p))
        if p.value == pid and user32.IsWindowVisible(hwnd) and not user32.GetWindow(hwnd, 4):
            found.append(hwnd)
            return False
        return True

    user32.EnumWindows(proc(cb), 0)
    return found[0] if found else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('pid', type=int)
    ap.add_argument('x', type=int)
    ap.add_argument('y', type=int)
    ap.add_argument('--timeout', type=float, default=30)
    a = ap.parse_args()
    end = time.time() + a.timeout
    hwnd = None
    while time.time() < end and not hwnd:
        hwnd = find_window(a.pid)
        time.sleep(0.2)
    if not hwnd:
        raise SystemExit(f'no window for PID {a.pid}')
    rect = wintypes.RECT()
    for _ in range(20):
        user32.SetWindowPos(hwnd, None, a.x, a.y, 0, 0, SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE)
        time.sleep(0.3)
        user32.GetWindowRect(hwnd, ctypes.byref(rect))
        if (rect.left, rect.top) == (a.x, a.y):
            break
    print(f'window at {rect.left},{rect.top} size {rect.right - rect.left}x{rect.bottom - rect.top}')


if __name__ == '__main__':
    main()
