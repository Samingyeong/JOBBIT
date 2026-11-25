"""Cute memo-paper capture UI for Experience Pet.

ChatGPT remains a separate official desktop chat.  This module never
claims to receive its messages automatically without an API integration.
"""
from __future__ import annotations

import os
from pathlib import Path
import sys
import uuid
import tkinter as tk
from tkinter import messagebox, simpledialog
from PIL import Image, ImageTk

from diary_board import DiaryBoard
from experience_format import normalize, history, obsidian_uri
from vault import APP_DATA, make_gpt_prompt
from chatgpt_desktop import open_interview
from winbridge import launch_chatgpt

ASSETS = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent)) / 'assets'
BROWN = '#20201e'
LEMON = '#f6f3b0'
PAPER = '#fffdf9'
CREAM = '#fdf5e4'
EDGE = '#856341'
PINK = '#ff8298'
PALE = '#fffaf1'
MUTED = '#806d62'
OUTLINE = '#dbbcac'


def cute_font(win, size=11, bold=False):
    """Use an installed rounded Korean font when available; ship no fonts."""
    import tkinter.font as tkfont
    if not hasattr(cute_font, '_family'):
        names = set(tkfont.families(root=win))
        cute_font._family = next((name for name in (
            '배달의민족 주아', 'BM JUA', 'Jua', '여기어때 잘난체 2', '여기어때 잘난체 2 TTF', 'Cafe24 Ssurround',
            'BM JUA', '여기어때 잘난체', '나눔스퀘어라운드',
            'NanumSquareRound', '맑은 고딕', 'Malgun Gothic'
        ) if name in names), 'Malgun Gothic')
    return (cute_font._family, size, 'bold' if bold else 'normal')


def roundrect(canvas, x1,y1,x2,y2,r, **kw):
    r = max(0, min(r, (x2-x1)/2, (y2-y1)/2))
    return canvas.create_polygon([
        x1+r,y1,x2-r,y1,x2,y1,x2,y1+r,x2,y2-r,x2,y2,
        x2-r,y2,x1+r,y2,x1,y2,x1,y2-r,x1,y1+r,x1,y1
    ], smooth=True, splinesteps=12, **kw)


class CaptureWindow:
    WIDTH, HEIGHT=628, 792

    def __init__(self, app):
        self.app=app
        self.win=tk.Toplevel(app.root)
        self.win.title('경험펫 · 오늘의 경험 기록')
        self.win.geometry(f'{self.WIDTH}x{self.HEIGHT}')
        self.win.minsize(self.WIDTH,self.HEIGHT)
        self.win.maxsize(self.WIDTH,self.HEIGHT)
        self.win.configure(bg=PALE)
        self.win.protocol('WM_DELETE_WINDOW',self.hide)
        try:self.win.iconbitmap(str(ASSETS/'shinchan_icon.ico'))
        except (OSError,tk.TclError):pass
        self.session=app.store.new_session() if app.store else None
        self.backup_id=uuid.uuid4().hex[:12]
        self.source_path=None
        self.dirty_after=None
        self.title_var=tk.StringVar(value='오늘의 경험')
        self.project_var=tk.StringVar()
        self.status=tk.StringVar(value='메모는 입력 후 1초면 Obsidian에 원본으로 저장돼요.')
        self.view='memo'
        self._build()
        self.win.bind('<Control-Return>', lambda e:self.send_to_chatgpt())
        self.win.bind('<Control-s>', lambda e:self.flush())
        self.win.bind('<Control-Shift-S>', lambda e:self.save_experience())
        self.raw.focus_set()

    def button(self,parent,label,action,color='#ffdd85'):
        return tk.Button(parent,text=label,command=action,relief='flat',bd=0,bg=color,
                         fg=BROWN,activebackground='#ffd4bc',activeforeground=BROWN,
                         padx=13,pady=6,cursor='hand2',font=cute_font(self.win,10,True))

    def _build(self):
        self.win.geometry('760x740')
        self.win.minsize(540,490)
        self.win.maxsize(self.win.winfo_screenwidth(),self.win.winfo_screenheight())
        self.win.configure(bg=LEMON)
        cover=tk.Frame(self.win,bg=LEMON,padx=19,pady=5)
        cover.pack(fill='both',expand=True)
        banner=tk.Canvas(cover,height=100,bg=LEMON,highlightthickness=0)
        banner.pack(fill='x')
        self.cover_face=self.design_image('914', (125, 109), (1.2855, 1.0817, -.1128, 0))
        self.cover_friend=self.design_image('919', (77, 77), (1, 1.9442, 0, -.4725))
        self.cover_pattern=self.design_image('911', (528, 232), (1.5205, 1.1888, -.4932, -.0863))

        def draw_banner(event):
            center=event.width/2
            banner.delete('all')
            banner.create_image(-230,-41,image=self.cover_pattern,anchor='nw')
            banner.create_image(event.width-260,-41,image=self.cover_pattern,anchor='nw')
            banner.create_image(center-216,-6,image=self.cover_face,anchor='nw')
            banner.create_image(center+154,31,image=self.cover_friend,anchor='nw')
            banner.create_text(center,56,text='짱구의 경험 기록장',font=cute_font(self.win,26,True),fill=BROWN)

        banner.bind('<Configure>',draw_banner)
        rail=tk.Frame(cover,bg=LEMON,height=42)
        rail.pack(fill='x',padx=(47,0))
        rail.pack_propagate(False)
        self.tabs={}
        for key,label,color in [('memo','오늘 이야기','#fa5b60'),('final','완성노트','#ffd567'),('archive','경험모음','#84e36e'),('calendar','일기달력','#6875f5')]:
            btn=self.button(rail,label,lambda k=key:self.select_view(k),color)
            btn.configure(activebackground=color)
            btn.place(x=109*len(self.tabs),y=12,width=100,height=42)
            self.tabs[key]=btn
        paper=tk.Frame(cover,bg=PAPER,highlightbackground=EDGE,highlightthickness=2)
        paper.pack(fill='both',expand=True)
        backing=tk.Canvas(paper,bg=PAPER,highlightthickness=0)
        backing.place(x=0,y=0,relwidth=1,relheight=1)
        backing.lower('all')
        self.memo_badges=(
            self.design_image('901', (66, 66)),
            self.design_image('904', (81, 77), (2.2009, 2.4154, -.5633, -.6824)),
        )

        def paint_paper(event=None):
            width,height=backing.winfo_width(),backing.winfo_height()
            if min(width,height)<=1:
                return
            backing.delete('all')
            self.paper_pattern=self.design_image('906', (width,height), (1,1.4811,0,-.4811))
            backing.create_image(0,0,image=self.paper_pattern,anchor='nw')
            if self.view=='memo':
                backing.create_image(-12,height,image=self.memo_badges[0],anchor='sw')
                backing.create_image(width+8,height,image=self.memo_badges[1],anchor='se')

        self.paint_paper=paint_paper
        backing.bind('<Configure>',paint_paper)
        self.page=tk.Frame(paper,bg=PAPER)
        self.page.pack(fill='both',expand=True,padx=39,pady=(26,10))
        self.memo_page=tk.Frame(self.page,bg='#fffdf5')
        self.final_page=tk.Frame(self.page,bg='#fffdf5')
        self.archive_page=tk.Frame(self.page,bg='#fffdf5')
        self._build_memo()
        self._build_final()
        self._build_archive()
        self.calendar=DiaryBoard(self.page,lambda:self.app.store,lambda size:cute_font(self.win,size),ASSETS,self.open_obsidian)
        self.action_row=tk.Frame(paper,bg=PAPER,pady=6)
        self.action_row.pack(fill='x',padx=40)
        self.action=self.button(self.action_row,'ChatGPT에서 대화하기',self.send_to_chatgpt,'#ffd567')
        self.action.pack(side='right')
        tk.Label(self.action_row,textvariable=self.status,bg=PAPER,fg=BROWN,
                 wraplength=310,justify='left',font=cute_font(self.win,9)).pack(side='left')
        self.project_var.trace_add('write',lambda *_:self.schedule_save())
        self.select_view('memo')

    def design_image(self, asset, size, crop=(1, 1, 0, 0)):
        width,height=size
        scale_x,scale_y,offset_x,offset_y=crop
        with Image.open(ASSETS/f'figma_{asset}.png') as source:
            scaled=source.convert('RGBA').resize(
                (round(width*scale_x),round(height*scale_y)),Image.Resampling.LANCZOS)
        result=Image.new('RGBA',size)
        result.paste(scaled,(round(width*offset_x),round(height*offset_y)))
        return ImageTk.PhotoImage(result,master=self.win)

    def _build_archive(self):
        self.library_project=tk.StringVar(value='전체 프로젝트')
        self.filter_button=tk.Menubutton(self.archive_page,textvariable=self.library_project,
                              bg='#c5e6d1',fg=BROWN,relief='flat',padx=12,pady=6,cursor='hand2')
        self.filter_button.pack(anchor='w')
        self.filters=tk.Menu(self.filter_button,tearoff=False)
        self.filter_button.configure(menu=self.filters)
        self.records=tk.Listbox(self.archive_page,height=5,exportselection=False,
                        bg='#fff5d9',fg=BROWN,bd=0,highlightthickness=0,
                        selectbackground='#f8cc78',selectforeground=BROWN,font=cute_font(self.win,11))
        self.records.pack(fill='x',pady=8)
        self.records.bind('<<ListboxSelect>>',lambda e:self.read_record())
        self.reader=tk.Text(self.archive_page,wrap='word',bg='#fffdf5',fg=BROWN,
                        bd=0,highlightthickness=0,padx=8,pady=4,font=cute_font(self.win,11))
        self.reader.tag_configure('heading',font=cute_font(self.win,13,True),foreground='#994e44',spacing1=10)
        self.reader.pack(fill='both',expand=True)
        self.reader.configure(state='disabled')

    def refresh_archive(self,selection=None):
        if selection is not None:
            self.library_project.set(selection)
        rows=list(history(self.app.store.root)) if self.app.store else []
        names=set(self.app.store.project_names()) if self.app.store else set()
        names.update(p for p,*_ in rows if p)
        self.filters.delete(0,'end')
        for p in ['전체 프로젝트',*sorted(names),'프로젝트 미지정']:
            self.filters.add_command(label=p,command=lambda n=p:self.refresh_archive(n))
        choice=self.library_project.get()
        self.rows=[r for r in rows if choice=='전체 프로젝트' or (r[0] or '프로젝트 미지정')==choice]
        self.records.delete(0,'end')
        for project,title,*_ in self.rows:
            self.records.insert('end','  '+title+'   ·   '+(project or '프로젝트 미지정'))
        if self.rows:
            self.records.selection_set(0)
        self.read_record()

    def read_record(self):
        pick=self.records.curselection()
        body=self.rows[pick[0]][3] if pick else '이 프로젝트에 저장한 경험이 아직 없어요.'
        self.reader.configure(state='normal')
        self.reader.delete('1.0','end')
        for line in body.splitlines():
            if line.startswith('#'):
                self.reader.insert('end',line.lstrip('# ').strip()+'\n','heading')
            else:
                self.reader.insert('end',line+'\n')
        self.reader.configure(state='disabled')

    def open_record(self):
        chosen=self.records.curselection()
        if chosen:
            self.open_obsidian(self.rows[chosen[0]][2])

    def open_obsidian(self,path):
        try:
            os.startfile(obsidian_uri(path))
        except OSError as exc:
            messagebox.showerror('Obsidian 열기',f'Obsidian을 실행할 수 없어요.\n{exc}',parent=self.win)

    def select_view(self,view):
        self.view=view
        self.paint_paper()
        for k,page in [('memo',self.memo_page),('final',self.final_page),('archive',self.archive_page),('calendar',self.calendar)]:
            page.pack_forget()
            self.tabs[k].place_configure(y=0 if k==view else 12)
            if k==view:
                page.pack(fill='both',expand=True)
        actions={'memo':('ChatGPT에서 대화하기',self.send_to_chatgpt),'final':('Obsidian에 저장',self.save_experience),
                 'archive':('Obsidian에서 열기',self.open_record)}
        if view=='calendar':
            self.flush()
            self.calendar.refresh()
            self.action.pack_forget()
            return
        self.action.pack(side='right')
        label,fn=actions[view]
        self.action.configure(text=label,command=fn)
        if view=='memo':
            self.redraw_tags()
        if view=='archive':
            self.refresh_archive()


    def _entry(self, parent, var):
        return tk.Entry(parent,textvariable=var,bg='#fff8eb',fg=BROWN,relief='flat',bd=0,highlightthickness=1,highlightbackground='#dfd0ad',
                        insertbackground=BROWN,font=cute_font(self.win,11))

    def _build_memo(self):
        from tkinter import font as tkfont
        tk.Label(self.memo_page,text='프로젝트 · 동아리',bg='#fffdf5',fg='#31563d',
                 font=cute_font(self.win,12,True)).pack(anchor='w',pady=(0,7))
        chips=tk.Canvas(self.memo_page,height=48,bg='#fffdf5',highlightthickness=0)
        chips.pack(fill='x')
        scroll=tk.Scrollbar(self.memo_page,orient='horizontal',command=chips.xview)
        chips.configure(xscrollcommand=scroll.set)
        def draw_tags(event=None):
            chips.delete('all')
            font=tkfont.Font(root=self.win,font=cute_font(self.win,10))
            names=self.app.store.project_names() if self.app.store else []
            x=3
            for i,name in enumerate([*names,None]):
                active=name is not None and self.project_var.get()==name
                label=('+ 새 태그' if name is None else ('✓ ' if active else '')+name)
                width=font.measure(label)+28
                color='#f7c600' if active else ['#c4ffb8','#ffbbbb','#ffe4b4','#c4ffb8'][i%4]
                tag='chip'+str(i)
                roundrect(chips,x,6,x+width,40,8,fill=color,outline=EDGE,width=1,tags=tag)
                chips.create_text(x+width/2,23,text=label,font=cute_font(self.win,10),fill='white' if active else BROWN,tags=tag)
                def choose(e,n=name):
                    if n is None: self.new_tag()
                    else: self.project_var.set('' if self.project_var.get()==n else n)
                chips.tag_bind(tag,'<Button-1>',choose)
                chips.tag_bind(tag,'<Enter>',lambda e:chips.configure(cursor='hand2'))
                chips.tag_bind(tag,'<Leave>',lambda e:chips.configure(cursor=''))
                x+=width+7
            chips.configure(scrollregion=(0,0,x,48))
            if x>chips.winfo_width() and not scroll.winfo_manager():
                scroll.pack(fill='x',after=chips)
            elif x<=chips.winfo_width() and scroll.winfo_manager():
                scroll.pack_forget()
        self.redraw_tags=draw_tags
        self.project_var.trace_add('write',lambda *_:draw_tags())
        chips.bind('<Configure>',draw_tags)
        sheet=tk.Frame(self.memo_page,bg=CREAM,highlightbackground=EDGE,highlightthickness=1)
        sheet.pack(fill='both',expand=True,pady=(12,0))
        self.raw=tk.Text(sheet,wrap='word',bg='white',fg=BROWN,relief='flat',bd=0,highlightthickness=0,
                  insertbackground=BROWN,font=cute_font(self.win,11),padx=14,pady=11,
                  selectbackground='#ffe6a5',undo=True,spacing2=4)
        self.raw.pack(fill='both',expand=True,padx=23,pady=(19,8))
        self.raw.bind('<<Modified>>',self.changed)
        tk.Label(sheet,text='오늘의 메모',bg=CREAM,fg=BROWN,
                 font=cute_font(self.win,12,True)).pack(anchor='w',padx=23)
        hint=tk.Label(sheet,bg=CREAM,fg=MUTED,wraplength=495,
                text='오늘 한 일, 새로 알게 된 점, 다음에 시도할 일을 적어 보세요.',
                font=cute_font(self.win,9))
        hint.pack(anchor='w',padx=23,pady=(3,10))

    def new_tag(self):
        if not self.app.store:
            messagebox.showinfo('프로젝트', '설정에서 Vault를 선택해 주세요.', parent=self.win)
            return
        name = simpledialog.askstring('새 프로젝트 태그', '프로젝트 이름', parent=self.win)
        if name:
            try:
                self.project_var.set(self.app.store.add_project(name))
            except (ValueError, OSError) as exc:
                messagebox.showerror('태그 추가', str(exc), parent=self.win)

    def _build_final(self):
        header=tk.Frame(self.final_page,bg='#fffdf5')
        header.pack(fill='x',pady=(0,7))
        tk.Label(header,text='경험 제목',bg='#fffdf5',fg=BROWN,
                 font=cute_font(self.win,12,True)).pack(anchor='w')
        self._entry(header,self.title_var).pack(fill='x',ipady=6,pady=(7,0))
        tk.Label(self.final_page,text='ChatGPT가 정리한 Markdown을 검토한 뒤 저장하세요.',
                 bg='#fffdf5',fg=MUTED,font=cute_font(self.win,9)).pack(anchor='w',pady=(11,5))
        sheet=tk.Frame(self.final_page,bg=CREAM,highlightbackground=EDGE,highlightthickness=1)
        sheet.pack(fill='both',expand=True)
        self.preview=tk.Text(sheet,wrap='word',bg='white',fg=BROWN,relief='flat',bd=0,highlightthickness=0,
                  insertbackground=BROWN,font=cute_font(self.win,10),padx=12,pady=9,
                  undo=True)
        self.preview.pack(fill='both',expand=True,padx=23,pady=(19,8))
        r=tk.Frame(sheet,bg=CREAM)
        r.pack(fill='x',padx=23,pady=(0,7))
        tk.Button(r,text='정리본 붙여넣기',command=self.paste_from_clipboard,
                bg='#ffe9b7',fg=BROWN,relief='flat',font=cute_font(self.win,9,True)).pack(side='left')
        tk.Button(r,text='빈 양식',command=self.make_template,
                bg='#f9ecd9',fg=BROWN,relief='flat',font=cute_font(self.win,9)).pack(side='right')

    def changed(self,event=None):
        if self.raw.edit_modified():
            self.raw.edit_modified(False)
            self.schedule_save()

    def schedule_save(self):
        if self.dirty_after:
            self.win.after_cancel(self.dirty_after)
        self.dirty_after=self.win.after(850,self.flush)

    def flush(self):
        self.dirty_after=None
        content=self.raw.get('1.0','end-1c')
        project=self.project_var.get().strip()
        if not content.strip():return False
        if not self.app.store:
            APP_DATA.mkdir(parents=True,exist_ok=True)
            drafts=APP_DATA/'drafts'
            drafts.mkdir(parents=True,exist_ok=True)
            (drafts/f'{self.backup_id}_경험일기.txt').write_text(content,encoding='utf-8')
            self.status.set('Vault가 연결되지 않아 로컬 임시 파일로 보관했어요. 설정에서 Vault를 선택해 주세요.')
            return False
        if self.session is None:self.session=self.app.store.new_session()
        try:
            self.source_path=self.app.store.autosave(self.session,content,project)
            self.status.set(f'✓ 오늘의 원본 기록 저장: {self.source_path.name}')
            return True
        except Exception as exc:
            APP_DATA.mkdir(parents=True,exist_ok=True)
            drafts=APP_DATA/'drafts'
            drafts.mkdir(parents=True,exist_ok=True)
            (drafts/f'{self.backup_id}_경험일기.txt').write_text(content,encoding='utf-8')
            self.status.set(f'Vault 저장 실패, 임시 파일로 백업: {exc}')
            return False

    def send_to_chatgpt(self):
        raw=self.raw.get('1.0','end-1c').strip()
        if not raw:
            messagebox.showinfo('오늘의 경험','어떤 일이 있었는지 한두 문장 먼저 적어 줘.',parent=self.win)
            return
        self.flush()
        related=self.app.store.related_notes(raw+' '+self.project_var.get()) if self.app.store else []
        prompt=make_gpt_prompt(raw,self.project_var.get(),related)
        prompt += ('\n\n[Experience Pet 플러그인]\n가능하다면 인터뷰가 끝난 뒤 검토한 경험 노트를 보여 주고, '
                   '사용자가 명시적으로 저장을 승인한 경우에만 save_experience_note 도구를 호출해. '
                   '플러그인이 연결되지 않았다면 저장에 성공한 척하지 말고 Markdown을 제공해.')
        self.win.clipboard_clear()
        self.win.clipboard_append(prompt)
        self.win.update()
        workspace=self.app.config.get('vault_path','')
        if open_interview(prompt,workspace):
            self.status.set('ChatGPT 앱에 인터뷰 질문을 채웠어요. Enter로 보내고 GPT의 꼬리질문에 답해 주세요.')
        else:
            kind=launch_chatgpt()
            self.status.set(f'프롬프트 복사 완료! ChatGPT {"앱" if kind=="app" else "웹"}에서 Ctrl+V → Enter로 시작해 주세요.')
        # Not a fake in-app AI chat: the real ChatGPT response appears in ChatGPT.

    def paste_from_clipboard(self):
        try:content=self.win.clipboard_get().strip()
        except tk.TclError:content=''
        if not content:
            messagebox.showinfo('붙여넣기','ChatGPT가 정리한 노트 텍스트를 먼저 복사해 줘.',parent=self.win)
            return
        self.preview.delete('1.0','end')
        title, markdown = normalize(content)
        if title and self.title_var.get() in ('', '오늘의 경험'):
            self.title_var.set(title)
        self.preview.insert('1.0',markdown)
        self.status.set('정리본을 붙여넣었어. 수치와 사실을 확인하고 최종 저장해 줘.')

    def make_template(self):
        raw=self.raw.get('1.0','end-1c').strip()
        _,body=normalize(raw)
        self.preview.delete('1.0','end')
        self.preview.insert('1.0',body)

    def save_experience(self):
        if not self.app.store:
            messagebox.showwarning('Vault 필요','캐릭터 우클릭 → 설정에서 Obsidian Vault를 선택해 줘.',parent=self.win)
            return
        body=self.preview.get('1.0','end-1c').strip()
        if not body:
            messagebox.showinfo('정리본 필요','ChatGPT의 최종 정리본을 붙여넣거나 양식을 채워 줘.',parent=self.win)
            return
        if not messagebox.askyesno('경험 노트 확정','수치와 사실을 확인했어?\n확정한 내용으로 새 노트를 저장할게.',parent=self.win):
            return
        try:
            self.flush()
            path=self.app.store.save_experience(self.title_var.get(),body,self.project_var.get(),self.source_path)
        except Exception as exc:
            messagebox.showerror('저장 실패',str(exc),parent=self.win)
        else:
            self.status.set(f'✓ 새 경험 노트 저장: {path.name}')
            if messagebox.askyesno('저장 완료',f'Obsidian에 저장했어!\n{path.name}\n\n노트를 열어 볼까?',parent=self.win):
                self.open_obsidian(path)

    def hide(self):
        self.flush()
        self.win.withdraw()

    def show(self):
        self.win.deiconify()
        self.win.lift()
        self.win.focus_force()
