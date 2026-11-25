"""Optional Win32 functionality. Imports and dry-runs on Linux for tests."""
from __future__ import annotations
import ctypes
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
import webbrowser

IS_WINDOWS = sys.platform == 'win32'
APP_ID = 'JOBBIT.ExperiencePet'


def identify_app():
    if IS_WINDOWS:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)


def notebook_caption(window):
    if not IS_WINDOWS:
        return
    from ctypes import wintypes
    user32=ctypes.windll.user32
    get_ancestor=user32.GetAncestor
    get_ancestor.argtypes=(wintypes.HWND,wintypes.UINT)
    get_ancestor.restype=wintypes.HWND
    hwnd=get_ancestor(window.winfo_id(),2)
    if hwnd:
        set_attribute=ctypes.windll.dwmapi.DwmSetWindowAttribute
        set_attribute.argtypes=(wintypes.HWND,wintypes.DWORD,ctypes.c_void_p,wintypes.DWORD)
        for attribute,color in ((34,0xB0A876),(35,0xD2F5FB),(36,0x242424)):
            value=wintypes.DWORD(color)
            set_attribute(hwnd,attribute,ctypes.byref(value),ctypes.sizeof(value))


class NotebookInstance:
    """Route a repeated launch to the running pet in the same Windows session."""
    def __init__(self):
        self.handle=None
        self.duplicate=False
        if IS_WINDOWS:
            from ctypes import wintypes
            self.kernel=ctypes.WinDLL('kernel32',use_last_error=True)
            self.kernel.CreateEventW.argtypes=(ctypes.c_void_p,wintypes.BOOL,wintypes.BOOL,wintypes.LPCWSTR)
            self.kernel.CreateEventW.restype=wintypes.HANDLE
            self.kernel.SetEvent.argtypes=(wintypes.HANDLE,)
            self.kernel.WaitForSingleObject.argtypes=(wintypes.HANDLE,wintypes.DWORD)
            self.kernel.CloseHandle.argtypes=(wintypes.HANDLE,)
            self.handle=self.kernel.CreateEventW(None,False,False,APP_ID+'.OpenNotebook')
            self.duplicate=bool(self.handle and ctypes.get_last_error()==183)
            if self.duplicate:
                self.kernel.SetEvent(self.handle)

    def requested(self):
        return bool(self.handle and self.kernel.WaitForSingleObject(self.handle,0)==0)

    def close(self):
        if self.handle:
            self.kernel.CloseHandle(self.handle)
            self.handle=None


def foreground_rect(screen_w:int, screen_h:int):
    """Return active external window (left, top, right, bottom), or None."""
    if not IS_WINDOWS:
        return None
    try:
        from ctypes import wintypes
        u = ctypes.windll.user32
        u.GetForegroundWindow.restype = wintypes.HWND
        hwnd = u.GetForegroundWindow()
        if not hwnd or not u.IsWindowVisible(hwnd):
            return None
        cls = ctypes.create_unicode_buffer(128)
        u.GetClassNameW(wintypes.HWND(hwnd), cls, len(cls))
        if cls.value in ('Progman', 'WorkerW', 'Shell_TrayWnd', 'Shell_SecondaryTrayWnd'):
            return None
        pid = ctypes.c_ulong()
        u.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value == os.getpid():
            return None
        class RECT(ctypes.Structure):
            _fields_ = [('left',ctypes.c_long),('top',ctypes.c_long),('right',ctypes.c_long),('bottom',ctypes.c_long)]
        r=RECT()
        if not u.GetWindowRect(hwnd,ctypes.byref(r)):
            return None
        if r.right-r.left < 350 or r.bottom-r.top < 180:
            return None
        return (r.left, r.top, r.right, r.bottom)
    except Exception:
        return None


def fullscreen_external(screen_w:int, screen_h:int):
    if not IS_WINDOWS:
        return False
    try:
        from ctypes import wintypes
        u = ctypes.windll.user32
        u.GetForegroundWindow.restype = wintypes.HWND
        hwnd = u.GetForegroundWindow()
        if not hwnd:
            return False
        cls = ctypes.create_unicode_buffer(128)
        u.GetClassNameW(wintypes.HWND(hwnd), cls, len(cls))
        if cls.value in ('Progman', 'WorkerW', 'Shell_TrayWnd', 'Shell_SecondaryTrayWnd'):
            return None
        pid=ctypes.c_ulong()
        u.GetWindowThreadProcessId(hwnd,ctypes.byref(pid))
        if pid.value == os.getpid():
            return False
        class RECT(ctypes.Structure):
            _fields_=[('left',ctypes.c_long),('top',ctypes.c_long),('right',ctypes.c_long),('bottom',ctypes.c_long)]
        r=RECT()
        if not u.GetWindowRect(hwnd,ctypes.byref(r)):
            return False
        same_size = (r.left <= 2 and r.top <= 2 and r.right >= screen_w-2 and r.bottom >= screen_h-2)
        GWL_STYLE=-16
        WS_CAPTION=0x00C00000
        style=u.GetWindowLongW(hwnd,GWL_STYLE)
        is_maximized=bool(u.IsZoomed(hwnd))
        return bool(same_size and not (style & WS_CAPTION) and not is_maximized)
    except Exception:
        return False


def set_startup(enabled: bool):
    """HKCU Run entry, never admin rights. Caller controls explicit toggle."""
    if not IS_WINDOWS:
        return False
    import winreg
    if getattr(sys,'frozen',False):
        command=f'"{sys.executable}"'
    else:
        exe=Path(sys.executable)
        pythonw=exe.with_name('pythonw.exe')
        command=f'"{pythonw if pythonw.exists() else exe}" "{Path(__file__).with_name("main.py")}"'
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Run', 0, winreg.KEY_SET_VALUE) as key:
        if enabled:
            winreg.SetValueEx(key,'ExperiencePet',0,winreg.REG_SZ,command)
        else:
            try:winreg.DeleteValue(key,'ExperiencePet')
            except FileNotFoundError:pass
    return True


def focus_chatgpt_app():
    """Bring up an already open ChatGPT window when possible; no automation of its contents."""
    if not IS_WINDOWS:
        return False
    from ctypes import wintypes
    u=ctypes.windll.user32
    u.GetForegroundWindow.restype=wintypes.HWND
    found=[]
    WNDENUMPROC=ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def inspect(hwnd,param):
        if not u.IsWindowVisible(hwnd): return True
        length=u.GetWindowTextLengthW(hwnd)
        if length < 1: return True
        buffer=ctypes.create_unicode_buffer(length+1)
        u.GetWindowTextW(hwnd,buffer,length+1)
        title=buffer.value.lower()
        if title.startswith('chatgpt') or title.endswith('- chatgpt'):
            found.append(hwnd)
        return True
    callback=WNDENUMPROC(inspect)
    u.EnumWindows(callback,0)
    if found:
        u.ShowWindow(found[0],9)
        u.SetForegroundWindow(found[0])
        return True
    return False


def launch_chatgpt():
    """Return app if existing desktop app was focused, otherwise browser fallback."""
    if focus_chatgpt_app():
        return 'app'
    if IS_WINDOWS:
        # Find a ChatGPT Start-menu app id without guessing a private URL scheme.
        try:
            script = "Get-StartApps | Where-Object { $_.Name -eq 'ChatGPT' } | Select-Object -First 1 -ExpandProperty AppID"
            p=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',script],
                capture_output=True,text=True,timeout=5,creationflags=0x08000000)
            appid=p.stdout.strip().splitlines()
            if appid:
                subprocess.Popen(['explorer.exe','shell:AppsFolder\\'+appid[0]])
                return 'app'
        except Exception:
            pass
    webbrowser.open('https://chatgpt.com/')
    return 'browser'


class GlobalHotkey:
    """Ctrl+Alt+E, Win32 RegisterHotKey; queue notification, no Tk from worker thread."""
    def __init__(self, event_queue):
        self.events=event_queue
        self.worker=None
        self.thread_id=None
    def start(self):
        if not IS_WINDOWS:return
        def work():
            from ctypes import wintypes
            user=ctypes.windll.user32
            kernel=ctypes.windll.kernel32
            self.thread_id=kernel.GetCurrentThreadId()
            hotkey_id=0xE11
            if not user.RegisterHotKey(None,hotkey_id,0x0001|0x0002,ord('E')):
                return
            class MSG(ctypes.Structure):
                _fields_=[('hwnd',wintypes.HWND),('message',wintypes.UINT),('wParam',wintypes.WPARAM),('lParam',wintypes.LPARAM),('time',wintypes.DWORD),('pt',wintypes.POINT)]
            msg=MSG()
            while user.GetMessageW(ctypes.byref(msg),None,0,0)>0:
                if msg.message == 0x0312 and msg.wParam == hotkey_id:
                    self.events.put('open')
            user.UnregisterHotKey(None,hotkey_id)
        self.worker=threading.Thread(target=work,daemon=True)
        self.worker.start()
    def stop(self):
        if IS_WINDOWS and self.thread_id:
            ctypes.windll.user32.PostThreadMessageW(self.thread_id,0x0012,0,0)
