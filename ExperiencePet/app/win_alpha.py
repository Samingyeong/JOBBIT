"""True per-pixel-alpha Win32 overlay (avoids chroma-key green fringes).

On Windows, UpdateLayeredWindow draws premultiplied BGRA straight to a layered
Tk top-level. Transparent pixels remain click-through, with no green colorkey.
Non-Windows platforms use the Canvas fallback in main.py.
"""
from __future__ import annotations
import ctypes
import sys
from PIL import Image

IS_WINDOWS = sys.platform == 'win32'

if IS_WINDOWS:
    from ctypes import wintypes
    class POINT(ctypes.Structure):
        _fields_=[('x',wintypes.LONG),('y',wintypes.LONG)]
    class SIZE(ctypes.Structure):
        _fields_=[('cx',wintypes.LONG),('cy',wintypes.LONG)]
    class BLENDFUNCTION(ctypes.Structure):
        _fields_=[('BlendOp',ctypes.c_ubyte),('BlendFlags',ctypes.c_ubyte),
                  ('SourceConstantAlpha',ctypes.c_ubyte),('AlphaFormat',ctypes.c_ubyte)]
    class BITMAPINFOHEADER(ctypes.Structure):
        _fields_=[('biSize',wintypes.DWORD),('biWidth',wintypes.LONG),
                  ('biHeight',wintypes.LONG),('biPlanes',wintypes.WORD),
                  ('biBitCount',wintypes.WORD),('biCompression',wintypes.DWORD),
                  ('biSizeImage',wintypes.DWORD),('biXPelsPerMeter',wintypes.LONG),
                  ('biYPelsPerMeter',wintypes.LONG),('biClrUsed',wintypes.DWORD),
                  ('biClrImportant',wintypes.DWORD)]
    class BITMAPINFO(ctypes.Structure):
        _fields_=[('bmiHeader',BITMAPINFOHEADER),('bmiColors',wintypes.DWORD*1)]


def rgba_to_premultiplied_bgra(im:Image.Image)->bytes:
    """Pure Python byte conversion for alpha correctness and headless tests."""
    b=bytearray(im.convert('RGBA').tobytes())
    for j in range(0,len(b),4):
        a=b[j+3]
        r,g,bl=b[j],b[j+1],b[j+2]
        b[j]=(bl*a+127)//255
        b[j+1]=(g*a+127)//255
        b[j+2]=(r*a+127)//255
    return bytes(b)


class WinAlphaOverlay:
    def __init__(self,tk_root):
        if not IS_WINDOWS:raise RuntimeError('Windows only')
        self.user=ctypes.windll.user32
        self.gdi=ctypes.windll.gdi32
        self.user.GetParent.argtypes=[wintypes.HWND]
        self.user.GetParent.restype=wintypes.HWND
        self.user.GetWindowLongW.argtypes=[wintypes.HWND,ctypes.c_int]
        self.user.GetWindowLongW.restype=ctypes.c_long
        self.user.SetWindowLongW.argtypes=[wintypes.HWND,ctypes.c_int,ctypes.c_long]
        self.user.SetWindowLongW.restype=ctypes.c_long
        self.user.GetDC.argtypes=[wintypes.HWND]
        self.user.GetDC.restype=wintypes.HDC
        self.user.ReleaseDC.argtypes=[wintypes.HWND,wintypes.HDC]
        self.gdi.CreateCompatibleDC.argtypes=[wintypes.HDC]
        self.gdi.CreateCompatibleDC.restype=wintypes.HDC
        self.gdi.DeleteDC.argtypes=[wintypes.HDC]
        self.gdi.CreateDIBSection.argtypes=[wintypes.HDC,ctypes.POINTER(BITMAPINFO),wintypes.UINT,
                                             ctypes.POINTER(ctypes.c_void_p),wintypes.HANDLE,wintypes.DWORD]
        self.gdi.CreateDIBSection.restype=wintypes.HBITMAP
        self.gdi.SelectObject.argtypes=[wintypes.HDC,wintypes.HGDIOBJ]
        self.gdi.SelectObject.restype=wintypes.HGDIOBJ
        self.gdi.DeleteObject.argtypes=[wintypes.HGDIOBJ]
        self.gdi.DeleteObject.restype=wintypes.BOOL
        self.user.UpdateLayeredWindow.argtypes=[wintypes.HWND,wintypes.HDC,ctypes.POINTER(POINT),
             ctypes.POINTER(SIZE),wintypes.HDC,ctypes.POINTER(POINT),wintypes.COLORREF,
             ctypes.POINTER(BLENDFUNCTION),wintypes.DWORD]
        self.user.UpdateLayeredWindow.restype=wintypes.BOOL
        tk_root.update_idletasks()
        child=tk_root.winfo_id()
        self.hwnd=self.user.GetParent(child) or child
        GWL_EXSTYLE=-20
        WS_EX_LAYERED=0x00080000
        WS_EX_TOOLWINDOW=0x00000080
        ex=self.user.GetWindowLongW(self.hwnd,GWL_EXSTYLE)
        self.user.SetWindowLongW(self.hwnd,GWL_EXSTYLE,ex|WS_EX_LAYERED|WS_EX_TOOLWINDOW)
        self.user.ShowWindow(self.hwnd,5)

    def display(self,im,x:int,y:int):
        if not IS_WINDOWS:return
        im=im.convert('RGBA')
        width,height=im.size
        screen=self.user.GetDC(None)
        memdc=self.gdi.CreateCompatibleDC(screen)
        dib=None;old=None
        try:
            info=BITMAPINFO()
            info.bmiHeader.biSize=ctypes.sizeof(BITMAPINFOHEADER)
            info.bmiHeader.biWidth=width
            info.bmiHeader.biHeight=-height # top-down DIB
            info.bmiHeader.biPlanes=1
            info.bmiHeader.biBitCount=32
            info.bmiHeader.biCompression=0  # BI_RGB
            pixels=ctypes.c_void_p()
            dib=self.gdi.CreateDIBSection(memdc,ctypes.byref(info),0,ctypes.byref(pixels),None,0)
            if not dib or not pixels.value:
                raise OSError('CreateDIBSection 실패')
            old=self.gdi.SelectObject(memdc,dib)
            bgra=rgba_to_premultiplied_bgra(im)
            ctypes.memmove(pixels,bgra,len(bgra))
            pt=POINT(int(x),int(y)); size=SIZE(width,height); source=POINT(0,0)
            blend=BLENDFUNCTION(0,0,255,1) # AC_SRC_OVER, AC_SRC_ALPHA
            if not self.user.UpdateLayeredWindow(self.hwnd,screen,ctypes.byref(pt),
                ctypes.byref(size),memdc,ctypes.byref(source),0,ctypes.byref(blend),2):
                raise ctypes.WinError()
        finally:
            if old:self.gdi.SelectObject(memdc,old)
            if dib:self.gdi.DeleteObject(dib)
            if memdc:self.gdi.DeleteDC(memdc)
            if screen:self.user.ReleaseDC(None,screen)
