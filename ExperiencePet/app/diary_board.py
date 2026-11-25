import calendar
from collections import defaultdict
from datetime import date
import re
import tkinter as tk
from PIL import Image, ImageTk
from experience_format import split_note

def diaries(root):
    result=defaultdict(list)
    roots=[root]
    if root.name=='Career_Experience_Vault' and (root.parent/'.obsidian').is_dir():
        roots.append(root.parent)
    for base in roots:
        for path in sorted((base/'03 Daily Logs').glob('*.md')):
            meta,body=split_note(path.read_text(encoding='utf-8-sig'))
            stamp=re.search(r'^created:\s*["\']?(\d{4}-\d\d-\d\d)',meta,re.M)
            stamp=stamp or re.match(r'(\d{4}-\d\d-\d\d)',path.name)
            if not stamp:
                continue
            try: day=date.fromisoformat(stamp[1])
            except ValueError: continue
            title=re.search(r'^# (.+)',body,re.M)
            memo=body.partition('## 원본 메모')[2].partition('## 후속 정리')[0].strip() or body
            label=title[1] if title and title[1]!='오늘의 경험일기' else memo.splitlines()[0] if memo else path.stem
            result[day].append((label,path,memo))
    return result

class DiaryBoard(tk.Frame):
    def __init__(self,parent,store,font,assets,opener):
        super().__init__(parent,bg='#fffdf5')
        self.store,self.font,self.opener=store,font,opener
        self.month=date.today().replace(day=1)
        self.days={}
        head=Image.open(assets/'sprites/idle.png').convert('RGBA')
        head=head.crop((int(head.width*.12),0,int(head.width*.94),int(head.height*.55)))
        head.thumbnail((56,38),Image.Resampling.LANCZOS)
        self.face=ImageTk.PhotoImage(head)
        bar=tk.Frame(self,bg='#fffdf5')
        bar.pack(fill='x')
        tk.Button(bar,text='‹',command=lambda:self.shift(-1),font=font(15),relief='flat',
                  bg='#fffdf5',fg='#20201e').pack(side='left')
        self.caption=tk.Label(bar,bg='#fffdf5',fg='#20201e',font=font(14))
        self.caption.pack(side='left',padx=10)
        tk.Button(bar,text='›',command=lambda:self.shift(1),font=font(15),relief='flat',
                  bg='#fffdf5',fg='#20201e').pack(side='left')
        self.board=tk.Canvas(self,bg='#fdf5e4',height=270,highlightthickness=1,highlightbackground='#856341')
        self.board.pack(fill='x',pady=6)
        self.board.bind('<Configure>',lambda e:self.draw())
        self.selected=None
        self.detail=tk.Text(self,wrap='word',bg='#fffdf5',fg='#3b3a32',font=font(10),relief='flat',padx=8,pady=5,height=4)
        self.detail.pack(fill='both',expand=True)
        self.detail.tag_configure('title',font=font(12),foreground='#9b433b',spacing1=7)
        self.detail.configure(state='disabled')

    def shift(self,n):
        absolute=self.month.year*12+self.month.month-1+n
        self.month=date(absolute//12,absolute%12+1,1)
        self.refresh()

    def refresh(self):
        store=self.store()
        self.days=diaries(store.root) if store else {}
        available=[d for d in self.days if d.replace(day=1)==self.month]
        self.choose(self.selected if self.selected in available else max(available,default=None))

    def draw(self):
        c=self.board
        c.delete('all')
        width=max(c.winfo_width(),200)/7
        weeks=calendar.Calendar(firstweekday=calendar.SUNDAY).monthdayscalendar(self.month.year,self.month.month)
        self.caption.configure(text=f'{self.month.year}년 {self.month.month}월')
        for col,label in enumerate(('SUN','MON','TUE','WED','THU','FRI','SAT')):
            c.create_text((col+.5)*width,17,text=label,fill='#20201e',font=self.font(9))
        for row,week in enumerate(weeks):
            for col,num in enumerate(week):
                if not num: continue
                day=self.month.replace(day=num)
                x=(col+.5)*width
                y=32+(row+.5)*(230/len(weeks))
                tag='day'+str(num)
                if day in self.days:
                    if day==self.selected:
                        c.create_oval(x-30,y-16,x+30,y+16,fill='white',outline='#856341',tags=tag)
                    c.create_image(x-7,y,image=self.face,tags=tag)
                    c.create_text(x+18,y+5,text=num,fill='#5d332d',font=self.font(10),tags=tag)
                    c.tag_bind(tag,'<Button-1>',lambda e,d=day:self.choose(d))
                    c.tag_bind(tag,'<Enter>',lambda e:c.configure(cursor='hand2'))
                    c.tag_bind(tag,'<Leave>',lambda e:c.configure(cursor=''))
                else:
                    c.create_text(x,y,text=num,fill='#77869d',font=self.font(10))

    def choose(self,day):
        self.selected=day
        self.draw()
        t=self.detail
        t.configure(state='normal')
        t.delete('1.0','end')
        for i,(label,path,memo) in enumerate(self.days.get(day,[])):
            tag='note'+str(i)
            t.insert('end',label+'\n',('title',tag))
            t.tag_bind(tag,'<Button-1>',lambda e,p=path:self.opener(p))
            t.insert('end',memo+'\n\n')
        if not day: t.insert('end','이번 달에는 기록한 일기가 아직 없어요.')
        t.configure(state='disabled')
