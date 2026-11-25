"""Calendar view for completed experiences and date-specific checklists."""
import calendar
from collections import defaultdict
from datetime import date, datetime
import re
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk

from daily_tasks import FOLDER, add_task, task_path, tasks_for, toggle_task
from experience_format import dated_history, note_paths, read_note

PAPER = '#fffdf5'
CREAM = '#fdf5e4'
INK = '#20201e'
EDGE = '#856341'


def experiences_by_day(root):
    result = defaultdict(list)
    for _, title, path, _, meta in dated_history(root):
        stamp = re.search(r'^(?:created|date):[ \t]*["\x27]?(\d{4}-\d\d-\d\d)', meta, re.M)
        stamp = stamp or re.match(r'(\d{4}-\d\d-\d\d)', path.name)
        try:
            day = date.fromisoformat(stamp[1]) if stamp else datetime.fromtimestamp(path.stat().st_mtime).date()
        except (ValueError, OSError):
            continue
        result[day].append((title, path))
    return result


def diaries_by_day(root):
    result = defaultdict(list)
    for path in note_paths(root, '03 Daily Logs'):
        try:
            meta,body = read_note(path)
            stamp = re.search(r'^created:[ \t]*["\x27]?(\d{4}-\d\d-\d\d)',meta,re.M)
            stamp = stamp or re.match(r'(\d{4}-\d\d-\d\d)',path.name)
            if stamp:
                memo = body.partition('## 원본 메모')[2].strip()
                label = memo.splitlines()[0] if memo else path.stem
                result[date.fromisoformat(stamp[1])].append((label,path))
        except (OSError, ValueError):
            continue
    return result


class DiaryBoard(tk.Frame):
    def __init__(self, parent, store, font, opener, assets, paper_tile):
        super().__init__(parent, bg=PAPER)
        self.store, self.font, self.opener = store, font, opener
        self.selected = date.today()
        self.month = self.selected.replace(day=1)
        self.days = {}
        self.diaries = {}
        self.note_items = []
        self.todo_days = set()
        self.tasks = []
        self.paper_tile=paper_tile
        self.face=self.calendar_image(assets,907,(47,35))
        self.small_face=self.calendar_image(assets,907,(19,14))
        self.frog=self.calendar_image(assets,923,(52,57),11.19)
        self.corner=self.calendar_image(assets,920,(94,108))
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
        panels.columnconfigure(0,weight=3,uniform='panel')
        panels.columnconfigure(1,weight=2,uniform='panel')
        panels.rowconfigure(0, weight=1)
        notes = tk.Frame(panels, bg=PAPER)
        notes.grid(row=0,column=1,sticky='nsew',padx=(15,0))
        todo = tk.Frame(panels, bg=PAPER)
        todo.grid(row=0,column=0,sticky='nsew',padx=(0,8))
        self.notes = self.make_list(notes, '완성 경험 · 원본 기록')
        self.notes.bind('<Double-Button-1>', self.open_note)
        self.notes.bind('<Return>', self.open_note)
        tk.Label(todo,text='체크리스트',bg=PAPER,fg=INK,font=font(11,True)).pack(anchor='w')
        self.todo=tk.Canvas(todo,bg=PAPER,highlightthickness=0,height=42,takefocus=True)
        self.todo.pack(fill='both',expand=True)
        self.todo.bind('<Configure>',lambda _:self.draw_tasks())
        self.todo.bind('<MouseWheel>',self.scroll_tasks)
        self.todo.bind('<Button-1>',self.click_task)
        self.badge=tk.Label(notes,image=self.corner,bg=PAPER,borderwidth=0)
        self.badge.place(relx=1,rely=1,anchor='se')
        self.badge.bind('<MouseWheel>',lambda event:self.notes.yview_scroll(-1 if event.delta>0 else 1,'units'))
        entry_row = tk.Frame(self, bg=PAPER)
        entry_row.pack(fill='x', pady=(4, 0))
        tk.Button(entry_row, text='노트 열기', command=self.open_note, bg=CREAM,
                  relief='flat', font=font(9)).pack(side='left', padx=(0,4))
        self.entry = tk.Entry(entry_row, font=font(10))
        self.entry.pack(side='left', fill='x', expand=True)
        self.entry.bind('<Return>', self.add)
        self.add_button = tk.Button(entry_row, text='할 일 추가', command=self.add, bg=CREAM,
                                    relief='flat', font=font(9))
        self.add_button.pack(side='left', padx=4)
        self.bind('<Configure>', self.fit_calendar)

    def calendar_image(self,assets,number,size,rotation=0):
        with Image.open(assets/f'figma_calendar_{number}.png') as source:
            art=source.convert('RGBA')
        art=art.crop(art.getchannel('A').getbbox())
        if rotation:
            art=art.rotate(-rotation,Image.Resampling.BICUBIC,expand=True)
        art.thumbnail(size,Image.Resampling.LANCZOS)
        return ImageTk.PhotoImage(art,master=self)

    def make_list(self, parent, label):
        tk.Label(parent,text=label,bg=PAPER,fg=INK,font=self.font(11,True)).pack(anchor='w')
        listing=tk.Listbox(parent,height=2,bg=PAPER,fg=INK,selectbackground='#ffefae',
                           selectforeground=INK,exportselection=False,font=self.font(10),
                           borderwidth=0,highlightthickness=0)
        listing.pack(fill='both', expand=True)
        return listing

    def fit_calendar(self, event):
        height = max(112,min(302,int(event.height*.55)))
        if int(self.board.cget('height')) != height:
            self.board.configure(height=height)
        if event.width>=560 and event.height>=402 and not self.note_items:
            self.badge.place(relx=1,rely=1,anchor='se')
        else:
            self.badge.place_forget()

    def shift(self, amount):
        absolute = self.month.year * 12 + self.month.month - 1 + amount
        self.month = date(absolute // 12, absolute % 12 + 1, 1)
        self.choose(self.month)

    def refresh(self):
        store = self.store()
        self.days = experiences_by_day(store.root) if store else {}
        self.diaries = diaries_by_day(store.root) if store else {}
        self.todo_days = {p.stem for p in (store.root / FOLDER).glob('*.md')} if store else set()
        self.choose(self.selected)

    def grid(self):
        weeks = calendar.Calendar(firstweekday=calendar.SUNDAY).monthdayscalendar(self.month.year, self.month.month)
        return weeks,max(self.board.winfo_width()-8,1)/7,max(self.board.winfo_height()-42,1)/len(weeks)

    def draw(self):
        self.board.delete('all')
        weeks, width, height = self.grid()
        self.caption.configure(text=f'{self.month.year}년 {self.month.month}월')
        w,h=self.board.winfo_width(),self.board.winfo_height()
        self.rounded(self.board,3,3,w-3,h-3,11,CREAM,EDGE)
        for col,label in enumerate(('SUN','MON','TUE','WED','THU','FRI','SAT')):
            self.board.create_text(4+(col+.5)*width,19,text=label,fill=INK,font=self.font(8,True))
        for row, week in enumerate(weeks):
            for col, number in enumerate(week):
                if not number:
                    continue
                day = self.month.replace(day=number)
                x,y=4+(col+.5)*width,37+(row+.5)*height
                marked=day in self.days or day in self.diaries or day.isoformat() in self.todo_days
                spacious=height>=32 and width>=54
                if day==self.selected:
                    radius=min(height*.41,19)
                    self.board.create_oval(x-25,y-radius,x+25,y+radius,fill='white',outline=EDGE)
                art=self.frog if day==self.selected else self.face
                if marked and spacious:
                    if day==self.selected:
                        self.board.create_image(x+19,y,image=art)
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
        self.notes.delete(0, 'end')
        self.note_items = [*self.days.get(day, []),
                           *((f'[원본] {title}',path) for title,path in self.diaries.get(day, []))]
        for title,_ in self.note_items:
            self.notes.insert('end',title)
        if not self.note_items:
            self.notes.insert('end', '이 날짜에 저장된 노트가 없어요.')
        if not self.note_items and self.winfo_width()>=560 and self.winfo_height()>=402:
            self.badge.place(relx=1,rely=1,anchor='se')
        else:
            self.badge.place_forget()
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

    @staticmethod
    def rounded(canvas,x1,y1,x2,y2,r,fill,outline):
        canvas.create_polygon(x1+r,y1,x2-r,y1,x2,y1,x2,y1+r,x2,y2-r,x2,y2,
                              x2-r,y2,x1+r,y2,x1,y2,x1,y2-r,x1,y1+r,x1,y1,
                              smooth=True,fill=fill,outline=outline)

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
                                     width=max(24,w-49))
            bottom=max(top+32,canvas.bbox(label)[3]+6)
            y=top+16
            self.rounded(canvas,12,y-9,30,y+9,4,'#ffd567' if done else 'white','#b48c3c' if done else '#8b8376')
            if done:
                canvas.create_line(16,y,20,y+4,27,y-5,fill='white',width=2)
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
                self.toggle_task_at(index)
                break

    def open_note(self, event=None):
        picked = self.notes.curselection()
        items = self.note_items
        if picked and picked[0] < len(items):
            self.opener(items[picked[0]][1])

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

    def toggle_task_at(self,index):
        store=self.store()
        if store:
            try:
                toggle_task(task_path(store.root,self.selected),self.tasks[index])
            except (OSError, ValueError) as exc:
                messagebox.showerror('할 일 저장', str(exc), parent=self)
            self.refresh_tasks()
