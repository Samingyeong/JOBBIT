"""Find an exposed, draggable Win32 caption below a released desktop pet."""
import ctypes
from ctypes import wintypes as W
import os

def rectangle(hwnd):
    if not hwnd:
        return None
    u=ctypes.windll.user32
    r=W.RECT()
    handle=W.HWND(hwnd)
    if u.IsWindowVisible(handle) and not u.IsIconic(handle) and u.GetWindowRect(handle,ctypes.byref(r)):
        return r.left,r.top,r.right,r.bottom

def window_at_caption(x,y):
    if os.name!='nt':
        return None
    u=ctypes.windll.user32
    found=[]
    callback=ctypes.WINFUNCTYPE(W.BOOL,W.HWND,W.LPARAM)
    @callback
    def visit(hwnd,_):
        pid=W.DWORD()
        u.GetWindowThreadProcessId(W.HWND(hwnd),ctypes.byref(pid))
        if pid.value==os.getpid():
            return True
        rect=rectangle(hwnd)
        if not rect:
            return True
        l,t,r,b=rect
        if not (l<=x<r and t<=y<b):
            return True
        cls=ctypes.create_unicode_buffer(128)
        u.GetClassNameW(W.HWND(hwnd),cls,128)
        if cls.value in ('Progman','WorkerW','Shell_TrayWnd','Shell_SecondaryTrayWnd'):
            return False
        result=ctypes.c_size_t()
        ok=u.SendMessageTimeoutW(W.HWND(hwnd),0x84,0,W.LPARAM((x&65535)|((y&65535)<<16)),
                                 2,60,ctypes.byref(result))
        if ok and result.value==2:  # HTCAPTION; excludes close, resize and tab buttons.
            found.append((hwnd,x-l,y-t))
        return False
    u.EnumWindows(visit,0)
    return found[0] if found else None

def foreground_owner(hwnd):
    u=ctypes.windll.user32
    u.GetForegroundWindow.restype=W.HWND
    active=u.GetForegroundWindow()
    pid=W.DWORD()
    u.GetWindowThreadProcessId(W.HWND(active),ctypes.byref(pid))
    return active==hwnd or pid.value==os.getpid()
