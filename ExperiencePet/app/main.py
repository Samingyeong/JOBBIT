"""Experience Pet: Windows roaming character + local-first Obsidian capture.

There is NO OpenAI API usage. ChatGPT desktop is a separate application:
we copy the interview prompt and open/focus it; the user pastes the final
answer back into a preview for a reviewed Obsidian save. No UI scraping.
"""
from __future__ import annotations
import os
from pathlib import Path
import queue
import sys
import time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from PIL import Image, ImageTk

from collections import deque
from titlebar import window_at_caption, rectangle, foreground_owner
from motion import PetMotion
from sprites import SpriteAtlas
from win_alpha import WinAlphaOverlay
from vault import VaultStore, load_settings, store_settings, make_gpt_prompt, APP_DATA
from mcp_bridge import check_connection
from chatgpt_desktop import open_interview
from winbridge import (foreground_rect,fullscreen_external,set_startup,
                       launch_chatgpt,GlobalHotkey)

HERE=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent))
CHROMA='#ff00ff'
BG='#fff9ee'
PANEL='#fff0d8'
TXT='#47342b'
MUTED='#856b5b'
ACCENT='#ff889c'


def label(parent,text,size=10,bold=False,color=TXT,**opts):
    return tk.Label(parent,text=text,bg=BG,fg=color,
        font=('Malgun Gothic',size,'bold' if bold else 'normal'),**opts)


def button(parent,text,fn,accent=False):
    return tk.Button(parent,text=text,command=fn,relief='flat',cursor='hand2',
        bg=ACCENT if accent else PANEL, fg='#41252d' if accent else TXT,
        activebackground='#ffb6c2' if accent else '#ffe5be',
        activeforeground='#41252d' if accent else TXT,
        font=('Malgun Gothic',10,'bold' if accent else 'normal'),padx=12,pady=10)


from memo_ui import CaptureWindow


class SettingsWindow:
    def __init__(self,app):
        self.app=app
        self.win=tk.Toplevel(app.root)
        self.win.title('Experience Pet 설정')
        self.win.geometry('570x520')
        self.win.configure(bg=BG)
        self.win.attributes('-topmost',True)
        root=tk.Frame(self.win,bg=BG,padx=22,pady=18)
        root.pack(fill='both',expand=True)
        label(root,'설정',17,True).pack(anchor='w')
        label(root,'Obsidian Vault 폴더를 연결하면 원본 메모가 자동으로 저장돼요.',9,color=MUTED).pack(anchor='w',pady=(5,15))
        self.path=tk.StringVar(value=app.config.get('vault_path',''))
        folder=tk.Frame(root,bg=BG)
        folder.pack(fill='x')
        tk.Entry(folder,textvariable=self.path,bg=PANEL,fg=TXT,insertbackground=TXT,relief='flat',
                 font=('Malgun Gothic',9)).pack(side='left',fill='x',expand=True,ipady=8)
        button(folder,'폴더 선택',self.browse).pack(side='left',padx=(9,0))
        self.roam=tk.BooleanVar(value=app.config['roam'])
        self.speech=tk.BooleanVar(value=app.config['speech'])
        self.fullscreen=tk.BooleanVar(value=app.config['hide_fullscreen'])
        self.startup=tk.BooleanVar(value=app.config['startup'])
        self.size=tk.IntVar(value=int(app.config['size']))
        for text,var in [('캐릭터가 자유롭게 돌아다니기',self.roam),
                         ('말풍선 사용',self.speech),
                         ('전체화면 앱에서는 캐릭터 숨기기',self.fullscreen),
                         ('Windows 시작 시 자동 실행',self.startup)]:
            tk.Checkbutton(root,text=text,variable=var,bg=BG,fg=TXT,
                activebackground=BG,activeforeground=TXT,selectcolor=PANEL,
                font=('Malgun Gothic',10)).pack(anchor='w',pady=3)
        label(root,'캐릭터 크기',9,color=MUTED).pack(anchor='w',pady=(9,0))
        tk.Scale(root,from_=100,to=220,orient='horizontal',resolution=10,variable=self.size,
            bg=BG,fg=TXT,highlightthickness=0,troughcolor=PANEL,activebackground=ACCENT).pack(fill='x')
        bar=tk.Frame(root,bg=BG)
        bar.pack(fill='x',pady=(13,0))
        button(bar,'ChatGPT 로그인/열기',self.open_chatgpt_login).pack(side='left')
        button(bar,'Obsidian MCP 진단',self.check_mcp).pack(side='left',padx=5)
        button(bar,'설정 저장',self.save,True).pack(side='right')

    def browse(self):
        p=filedialog.askdirectory(parent=self.win,title='Career Experience Vault 선택')
        if p:self.path.set(p)

    def open_chatgpt_login(self):
        kind=launch_chatgpt()
        messagebox.showinfo('ChatGPT 로그인', 'ChatGPT가 열렸어요. 공식 앱의 로그인 화면에서 직접 로그인해 주세요.\nExperience Pet은 비밀번호나 세션 정보를 받거나 저장하지 않습니다.',parent=self.win)

    def check_mcp(self):
        key=simpledialog.askstring('MCP 연결 진단','Obsidian Local REST API with MCP의 API 키를 입력하세요.\n이 키는 앱 설정에 저장하지 않습니다.',show='*',parent=self.win)
        if not key:return
        try:
            names=check_connection(self.app.config['mcp_url'],key)
        except Exception as exc:
            messagebox.showerror('MCP 연결 실패',str(exc),parent=self.win)
        else:
            messagebox.showinfo('MCP 연결 성공',f'로컬 MCP 서버 연결 확인! ({len(names)}개 도구)\nVault 쓰기는 별도 API 대신 앱이 직접 Vault 파일에 수행합니다.',parent=self.win)

    def save(self):
        v=self.path.get().strip()
        if v and not Path(v).is_dir():
            messagebox.showwarning('잘못된 경로','존재하는 Vault 폴더를 선택해 주세요.',parent=self.win)
            return
        config=self.app.config
        config.update({'vault_path':v,'roam':self.roam.get(),'speech':self.speech.get(),
                        'hide_fullscreen':self.fullscreen.get(),'startup':self.startup.get(),
                        'size':self.size.get()})
        try:
            if v:self.app.store=VaultStore(v)
            else:self.app.store=None
            store_settings(config)
            set_startup(self.startup.get())
        except Exception as exc:
            messagebox.showwarning('설정 저장 문제',str(exc),parent=self.win)
            return
        self.app.reload_sprite()
        self.app.motion.resize(int(config['size']))
        if self.app.note and self.app.note.session is None and self.app.store:
            self.app.note.session=self.app.store.new_session()
            self.app.note.flush()
        self.win.destroy()


class ExperiencePet:
    def __init__(self):
        self.config=load_settings()
        self.store=None
        try:
            if self.config['vault_path']:
                self.store=VaultStore(self.config['vault_path'])
        except ValueError:pass
        self.root=tk.Tk()
        self.root.title('ExperiencePet-overlay')
        self.root.overrideredirect(True)
        self.root.wm_attributes('-topmost',False)
        self.anchor = None
        self.work_rect = None
        self.overlay=None
        self.root.geometry('306x300+400+550')
        self.canvas=tk.Canvas(self.root,width=306,height=300,highlightthickness=0,
                         bd=0,bg=CHROMA,cursor='hand2')
        self.canvas.pack(fill='both',expand=True)
        if sys.platform=='win32':
            try:self.overlay=WinAlphaOverlay(self.root)
            except Exception:
                self.root.wm_attributes('-transparentcolor',CHROMA)
        self.w,self.h=self.root.winfo_screenwidth(),self.root.winfo_screenheight()
        self.motion=PetMotion(self.w,self.h,size=int(self.config['size']))
        self.atlas=SpriteAtlas(HERE/'assets/sprites')
        self.character=Image.open(HERE/'assets/shinchan_icon.png').convert('RGBA')
        try:self.root.iconbitmap(str(HERE/'assets/shinchan_icon.ico'))
        except (tk.TclError,OSError):pass
        self.photos=[]
        self.note=None
        self.context=tk.Menu(self.root,tearoff=0)
        self.context.add_command(label='📝 경험 기록',command=self.open_notes)
        self.context.add_command(label='⚙ 설정',command=self.open_settings)
        self.context.add_command(label='🐾 이동 멈추기/재개',command=self.toggle_pause)
        self.context.add_command(label='💤 잠깐 숨기기 (트레이)',command=self.hide)
        self.context.add_separator()
        self.context.add_command(label='종료',command=self.quit)
        self.canvas.bind('<ButtonPress-1>',self.pointer_down)
        self.canvas.bind('<B1-Motion>',self.pointer_drag)
        self.canvas.bind('<ButtonRelease-1>',self.pointer_up)
        self.canvas.bind('<Button-3>',self.popup)
        self.drag_start=None
        self.is_drag=False
        self.last_fullscreen=False
        self.displayed=True
        self.hidden=False
        self.events=queue.Queue()
        self.hotkey=GlobalHotkey(self.events)
        self.hotkey.start()
        self.tray=None
        self.setup_tray()
        self.reload_sprite()
        self.last_tick=time.monotonic()
        self.root.after(50,self.tick)
        self.root.after(300,self.poll_events)
        if self.config['startup']:
            try:set_startup(True)
            except Exception:pass
        if not self.store:self.root.after(550,self.open_settings)

    def setup_tray(self):
        try:
            import pystray
            image=self.character.resize((64,64))
            items=pystray.Menu(
                pystray.MenuItem('경험 기록',lambda icon,item:self.events.put('open')),
                pystray.MenuItem('캐릭터 표시',lambda icon,item:self.events.put('show')),
                pystray.MenuItem('잠시 숨기기',lambda icon,item:self.events.put('hide')),
                pystray.MenuItem('종료',lambda icon,item:self.events.put('quit')))
            self.tray=pystray.Icon('ExperiencePet',image,'경험 기록 짱구',items)
            self.tray.run_detached()
        except Exception:
            self.tray=None

    def reload_sprite(self):
        self.size=int(self.config.get('size',156))
        self.base=self.character.resize((self.size,self.size),Image.Resampling.LANCZOS)
        self.atlas.clear_cache()
        self.canvas.configure(width=306,height=300)

    def render(self,m):
        from PIL import ImageDraw, ImageFont
        canvas=Image.new('RGBA',(306,300),(0,0,0,0))
        name=m.get('frame','idle')
        art=self.atlas.get(name,self.size,m['face'])
        # Each 320px frame is kept proportional to avoid a visible green keyline.
        canvas.alpha_composite(art,(int((306-self.size)/2),57))
        if self.config['speech'] and m['speech']:
            draw=ImageDraw.Draw(canvas)
            draw.rounded_rectangle((10,7,295,49),radius=16,fill='#fffdf4',outline='#382922',width=3)
            draw.polygon([(143,47),(153,59),(162,47)],fill='#fffdf4')
            try:
                font_path=Path(os.environ.get('WINDIR',r'C:\Windows'))/'Fonts'/'malgunbd.ttf'
                font=ImageFont.truetype(str(font_path),16) if font_path.exists() else ImageFont.load_default()
            except OSError:font=ImageFont.load_default()
            draw.text((153,26),m['speech'][:18],font=font,fill='#3f2f28',anchor='mm')
        x=int(m['x']);y=int(m['y'])
        if self.work_rect:
            l,t,r,b = self.work_rect
            box = (max(0,l-x), max(0,t-y), min(canvas.width,r-x), min(canvas.height,b-y))
            if box[2] > box[0] and box[3] > box[1]:
                canvas.paste((0,0,0,0),box)
        if self.overlay is not None:
            try:
                self.overlay.display(canvas,x,y)
                return
            except (OSError,ValueError) as exc:
                self.overlay=None
                try:self.root.wm_attributes('-transparentcolor',CHROMA)
                except tk.TclError:pass
                print('Windows alpha renderer unavailable, using fallback:',exc)
        self.canvas.delete('all')
        self.photos=[ImageTk.PhotoImage(canvas)]
        self.canvas.create_image(0,0,anchor='nw',image=self.photos[0])
        self.root.geometry(f'+{x}+{y}')

    def detach(self,now):
        self.anchor=None
        self.root.wm_attributes('-topmost',False)
        self.motion.release(now,0,0)

    def follow_caption(self,now):
        hwnd,dx,dy=self.anchor
        rect=rectangle(hwnd)
        if not rect or now>=self.motion.end or not foreground_owner(hwnd):
            self.detach(now)
            return False
        left,top,right,bottom=rect
        self.motion.x=left+min(dx,max(0,right-left-1))-153
        self.motion.y=top+dy-57-int(self.size*.09)
        return True

    def tick(self):
        now=time.monotonic()
        self.work_rect=foreground_rect(self.w,self.h)
        full=fullscreen_external(self.w,self.h) if self.config['hide_fullscreen'] else False
        hanging=bool(self.anchor and self.follow_caption(now))
        should_show=((hanging or not full) and not self.hidden)
        if hanging:
            self.work_rect=None
        if should_show != self.displayed:
            if should_show:self.root.deiconify()
            else:self.root.withdraw()
            self.displayed=should_show
        if hanging:
            m=self.motion.visual(now)
        elif (self.config['roam'] and not self.motion.paused) or self.motion.state in ('flight','fallen','cry'):
            m=self.motion.tick(now)
        else:
            self.motion.paused=True
            m=self.motion.visual(now)
        self.render(m)
        self.root.after(55,self.tick)

    def pointer_down(self,e):
        if self.anchor:
            self.detach(time.monotonic())
        self.drag_start=(e.x_root,e.y_root,self.motion.x,self.motion.y)
        self.is_drag=False
        self.samples=deque([(time.monotonic(),e.x_root,e.y_root)],maxlen=100)
        self.turns=deque(maxlen=4)
        self.direction=(0,0)
        self.pivot=(e.x_root,e.y_root)
        self.motion.paused=True
        self.motion.state='held'
        self.motion.bubble=''

    def pointer_drag(self,e):
        if not self.drag_start:
            return
        mx,my,x,y=self.drag_start
        dx,dy=e.x_root-mx,e.y_root-my
        if not self.is_drag and abs(dx)+abs(dy)<=9:
            return
        self.is_drag=True
        now=time.monotonic()
        self.samples.append((now,e.x_root,e.y_root))
        sx,sy=e.x_root-self.pivot[0],e.y_root-self.pivot[1]
        if max(abs(sx),abs(sy))>=12:
            axis=(1 if sx>0 else -1,0) if abs(sx)>=abs(sy) else (0,1 if sy>0 else -1)
            if sum(a*b for a,b in zip(axis,self.direction))<0:
                self.turns.append(now)
            self.pivot=(e.x_root,e.y_root)
            self.direction=axis
            if len(self.turns)>=3 and now-self.turns[-3]<.85:
                self.motion.state='dizzy'
        inset=(306-self.size)/2
        self.motion.x=max(-inset,min(self.w-self.size-inset,x+dx))
        self.motion.y=max(-57,min(self.motion.ground_y,y+dy))

    def pointer_up(self,e):
        if not self.drag_start:
            return
        self.drag_start=None
        now=time.monotonic()
        self.motion.paused=not self.config['roam']
        if not self.is_drag:
            self.motion._set('idle',now,2)
            self.open_notes()
            return
        anchor=window_at_caption(e.x_root,e.y_root)
        if anchor:
            self.anchor=anchor
            self.motion._set('cling',now,4.2)
            self.motion.bubble=''
            self.motion.face=1
            self.root.wm_attributes('-topmost',True)
            return
        recent=[p for p in self.samples if now-p[0]<=.12]
        vx=vy=0
        if recent:
            t,x,y=recent[0]
            dt=max(.016,now-t)
            vx,vy=(e.x_root-x)/dt,(e.y_root-y)/dt
        self.motion.release(now,vx,vy)

    def popup(self,e):
        self.context.tk_popup(e.x_root,e.y_root)

    def open_notes(self):
        if self.note and self.note.win.winfo_exists():
            self.note.show()
        else:
            self.note=CaptureWindow(self)
    def open_settings(self):SettingsWindow(self)
    def toggle_pause(self):
        paused=not self.motion.paused
        self.motion.paused=paused
        self.config['roam']=not paused
        store_settings(self.config)
    def hide(self):
        if not self.tray:
            messagebox.showinfo('트레이 미사용','pystray가 설치되지 않아 트레이로 숨길 수 없습니다.')
            return
        self.hidden=True
        self.displayed=False
        self.root.withdraw()
    def show(self):
        self.hidden=False
        self.displayed=True
        self.root.deiconify()
        self.root.lift()
    def poll_events(self):
        try:
            while True:
                event=self.events.get_nowait()
                if event=='open':self.show();self.open_notes()
                elif event=='show':self.show()
                elif event=='hide':self.hide()
                elif event=='quit':self.quit();return
        except queue.Empty:pass
        self.root.after(250,self.poll_events)
    def quit(self):
        if self.note:
            try:self.note.flush()
            except Exception:pass
        self.hotkey.stop()
        if self.tray:
            try:self.tray.stop()
            except Exception:pass
        self.root.destroy()
    def run(self):self.root.mainloop()

if __name__=='__main__':
    ExperiencePet().run()
