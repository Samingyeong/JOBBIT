"""Calendar view for completed experiences and date-specific checklists."""
import calendar
from collections import defaultdict
from datetime import date, datetime
import re
import tkinter as tk
from tkinter import messagebox

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
    def __init__(self, parent, store, font, opener):
        super().__init__(parent, bg=PAPER)
        self.store, self.font, self.opener = store, font, opener
        self.selected = date.today()
        self.month = self.selected.replace(day=1)
        self.days = {}
        self.diaries = {}
        self.note_items = []
        self.todo_days = set()
        self.tasks = []
        bar = tk.Frame(self, bg=PAPER)
        bar.pack(fill='x')
        tk.Button(bar, text='‹', command=lambda: self.shift(-1), relief='flat',
                  bg=PAPER, font=font(13)).pack(side='left')
        self.caption = tk.Label(bar, bg=PAPER, fg=INK, font=font(13))
        self.caption.pack(side='left', padx=8)
        tk.Button(bar, text='›', command=lambda: self.shift(1), relief='flat',
                  bg=PAPER, font=font(13)).pack(side='left')
        self.board = tk.Canvas(self, bg=CREAM, height=166, highlightthickness=1, highlightbackground=EDGE)
        self.board.pack(fill='x', pady=(2, 4))
        self.board.bind('<Configure>', lambda _: self.draw())
        self.board.bind('<Button-1>', self.pick_day)

        self.day_label = tk.Label(self, bg=PAPER, fg=INK, font=font(10))
        self.day_label.pack(anchor='w')
        panels = tk.Frame(self, bg=PAPER)
        panels.pack(fill='both', expand=True)
        panels.columnconfigure((0, 1), weight=1, uniform='panel')
        panels.rowconfigure(0, weight=1)
        notes = tk.Frame(panels, bg=PAPER)
        notes.grid(row=0, column=0, sticky='nsew', padx=(0, 5))
        todo = tk.Frame(panels, bg=PAPER)
        todo.grid(row=0, column=1, sticky='nsew', padx=(5, 0))
        self.notes = self.make_list(notes, '완성 경험 · 원본 기록')
        self.notes.bind('<Double-Button-1>', self.open_note)
        self.notes.bind('<Return>', self.open_note)
        self.todo = self.make_list(todo, '할 일')
        self.todo.bind('<Double-Button-1>', self.toggle_selected)
        self.todo.bind('<space>', self.toggle_selected)
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
        self.toggle_button = tk.Button(entry_row, text='체크 전환', command=self.toggle_selected, bg=CREAM,
                                       relief='flat', font=font(9))
        self.toggle_button.pack(side='left')
        self.bind('<Configure>', self.fit_calendar)

    def make_list(self, parent, label):
        tk.Label(parent, text=label, bg=PAPER, fg=INK, font=self.font(10)).pack(anchor='w')
        bar = tk.Scrollbar(parent)
        bar.pack(side='right', fill='y')
        listing = tk.Listbox(parent, height=2, bg=CREAM, fg=INK, selectbackground='#f6cb75',
                             selectforeground=INK, exportselection=False, font=self.font(9),
                             yscrollcommand=bar.set)
        listing.pack(fill='both', expand=True)
        bar.configure(command=listing.yview)
        return listing

    def fit_calendar(self, event):
        height = max(103, min(190, int(event.height * .43)))
        if int(self.board.cget('height')) != height:
            self.board.configure(height=height)

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
        return weeks, max(self.board.winfo_width(), 1) / 7, max(self.board.winfo_height() - 22, 1) / len(weeks)

    def draw(self):
        self.board.delete('all')
        weeks, width, height = self.grid()
        self.caption.configure(text=f'{self.month.year}년 {self.month.month}월')
        for col, label in enumerate(('일', '월', '화', '수', '목', '금', '토')):
            self.board.create_text((col+.5)*width, 12, text=label, fill=INK, font=self.font(9))
        for row, week in enumerate(weeks):
            for col, number in enumerate(week):
                if not number:
                    continue
                day = self.month.replace(day=number)
                x, y = (col+.5)*width, 22+(row+.5)*height
                if day == self.selected:
                    self.board.create_rectangle(col*width+3, 22+row*height+1, (col+1)*width-3,
                                                22+(row+1)*height-1, fill='#fffdf5', outline=EDGE)
                self.board.create_text(x, y, text=number, fill=INK, font=self.font(9))
                if day in self.days:
                    self.board.create_oval(x+12,y-2,x+16,y+2,fill='#a34e43',outline='')
                elif day in self.diaries:
                    self.board.create_oval(x+12,y-2,x+16,y+2,fill='#ad8757',outline='')
                if day.isoformat() in self.todo_days:
                    self.board.create_oval(x+19,y-2,x+23,y+2,fill='#497641',outline='')

    def pick_day(self, event):
        weeks, width, height = self.grid()
        row, col = int((event.y-22)//height), int(event.x//width)
        if 0 <= row < len(weeks) and 0 <= col < 7 and weeks[row][col]:
            self.choose(self.month.replace(day=weeks[row][col]))

    def choose(self, day):
        if day != self.selected:
            self.entry.delete(0, 'end')
        self.selected = day
        self.draw()
        self.day_label.configure(text=f'{day.isoformat()} · 완성 경험과 할 일')
        self.notes.delete(0, 'end')
        self.note_items = [*self.days.get(day, []),
                           *((f'[원본] {title}',path) for title,path in self.diaries.get(day, []))]
        for title,_ in self.note_items:
            self.notes.insert('end',title)
        if not self.note_items:
            self.notes.insert('end', '이 날짜에 저장된 노트가 없어요.')
        self.refresh_tasks()

    def refresh_tasks(self):
        store = self.store()
        self.tasks = []
        self.todo.delete(0, 'end')
        state = 'normal' if store else 'disabled'
        for widget in (self.entry, self.add_button, self.toggle_button):
            widget.configure(state=state)
        if not store:
            self.todo.insert('end', '설정에서 Obsidian Vault를 선택해 주세요.')
            return
        try:
            self.tasks = tasks_for(task_path(store.root, self.selected))
        except (OSError, ValueError) as exc:
            self.todo.insert('end', str(exc))
            return
        for _, done, text in self.tasks:
            self.todo.insert('end', ('☑ ' if done else '☐ ') + text)
        if not self.tasks:
            self.todo.insert('end', '등록한 할 일이 없어요.')

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

    def toggle_selected(self, event=None):
        store, picked = self.store(), self.todo.curselection()
        if store and picked and picked[0] < len(self.tasks):
            try:
                toggle_task(task_path(store.root, self.selected), self.tasks[picked[0]])
            except (OSError, ValueError) as exc:
                messagebox.showerror('할 일 저장', str(exc), parent=self)
            self.refresh_tasks()
            if picked[0] < len(self.tasks):
                self.todo.selection_set(picked[0])
        return 'break'
