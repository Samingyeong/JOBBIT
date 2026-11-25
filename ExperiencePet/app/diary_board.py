"""Calendar view for completed experiences and date-specific checklists."""
import calendar
from collections import defaultdict
from datetime import date, datetime
import re
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk

from daily_tasks import FOLDER, add_task, task_path, tasks_for, update_task
from experience_format import dated_history, read_note
from note_rows import NoteRows, rounded

PAPER = '#fffdf5'
CREAM = '#fdf5e4'
INK = '#20201e'
EDGE = '#856341'


def original_date(root,stem):
    roots=[root]
    if root.name=='Career_Experience_Vault' and (root.parent/'.obsidian').is_dir():
        roots.append(root.parent)
    for base in roots:
        path=base/'03 Daily Logs'/f'{stem.removesuffix(".md")}.md'
        try:
            if path.resolve()!=path:
                continue
            meta,_=read_note(path)
            stamp=re.search(r'^created:[ \t]*["\x27]?(\d{4}-\d\d-\d\d)',meta,re.M)
            stamp=stamp or re.match(r'(\d{4}-\d\d-\d\d)',path.name)
            if stamp:
                return date.fromisoformat(stamp[1])
        except (OSError,ValueError):
            continue
    return None


def experiences_by_day(root):
    result = defaultdict(list)
    for _,title,path,body,meta in dated_history(root):
        stamp = re.search(r'^(?:created|date):[ \t]*["\x27]?(\d{4}-\d\d-\d\d)', meta, re.M)
        stamp = stamp or re.match(r'(\d{4}-\d\d-\d\d)', path.name)
        source=re.search(r'^> 원본:[ \t]*\[\[03 Daily Logs/([^/\\|\]\n]+)',body,re.M)
        saved_date=original_date(root,source[1]) if source else None
        if saved_date:
            result[saved_date].append((title,path))
            continue
        try:
            day = date.fromisoformat(stamp[1]) if stamp else datetime.fromtimestamp(path.stat().st_mtime).date()
        except (ValueError, OSError):
            continue
        result[day].append((title, path))
    return result


class DiaryBoard(tk.Frame):
    def __init__(self, parent, store, font, opener, assets, paper_tile):
        super().__init__(parent, bg=PAPER)
        self.store, self.font, self.opener = store, font, opener
        self.selected = date.today()
        self.month = self.selected.replace(day=1)
        self.days = {}
        self.note_items = []
        self.todo_days = set()
        self.tasks = []
        self.paper_tile=paper_tile
        self.face=self.calendar_image(assets,907,(47,35))
        self.small_face=self.calendar_image(assets,907,(19,14))
        self.frog=self.calendar_image(assets,923,(52,57),11.19)
        self.corner=self.calendar_image(assets,920,(96,108))
        action_font=('Malgun Gothic',10,'bold')
        bar = tk.Frame(self, bg=PAPER)
        bar.pack(fill='x')
        tk.Button(bar, text='‹', command=lambda: self.shift(-1), relief='flat',
                  bg=PAPER, font=font(13)).pack(side='left')
        self.caption = tk.Label(bar, bg=PAPER, fg=INK, font=font(12,True))
        self.caption.pack(side='left', padx=8)
        tk.Button(bar, text='›', command=lambda: self.shift(1), relief='flat',
                  bg=PAPER, font=font(13)).pack(side='left')
        self.board = tk.Canvas(self, bg=PAPER, height=295, highlightthickness=0)
        self.board.pack(fill='x', pady=(7,7))
        self.board.bind('<Configure>', lambda _: self.draw())
        self.board.bind('<Button-1>', self.pick_day)

        panels = tk.Frame(self, bg=PAPER)
        panels.pack(fill='both', expand=True)
        panels.columnconfigure(0,weight=2,uniform='panel')
        panels.columnconfigure(1,weight=3,uniform='panel')
        panels.rowconfigure(0, weight=1)
        notes = tk.Frame(panels, bg=PAPER)
        notes.grid(row=0,column=1,sticky='nsew',padx=(10,0))
        todo = tk.Frame(panels, bg=PAPER)
        todo.grid(row=0,column=0,sticky='nsew',padx=(0,8))
        self.notes_heading=tk.StringVar(value='완성 경험')
        note_header=tk.Frame(notes,bg=PAPER)
        note_header.pack(fill='x')
        tk.Label(note_header,textvariable=self.notes_heading,bg=PAPER,fg=INK,font=font(11,True)).pack(side='left')
        tk.Button(note_header,text='노트 열기 ↗',command=self.open_note,bg='#ffefae',
                  activebackground='#ffd567',fg=INK,borderwidth=0,cursor='hand2',
                  font=action_font,padx=7,pady=1).pack(side='right')
        self.notes=NoteRows(notes,font(10),height=70,on_open=self.open_note,art=self.corner)
        self.notes.pack(fill='both',expand=True,pady=(5,0))
        tk.Label(todo,text='체크리스트',bg=PAPER,fg=INK,font=font(11,True)).pack(anchor='w')
        self.todo=tk.Canvas(todo,bg=PAPER,highlightthickness=0,height=42,takefocus=True)
        self.todo.pack(fill='both',expand=True)
        self.todo.bind('<Configure>',lambda _:self.draw_tasks())
        self.todo.bind('<MouseWheel>',self.scroll_tasks)
        self.todo.bind('<Button-1>',self.click_task)
        entry_row=tk.Frame(self,bg=CREAM,highlightbackground='#d5bea0',highlightthickness=1)
        entry_row.pack(side='bottom',fill='x',pady=(5,0),before=panels)
        tk.Label(entry_row,text='새 할 일',bg=CREAM,fg=INK,font=action_font).pack(side='left',padx=(7,6))
        self.entry=tk.Entry(entry_row,font=font(10),bg='white',fg=INK,relief='flat',borderwidth=0,
                            highlightbackground='#e1cfac',highlightcolor=EDGE,highlightthickness=1)
        self.entry.pack(side='left',fill='x',expand=True,ipady=1,pady=3)
        self.entry.bind('<Return>', self.add)
        self.add_button=tk.Button(entry_row,text='+ 할 일 추가',command=self.add,bg='#ffdf83',
                                  activebackground='#ffd567',fg=INK,relief='flat',cursor='hand2',
                                  font=action_font,padx=8,pady=1)
        self.add_button.pack(side='left',padx=(6,4),pady=3)
        self.bind('<Configure>', self.fit_calendar)

    def calendar_image(self,assets,number,size,rotation=0):
        with Image.open(assets/f'figma_calendar_{number}.png') as source:
            art=source.convert('RGBA')
        art=art.crop(art.getchannel('A').getbbox())
        if rotation:
            art=art.rotate(-rotation,Image.Resampling.BICUBIC,expand=True)
        art.thumbnail(size,Image.Resampling.LANCZOS)
        return ImageTk.PhotoImage(art,master=self)

    def fit_calendar(self, event):
        height = max(112,min(302,int(event.height*.55)))
        if int(self.board.cget('height')) != height:
            self.board.configure(height=height)

    def shift(self, amount):
        absolute = self.month.year * 12 + self.month.month - 1 + amount
        self.month = date(absolute // 12, absolute % 12 + 1, 1)
        self.choose(self.month)

    def refresh(self):
        store = self.store()
        self.days=experiences_by_day(store.root) if store else {}
        self.todo_days=set()
        if store:
            for path in (store.root/FOLDER).glob('*.md'):
                try:
                    day=date.fromisoformat(path.stem)
                    if tasks_for(task_path(store.root,day)):
                        self.todo_days.add(path.stem)
                except (OSError,ValueError):
                    continue
        self.choose(self.selected)

    def grid(self):
        weeks = calendar.Calendar(firstweekday=calendar.SUNDAY).monthdayscalendar(self.month.year, self.month.month)
        return weeks,max(self.board.winfo_width()-8,1)/7,max(self.board.winfo_height()-42,1)/len(weeks)

    def draw(self):
        self.board.delete('all')
        weeks, width, height = self.grid()
        self.caption.configure(text=f'{self.month.year}년 {self.month.month}월')
        w,h=self.board.winfo_width(),self.board.winfo_height()
        rounded(self.board,3,3,w-3,h-3,11,CREAM,EDGE)
        for col,label in enumerate(('SUN','MON','TUE','WED','THU','FRI','SAT')):
            self.board.create_text(4+(col+.5)*width,19,text=label,fill=INK,font=self.font(8,True))
        for row, week in enumerate(weeks):
            for col, number in enumerate(week):
                if not number:
                    continue
                day = self.month.replace(day=number)
                x,y=4+(col+.5)*width,37+(row+.5)*height
                marked=day in self.days or day.isoformat() in self.todo_days
                spacious=height>=32 and width>=54
                if day==self.selected:
                    radius=min(height*.41,19)
                    self.board.create_oval(x-25,y-radius,x+25,y+radius,fill='white',outline=EDGE)
                art=self.frog if day==self.selected else self.face
                if marked and spacious:
                    if day==self.selected:
                        self.board.create_image(x+27,y,image=art)
                    else:
                        self.board.create_image(x,y,image=art)
                if not (marked and spacious) or day==self.selected:
                    self.board.create_text(x-6 if marked and spacious else x,y,text=number,
                                           fill='#77869d',font=self.font(11,day==self.selected))
                if marked and not spacious:
                    self.board.create_image(x+18,y,image=self.small_face)

    def pick_day(self, event):
        weeks, width, height = self.grid()
        row,col=int((event.y-37)//height),int((event.x-4)//width)
        if 0 <= row < len(weeks) and 0 <= col < 7 and weeks[row][col]:
            self.choose(self.month.replace(day=weeks[row][col]))

    def choose(self, day):
        if day != self.selected:
            self.entry.delete(0, 'end')
        self.selected = day
        self.draw()
        self.note_items=self.days.get(day,[])
        self.notes_heading.set(f'완성 경험 ({len(self.note_items)})')
        self.notes.art=None if self.note_items else self.corner
        self.notes.set_rows([f'{i+1:02d}   {title}' for i,(title,_) in enumerate(self.note_items)],
                            placeholder='이 날짜에 저장된 완성 경험이 없어요.')
        self.refresh_tasks()

    def refresh_tasks(self):
        store = self.store()
        self.tasks = []
        self.todo.yview_moveto(0)
        state = 'normal' if store else 'disabled'
        for widget in (self.entry,self.add_button):
            widget.configure(state=state)
        self.todo_message='등록한 할 일이 없어요.'
        if not store:
            self.todo_message='설정에서 Obsidian Vault를 선택해 주세요.'
            self.draw_tasks()
            return
        try:
            self.tasks = tasks_for(task_path(store.root, self.selected))
        except (OSError, ValueError) as exc:
            self.todo_message=str(exc)
        self.draw_tasks()

    def draw_tasks(self):
        canvas=self.todo
        canvas.delete('all')
        w,h=canvas.winfo_width(),canvas.winfo_height()
        self.task_bounds=[]
        top=0
        if not self.tasks:
            canvas.create_text(10,14,text=getattr(self,'todo_message',''),anchor='w',
                               fill='#6d675e',font=self.font(9))
        for _,done,text in self.tasks:
            label=canvas.create_text(43,top+6,text=text,anchor='nw',fill=INK,font=self.font(10),
                                     width=max(24,w-70))
            bottom=max(top+32,canvas.bbox(label)[3]+6)
            y=top+16
            rounded(canvas,12,y-9,30,y+9,4,'#ffd567' if done else 'white','#b48c3c' if done else '#8b8376')
            if done:
                canvas.create_line(16,y,20,y+4,27,y-5,fill='white',width=2)
            canvas.create_text(w-13,y,text='×',fill='#994e44',font=self.font(12,True))
            self.task_bounds.append((top,bottom))
            top=bottom
        total=max(h,top)
        for x in range(0,w,274):
            for y in range(0,total,322):
                tile=canvas.create_image(x,y,image=self.paper_tile,anchor='nw')
                canvas.tag_lower(tile)
        canvas.configure(scrollregion=(0,0,w,total),yscrollincrement=24)

    def scroll_tasks(self,event):
        self.todo.yview_scroll(-1 if event.delta>0 else 1,'units')
        return 'break'

    def click_task(self,event):
        y=self.todo.canvasy(event.y)
        for index,(top,bottom) in enumerate(self.task_bounds):
            if top<=y<bottom:
                remove=event.x>=self.todo.winfo_width()-28
                if not remove or messagebox.askyesno('할 일 삭제','이 할 일을 삭제할까요?',parent=self):
                    self.toggle_task_at(index,remove=remove)
                break

    def open_note(self, event=None):
        picked = self.notes.selected
        items = self.note_items
        if picked is not None and picked<len(items):
            self.opener(items[picked][1])

    def add(self, event=None):
        store, text = self.store(), self.entry.get().strip()
        if not store or not text:
            return
        try:
            add_task(task_path(store.root, self.selected), self.selected, ' '.join(text.splitlines()))
        except (OSError, ValueError) as exc:
            messagebox.showerror('할 일 저장', str(exc), parent=self)
            return
        self.entry.delete(0, 'end')
        self.todo_days.add(self.selected.isoformat())
        self.refresh_tasks()
        self.draw()

    def toggle_task_at(self,index,*,remove=False):
        store=self.store()
        if store:
            try:
                update_task(task_path(store.root,self.selected),self.tasks[index],remove=remove)
            except (OSError, ValueError) as exc:
                messagebox.showerror('할 일 저장', str(exc), parent=self)
            self.refresh_tasks()
            if not self.tasks:
                self.todo_days.discard(self.selected.isoformat())
            self.draw()
