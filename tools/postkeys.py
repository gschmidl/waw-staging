"""Post key presses to the top-level window of a process (Windows), e.g. DOSBox Staging's hotkeys.

    python postkeys.py PID KEY [KEY...]      KEY = name or combo like ctrl+f5, alt+enter, a, enter
A window on a private desktop is looked for on the desktop named by POSTKEYS_DESKTOP (default waw-test).
"""
import ctypes
import os
import sys
import time
from ctypes import wintypes

user32 = ctypes.WinDLL('user32', use_last_error=True)
WM_KEYDOWN, WM_KEYUP, WM_SYSKEYDOWN, WM_SYSKEYUP = 0x100, 0x101, 0x104, 0x105
VK = {'ctrl': 0x11, 'shift': 0x10, 'alt': 0x12, 'enter': 0x0D, 'esc': 0x1B, 'space': 0x20, 'tab': 0x09,
      'up': 0x26, 'down': 0x28, 'left': 0x25, 'right': 0x27, 'bs': 0x08,
      **{f'f{i}': 0x6F + i for i in range(1, 13)}}
EXTENDED = {0x26, 0x28, 0x25, 0x27}


def vk_of(name):
    if name in VK:
        return VK[name]
    if len(name) == 1:
        return ord(name.upper())
    raise SystemExit('unknown key ' + name)


def find_window(pid, desktop='waw-test'):
    """The process's visible top-level window, on the user's desktop or on the private test desktop."""
    found = []
    proc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def cb(hwnd, _):
        p = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(p))
        if p.value == pid and user32.IsWindowVisible(hwnd) and not user32.GetWindow(hwnd, 4):
            found.append(hwnd)
            return False
        return True

    callback = proc(cb)
    user32.EnumWindows(callback, 0)
    if not found:
        user32.OpenDesktopW.restype = wintypes.HANDLE
        desk = user32.OpenDesktopW(desktop, 0, False, 0x0040 | 0x0001)  # DESKTOP_ENUMERATE | READOBJECTS
        if desk:
            user32.EnumDesktopWindows(wintypes.HANDLE(desk), callback, 0)
            user32.CloseDesktop(wintypes.HANDLE(desk))
    return found[0] if found else None


US_LAYOUT = None


def post(hwnd, vk, down, alt):
    # Scan codes from the US layout: DOSBox maps physical keys, and the user's layout is German (Y/Z swapped).
    global US_LAYOUT
    if US_LAYOUT is None:
        user32.LoadKeyboardLayoutW.restype = wintypes.HANDLE
        US_LAYOUT = user32.LoadKeyboardLayoutW('00000409', 0)
    user32.MapVirtualKeyExW.argtypes = [wintypes.UINT, wintypes.UINT, wintypes.HANDLE]
    scan = user32.MapVirtualKeyExW(vk, 0, US_LAYOUT)
    lp = 1 | (scan << 16) | ((1 << 24) if vk in EXTENDED else 0)
    if alt:
        lp |= 1 << 29
    if not down:
        lp |= (1 << 30) | (1 << 31)
    msg = (WM_SYSKEYDOWN if down else WM_SYSKEYUP) if alt else (WM_KEYDOWN if down else WM_KEYUP)
    user32.PostMessageW(hwnd, msg, vk, lp)


def main():
    pid = int(sys.argv[1])
    hwnd = find_window(pid, os.environ.get('POSTKEYS_DESKTOP', 'waw-test'))
    if not hwnd:
        raise SystemExit(f'no window for PID {pid}')
    user32.PostMessageW(hwnd, 0x0006, 1, 0)  # WM_ACTIVATE: windows on a private desktop never get focus,
    user32.PostMessageW(hwnd, 0x0007, 0, 0)  # WM_SETFOCUS: and SDL drops keys without it
    time.sleep(0.1)
    for combo in sys.argv[2:]:
        parts = combo.lower().split('+')
        mods, key = [vk_of(p) for p in parts[:-1]], vk_of(parts[-1])
        alt = 0x12 in mods
        for m in mods:
            post(hwnd, m, True, alt)
            time.sleep(0.03)
        post(hwnd, key, True, alt)
        time.sleep(0.05)
        post(hwnd, key, False, alt)
        for m in reversed(mods):
            time.sleep(0.03)
            post(hwnd, m, False, alt)
        time.sleep(0.15)


if __name__ == '__main__':
    main()
