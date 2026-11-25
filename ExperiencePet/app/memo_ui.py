"""Cute memo-paper capture UI for Experience Pet.

ChatGPT remains a separate official desktop chat.  This module never
claims to receive its messages automatically without an API integration.
"""
from __future__ import annotations

import os
from math import sin
from pathlib import Path
import re
import sys
import uuid
from urllib.parse import unquote,urlsplit
import webbrowser
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
from PIL import Image, ImageOps, ImageTk

from diary_board import DiaryBoard
from experience_format import normalize, history, markdown_blocks, markdown_inline, obsidian_uri
from note_rows import NoteRows, rounded
from vault import APP_DATA, make_gpt_prompt
from chatgpt_desktop import open_interview
from winbridge import launch_chatgpt, notebook_caption

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
    if not bold:
        return ('Malgun Gothic', size, 'normal')
    return (cute_font._family, size, 'normal')


def roundrect(canvas, x1,y1,x2,y2,r, **kw):
    r = max(0, min(r, (x2-x1)/2, (y2-y1)/2))
    return canvas.create_polygon([
        x1+r,y1,x2-r,y1,x2,y1,x2,y1+r,x2,y2-r,x2,y2,
        x2-r,y2,x1+r,y2,x1,y2,x1,y2-r,x1,y1+r,x1,y1
    ], smooth=True, splinesteps=12, **kw)


class ProjectTagDialog(simpledialog.Dialog):
    def __init__(self,parent,add_project):
        self.add_project=add_project
        super().__init__(parent,'새 프로젝트 태그')

    def body(self,master):
        self.overrideredirect(True)
        self.configure(bg=CREAM,highlightbackground=EDGE,highlightthickness=1)
        master.configure(bg=CREAM,padx=7,pady=2)
        heading=tk.Frame(master,bg=CREAM)
        heading.pack(fill='x')
        tk.Label(heading,text='새 프로젝트 태그',bg=CREAM,fg=BROWN,
                 font=cute_font(self,10,True)).pack(side='left')
        tk.Button(heading,text='×',command=self.cancel,bg=CREAM,fg=BROWN,
                  relief='flat',font=cute_font(self,11),padx=4,pady=0).pack(side='right')
        self.name=tk.Entry(master,width=23,bg='white',fg=BROWN,relief='flat',
                           highlightthickness=1,highlightbackground=EDGE,font=cute_font(self,11))
        self.name.pack(fill='x',pady=(4,0),ipady=3)
        self.error=tk.Label(master,bg=CREAM,fg='#994e44',wraplength=275,
                            justify='left',font=cute_font(self,9))
        return self.name

    def buttonbox(self):
        actions=tk.Frame(self,bg=CREAM)
        actions.pack(fill='x',padx=12,pady=(0,8))
        for text,command,color in (('추가',self.ok,'#ffd567'),('취소',self.cancel,CREAM)):
            tk.Button(actions,text=text,command=command,bg=color,fg=BROWN,relief='flat',
                      cursor='hand2',font=cute_font(self,9,True),padx=9,pady=2).pack(side='right',padx=(5,0))
        self.bind('<Return>',self.ok)
        self.bind('<Escape>',self.cancel)

    def validate(self):
        try:
            self.result=self.add_project(self.name.get())
        except (ValueError,OSError) as exc:
            self.error.configure(text=str(exc))
            self.error.pack(anchor='w',pady=(6,0))
            return False
        return True


class CaptureWindow:
    WIDTH, HEIGHT=628, 792

    def __init__(self, app):
        self.app=app
        self.win=tk.Toplevel(app.root)
        self.win.withdraw()
        self.win.title('짱구의 경험 기록장')
        self.win.geometry(f'{self.WIDTH}x{self.HEIGHT}')
        self.win.minsize(self.WIDTH,self.HEIGHT)
        self.win.maxsize(self.WIDTH,self.HEIGHT)
        self.win.configure(bg=PALE)
        self.win.protocol('WM_DELETE_WINDOW',self.hide)
        try:
            self.window_icon=tk.PhotoImage(file=str(ASSETS/'shinchan_icon.png'),master=self.win)
            self.win.iconphoto(True,self.window_icon)
            self.win.iconbitmap(str(ASSETS/'shinchan_icon.ico'))
        except (OSError,tk.TclError):
            pass
        self.session=app.store.new_session() if app.store else None
        self.session_store=app.store
        self.backup_id=uuid.uuid4().hex[:12]
        self.source_path=None
        self.final_source=None
        self.pending_source=None
        self.source_explicit=False
        self.capture_choices=[]
        self.dirty_after=None
        self.title_var=tk.StringVar(value='오늘의 경험')
        self.project_var=tk.StringVar()
        self.status=tk.StringVar(value='메모는 입력 후 1초면 Obsidian에 원본으로 저장돼요.')
        self.view=None
        self._build()
        self.win.bind('<Control-Return>', lambda e:self.send_to_chatgpt())
        self.win.bind('<Control-s>', lambda e:self.flush())
        self.win.bind('<Control-Shift-S>', lambda e:self.save_experience())
        self.win.deiconify()
        self.win.after_idle(lambda:notebook_caption(self.win) if self.win.winfo_exists() else None)
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
        cover=tk.Frame(self.win,bg=LEMON)
        cover.pack(fill='both',expand=True)
        self.archive_art=None
        self.archive_grid=None
        self.archive_grid_size=None
        self.paper_layout=None
        banner=tk.Canvas(cover,bg=LEMON,highlightthickness=0)
        banner.place(x=0,y=0,relwidth=1,relheight=1)
        self.cover_face=self.design_image('914', (101,103), (1.2855,1.0817,-.1128,0), 15.74)
        self.cover_friend=self.design_image('919', (67,68), (1,1.9442,0,-.4725), 8.88)
        self.pattern_wide=self.design_image('911', (232,528), (1.5205,1.1888,-.4932,-.0863), -90)
        self.pattern_left=self.design_image('911', (304,528), (1.1604,1.1888,-.1494,-.0863))
        self.pattern_right=self.design_image('911', (333,448), (1,1.3204,0,-.0959), 173.47)

        tabs=(('memo','오늘 이야기','#f95e64'),('final','완성노트','#ffd768'),
              ('archive','경험모음','#81e66e'),('calendar','일기달력','#6775f7'))

        def draw_banner(event=None):
            width,height=banner.winfo_width(),banner.winfo_height()
            if width<=1:
                return
            center=width/2
            banner.delete('all')
            banner.create_image(-193,-41,image=self.pattern_wide,anchor='nw')
            banner.create_image(width-360,-41,image=self.pattern_wide,anchor='nw')
            banner.create_image(71,height-147,image=self.pattern_wide,anchor='nw')
            banner.create_image(-86,242,image=self.pattern_left,anchor='nw')
            banner.create_image(width-335,205,image=self.pattern_right,anchor='nw')
            from tkinter.font import Font
            title='짱구의 경험 기록장'
            font=Font(root=self.win,font=cute_font(self.win,26,True))
            max_width=max(width-222,150)
            while font.measure(title)>max_width and font.cget('size')>10:
                font.configure(size=font.cget('size')-1)
            self.banner_font=font
            banner.create_image(center-280,-6,image=self.cover_face,anchor='nw')
            banner.create_image(center+152,58,image=self.cover_friend,anchor='nw')
            banner.create_text(center,66,text=title,font=font,fill=BROWN)
            for index,(key,label,color) in enumerate(tabs):
                x,y=66+109*index,108 if key==self.view else 121
                shape=rounded(banner,x,y,x+100,158,8,color)
                banner.itemconfigure(shape,tags=(key,))
                banner.create_text(x+50,y+(145-y)/2,text=label,tags=(key,),
                                   font=cute_font(self.win,10,True),fill=BROWN)
                banner.tag_bind(key,'<Button-1>',lambda _,view=key:self.select_view(view))
                banner.tag_bind(key,'<Enter>',lambda _:banner.configure(cursor='hand2'))
                banner.tag_bind(key,'<Leave>',lambda _:banner.configure(cursor=''))
            self.draw_paper_edge(banner,width,height)
            if self.view=='archive' and width>48 and height>167:
                banner.create_image(24,150,image=self.archive_paper(width-48,height-167),anchor='nw')
                banner.create_image(width-112,64,image=self.archive_art[0],anchor='nw')
                banner.create_image(-39,height-120,image=self.archive_art[1],anchor='nw')

        banner.bind('<Configure>',draw_banner)
        self.draw_banner=draw_banner
        for index,(key,_,_) in enumerate(tabs,1):
            self.win.bind(f'<Alt-Key-{index}>',lambda _,view=key:self.select_view(view))
        paper=tk.Frame(cover,bg=PAPER)
        self.paper=paper
        paper.pack(fill='both',expand=True,padx=24,pady=(150,17))
        backing=tk.Canvas(paper,bg=PAPER,highlightthickness=0)
        backing.place(x=0,y=0,relwidth=1,relheight=1)
        self.paper_tile=self.design_image('906', (274,322), (1,1.4811,0,-.4811), opacity=.4)

        def paint_paper(event=None):
            width,height=backing.winfo_width(),backing.winfo_height()
            if min(width,height)<=1:
                return
            offset=-((backing.winfo_rootx()-cover.winfo_rootx()-24)%274)
            layout=(width,height,offset)
            if layout==self.paper_layout:
                return
            self.paper_layout=layout
            backing.delete('all')
            for y in range(0,height,322):
                for x in range(offset,width,274):
                    backing.create_image(x,y,image=self.paper_tile,anchor='nw')

        backing.bind('<Configure>',paint_paper)
        self.paint_paper=paint_paper
        self.page=tk.Frame(paper,bg=PAPER)
        self.page.pack(fill='both',expand=True,padx=36,pady=(24,8))
        self.memo_page=tk.Frame(self.page,bg='#fffdf5')
        self.final_page=tk.Frame(self.page,bg='#fffdf5')
        self.archive_page=tk.Frame(self.page,bg='#fffdf5')
        self._build_memo()
        self._build_final()
        self._build_archive()
        self.calendar=None
        self.action_row=tk.Frame(paper,bg=PAPER,pady=6)
        self.action_row.pack(side='bottom',fill='x',padx=40,before=self.page)
        self.action=self.button(self.action_row,'ChatGPT에서 대화하기',self.send_to_chatgpt,'#ffd567')
        self.action.pack(side='right')
        self.status_label=tk.Label(self.action_row,textvariable=self.status,bg=PAPER,fg=BROWN,
                                   wraplength=310,justify='left',font=cute_font(self.win,9))
        self.status_label.pack(side='left')
        self.project_var.trace_add('write',lambda *_:self.schedule_save())
        self.memo_footer=tk.Canvas(paper,bg=PAPER,height=112,highlightthickness=0)
        self.project_colors={}
        self.memo_badges=(
            self.design_image('901', (105,105), rotation=10.33, trim=True),
            self.design_image('904', (112,102), (2.2009,2.4154,-.5633,-.6824), 12.64, trim=True),
        )
        self.memo_footer.bind('<Configure>',self.draw_memo_footer)
        self.final_art=None
        self.select_view('memo')

    def draw_paper_edge(self,canvas,width,height):
        left,top,right,bottom=19,145,width-19,height-12
        points=[]
        for x in range(left+10,right-9,5):
            points.extend((x,top+sin(x*1.63)*1.5))
        for y in range(top+10,bottom-9,5):
            points.extend((right+sin(y*1.63)*1.5,y))
        for x in range(right-10,left+9,-5):
            points.extend((x,bottom+sin(x*1.63)*1.5))
        for y in range(bottom-10,top+9,-5):
            points.extend((left+sin(y*1.63)*1.5,y))
        if points:
            canvas.create_polygon(points,smooth=True,splinesteps=8,fill=PAPER,outline=EDGE,width=3)

    def make_art(self,parent,image,width,height,surfaces=()):
        art=tk.Canvas(parent,width=width,height=height,bg=PAPER,highlightthickness=0)

        def paint(_):
            art.delete('all')
            left=-(art.winfo_x()%274)
            top=-(art.winfo_y()%322)
            for x in range(left,width,274):
                for y in range(top,height,322):
                    art.create_image(x,y,image=self.paper_tile,anchor='nw')
            for widget,fill,outline in surfaces:
                x=widget.winfo_rootx()-art.winfo_rootx()
                y=widget.winfo_rooty()-art.winfo_rooty()
                art.create_rectangle(x,y,x+widget.winfo_width(),y+widget.winfo_height(),
                                     fill=fill,outline=outline)
            art.create_image(width/2,height,image=image,anchor='s')

        art.bind('<Configure>',paint)
        for widget,_,_ in surfaces:
            widget.bind('<Configure>',lambda event: art.after_idle(lambda:paint(event) if art.winfo_ismapped() else None),add='+')
        return art

    def archive_paper(self,width,height):
        if self.archive_grid_size!=(width,height):
            grid=tk.PhotoImage(master=self.win,width=width,height=height)
            for x in range(0,width,274):
                for y in range(0,height,322):
                    grid.tk.call(str(grid),'copy',str(self.paper_tile),'-from',0,0,
                                 min(274,width-x),min(322,height-y),'-to',x,y)
            self.archive_grid=grid
            self.archive_grid_size=(width,height)
        return self.archive_grid

    def draw_memo_footer(self, *_):
        footer=self.memo_footer
        width,height=footer.winfo_width(),footer.winfo_height()
        footer.delete('all')
        grid_y=-(footer.winfo_y()%322)
        for x in range(0,width,274):
            footer.create_image(x,grid_y,image=self.paper_tile,anchor='nw')
            footer.create_image(x,grid_y+322,image=self.paper_tile,anchor='nw')
        footer.create_rectangle(36,-1,width-37,height-12,fill=CREAM,outline='')
        footer.create_line(36,0,36,height-12,width-37,height-12,width-37,0,fill=EDGE)
        footer.create_text(63,16,text='오늘의 메모',font=cute_font(self.win,12,True),
                           fill=BROWN,anchor='w')
        project=self.project_var.get().strip()
        if project in self.project_colors:
            from tkinter.font import Font
            font=Font(root=self.win,font=cute_font(self.win,10))
            chip_width=min(font.measure(project)+20,max(100,width-220))
            fill,outline=self.project_colors[project]
            roundrect(footer,63,34,63+chip_width,63,8,fill=fill,outline=outline)
            footer.create_text(73,48,text=project,font=font,fill=BROWN,anchor='w',
                               width=chip_width-14)
        footer.create_image(3,height-3,image=self.memo_badges[0],anchor='sw')
        footer.create_image(width-3,height-3,image=self.memo_badges[1],anchor='se')

    def design_image(self, asset, size, crop=(1, 1, 0, 0), rotation=0, opacity=1, trim=False, mirror=False):
        width,height=size
        scale_x,scale_y,offset_x,offset_y=crop
        with Image.open(ASSETS/f'figma_{asset}.png') as source:
            scaled=source.convert('RGBA').resize(
                (round(width*scale_x),round(height*scale_y)),Image.Resampling.LANCZOS)
        result=Image.new('RGBA',size)
        result.paste(scaled,(round(width*offset_x),round(height*offset_y)))
        if rotation:
            result=result.rotate(-rotation,Image.Resampling.BICUBIC,expand=True)
        if mirror:
            result=ImageOps.mirror(result)
        if opacity<1:
            result.putalpha(result.getchannel('A').point(lambda alpha:round(alpha*opacity)))
        if trim:
            result=result.crop(result.getchannel('A').getbbox())
            result.thumbnail((105,105),Image.Resampling.LANCZOS)
        return ImageTk.PhotoImage(result,master=self.win)

    def _build_archive(self):
        self.archive_state=None
        self.archive_rows=[]
        self.rows=[]
        self.archive_query_after=None
        self.new_archive_path=None
        self.rendered_record=None
        self.reader_tables=[]
        self.reader_links=[]
        self.library_project=tk.StringVar(value='전체 프로젝트')
        project_font=('Malgun Gothic',10,'bold')
        self.filter_button=tk.Menubutton(self.archive_page,textvariable=self.library_project,
                              bg=PAPER,fg=BROWN,relief='flat',padx=0,pady=3,cursor='hand2',
                              font=('Malgun Gothic',11,'bold'))
        self.filter_button.pack(anchor='w')
        self.filters=tk.Menu(self.filter_button,tearoff=False,font=project_font)
        self.filter_button.configure(menu=self.filters)
        self.archive_query=tk.StringVar()
        search=tk.Frame(self.archive_page,bg=PAPER)
        search.pack(fill='x',pady=(3,4))
        tk.Label(search,text='경험 검색',bg=PAPER,fg=BROWN,font=project_font).pack(side='left',padx=(0,8))
        self.archive_search=tk.Entry(search,textvariable=self.archive_query,bg='white',fg=BROWN,
                                     font=cute_font(self.win,10),relief='flat',highlightthickness=1,
                                     highlightbackground='#d5bea0',highlightcolor=EDGE)
        self.archive_search.pack(side='left',fill='x',expand=True,ipady=3)
        self.archive_search.bind('<Escape>',lambda _:self.archive_query.set(''))
        self.archive_query.trace_add('write',self.schedule_archive_query)
        record_panel=tk.Frame(self.archive_page,bg=PAPER)
        record_panel.pack(fill='x',pady=(4,9))
        self.records=NoteRows(record_panel,project_font,height=157,
                              on_select=self.read_record,on_open=self.open_record)
        self.records.pack(side='left',fill='both',expand=True)
        self.records.show_whole_rows()
        reading_area=tk.Frame(self.archive_page,bg=PAPER)
        reading_area.pack(fill='both',expand=True)
        self.reader=tk.Text(reading_area,wrap='word',bg='#fffdf5',fg=BROWN,
                        bd=0,highlightthickness=0,padx=8,pady=4,font=cute_font(self.win,11))
        self.reader.tag_configure('heading',font=cute_font(self.win,13,True),foreground='#994e44',spacing1=10)
        for name,weight,slant in (('bold','bold','roman'),('italic','normal','italic'),
                                  ('bold_italic','bold','italic')):
            self.reader.tag_configure(name,font=('Malgun Gothic',11,weight,slant))
        self.reader.tag_configure('code',font=('Consolas',10),background=CREAM)
        self.reader.tag_configure('link',foreground='#335880',underline=True)
        self.reader.tag_bind('link','<Enter>',lambda _:self.reader.configure(cursor='hand2'))
        self.reader.tag_bind('link','<Leave>',lambda _:self.reader.configure(cursor=''))
        self.reader.pack(fill='both',expand=True)
        self.reader.bind('<Configure>',self.resize_reader_tables)
        self.reader.configure(state='disabled')

    def refresh_archive(self):
        self.archive_rows=history(self.app.store.root) if self.app.store else []
        names=set(self.app.store.project_names()) if self.app.store else set()
        names.update(p for p,*_ in self.archive_rows if p)
        self.filters.delete(0,'end')
        for name in ['전체 프로젝트',*sorted(names),'프로젝트 미지정']:
            self.filters.add_command(label=name,command=lambda project=name:self.filter_archive(project))
        self.filter_archive()

    def schedule_archive_query(self,*_):
        if self.archive_query_after is not None:
            self.win.after_cancel(self.archive_query_after)
        self.archive_query_after=self.win.after(110,self.filter_archive)

    def filter_archive(self,project=None):
        if self.archive_query_after is not None:
            self.win.after_cancel(self.archive_query_after)
            self.archive_query_after=None
        if project is not None:
            self.library_project.set(project)
        choice=self.library_project.get()
        terms=self.archive_query.get().casefold().split()
        state=(self.archive_rows,choice,terms)
        target=self.new_archive_path
        self.new_archive_path=None
        if state==self.archive_state and target is None:
            return
        self.archive_state=state
        previous=self.records.selected
        if target is None and previous is not None:
            target=self.rows[previous][2]
        self.rows=[]
        labels=[]
        for row in self.archive_rows:
            project,title,*_=row
            project=project or '프로젝트 미지정'
            label=f'[{project}] - {title}'
            searchable=label.casefold()
            if (choice=='전체 프로젝트' or project==choice) and all(term in searchable for term in terms):
                self.rows.append(row)
                labels.append(label)
        index=next((i for i,row in enumerate(self.rows) if row[2]==target),0)
        placeholder='검색 결과가 없어요.' if terms else '저장된 경험이 없어요.'
        self.records.set_rows(labels,selected=index,placeholder=placeholder)
        self.read_record()

    def read_record(self):
        pick=self.records.selected
        row=self.rows[pick] if pick is not None else None
        body=row[3] if row else self.records.placeholder
        record=(row[2] if row else None,body)
        if record==self.rendered_record:
            return
        self.rendered_record=record
        self.reader.configure(state='normal')
        for table,_,_,_ in self.reader_tables:
            table.destroy()
        self.reader_tables.clear()
        for tag in self.reader_links:
            self.reader.tag_delete(tag)
        self.reader_links.clear()
        self.reader.delete('1.0','end')
        if row and not body.startswith('# '):
            self.insert_reader_line(row[1],('heading',))
        fence=None
        for block in markdown_blocks(body):
            if isinstance(block,list):
                self.insert_reader_table(block)
                continue
            marker=re.match(r'^ {0,3}(`{3,}|~{3,})(.*)$',block)
            if marker and (fence is None or marker[1].startswith(fence) and not marker[2].strip()):
                fence=None if fence else marker[1]
            elif fence:
                self.reader.insert('end',block+'\n','code')
            else:
                heading=re.match(r'^#{1,6}\s+(.*)$',block)
                if heading:
                    self.insert_reader_line(heading[1],('heading',))
                else:
                    self.insert_reader_line(re.sub(r'^(\s*)[-*+]\s+',r'\1• ',block))
        self.reader.configure(state='disabled')

    def insert_reader_line(self,line,base=()):
        for text,styles,link in markdown_inline(line):
            tags=base
            emphasis=set(styles)
            if 'code' in emphasis:
                tags+=('code',)
            elif emphasis:
                tags+=('bold_italic' if {'bold','italic'}<=emphasis else next(iter(emphasis)),)
            if link:
                tag=f'reader_link_{len(self.reader_links)}'
                self.reader_links.append(tag)
                tags+=('link',tag)
                self.reader.tag_bind(tag,'<Button-1>',lambda _,target=link:self.follow_reader_link(*target))
            self.reader.insert('end',text,tags)
        self.reader.insert('end','\n')

    def follow_reader_link(self,kind,target):
        try:
            url=urlsplit(target)
        except ValueError:
            return
        if kind=='link' and url.scheme in ('https','http') and url.hostname:
            webbrowser.open(target)
            return
        store=self.app.store
        selected=self.records.selected
        if not store or selected is None or kind=='link' and (url.scheme or url.netloc):
            return
        root=store.root
        path=Path(unquote(url.path))
        source=self.rows[selected][2]
        if not path.name:
            self.open_obsidian(source)
            return
        if path.suffix.lower()!='.md' and kind=='wiki':
            path=path.parent/(path.name+'.md')
        vault=root.parent if (root.parent/'.obsidian').is_dir() else root
        bases=(root,vault,source.parent) if kind=='wiki' else (source.parent,root)
        for base in bases:
            resolved=(base/path).resolve()
            if resolved.is_relative_to(vault) and resolved.is_file():
                self.open_obsidian(resolved)
                return
        if kind=='wiki' and len(path.parts)==1:
            matches=[p for p in vault.rglob('*.md') if p.name.casefold()==path.name.casefold()
                     and p.resolve().is_relative_to(vault)]
            if len(matches)==1:
                self.open_obsidian(matches[0])
                return
        messagebox.showinfo('링크 열기','Vault에서 연결된 노트를 찾을 수 없어요.',parent=self.win)

    def insert_reader_table(self, rows):
        table=tk.Frame(self.reader,bg=EDGE,padx=1,pady=1)
        labels=[]
        from tkinter.font import Font
        fonts=[Font(root=self.win,font=cute_font(self.win,10,bold)) for bold in (True,False)]
        preferred=[94]*len(rows[0])
        for row,values in enumerate(rows):
            for column,value in enumerate(values):
                display=''.join(part for part,_,_ in markdown_inline(value))
                preferred[column]=max(preferred[column],min(275,fonts[row!=0].measure(display)+15))
                label=tk.Label(table,text=display,justify='left',anchor='w',
                               bg='#fff5d9' if row==0 else PAPER,fg=BROWN,padx=5,pady=3,
                               font=cute_font(self.win,10,row==0))
                label.source_text=display
                label.measure=fonts[row!=0].measure
                labels.append(label)
                label.bind('<MouseWheel>',self.scroll_reader)
        table.bind('<MouseWheel>',self.scroll_reader)
        self.reader.window_create('end',window=table)
        self.reader.insert('end','\n')
        layout=(table,len(rows),preferred,labels)
        self.reader_tables.append(layout)
        self.resize_reader_table(*layout)

    def resize_reader_tables(self,event=None):
        for layout in self.reader_tables:
            self.resize_reader_table(*layout)

    def scroll_reader(self,event):
        self.reader.yview_scroll(-3 if event.delta>0 else 3,'units')
        return 'break'

    def resize_reader_table(self,table,row_count,preferred,labels):
        available=max(120,self.reader.winfo_width()-2*int(self.reader.cget('padx'))-6)
        columns=len(preferred)
        visible=min(columns,max(1,available//56))
        key=(available,visible)
        if getattr(table,'layout_key',None)==key:
            return
        table.layout_key=key
        for column in range(columns):
            table.columnconfigure(column,minsize=0)
        for index,label in enumerate(labels):
            row,column=divmod(index,columns)
            group,slot=divmod(column,visible)
            label.grid(row=group*row_count+row,column=slot,sticky='nsew',
                       padx=(0,1 if slot<visible-1 else 0),pady=(0,1))
        usable=available-2
        columns_used=min(columns,visible)
        remainder=max(0,usable-56*columns_used)
        weights=preferred[:columns_used] if columns_used==columns else [1]*columns_used
        widths=[56+remainder*weight//sum(weights) for weight in weights]
        widths[-1]+=usable-sum(widths)
        for slot,width in enumerate(widths):
            table.columnconfigure(slot,minsize=width)
        for index,label in enumerate(labels):
            width=max(1,widths[(index%columns)%visible]-15)
            text=re.sub(r'\S+',lambda match:self.wrap_table_word(match[0],label.measure,width),
                        label.source_text)
            label.configure(text=text,wraplength=width)

    @staticmethod
    def wrap_table_word(word,measure,width):
        if measure(word)<=width:
            return word
        pieces=[]
        part=''
        for character in word:
            if part and measure(part+character)>width:
                pieces.append(part)
                part=''
            part+=character
        pieces.append(part)
        return '\n'.join(pieces)

    def open_record(self):
        chosen=self.records.selected
        if chosen is not None:
            self.open_obsidian(self.rows[chosen][2])

    def open_obsidian(self,path):
        try:
            os.startfile(obsidian_uri(path))
        except OSError as exc:
            messagebox.showerror('Obsidian 열기',f'Obsidian을 실행할 수 없어요.\n{exc}',parent=self.win)

    def select_view(self,view):
        if self.view==view:
            return
        if view=='calendar' and self.calendar is None:
            self.calendar=DiaryBoard(self.page,lambda:self.app.store,
                                     lambda size,bold=False:cute_font(self.win,size,bold),
                                     self.open_obsidian,ASSETS,self.paper_tile)
        if view=='archive' and self.archive_art is None:
            self.archive_art=(self.design_image('902',(125,253),(2.0177,1,-.5265,0),mirror=True),
                              self.design_image('921',(133,133),mirror=True))
        if view=='final' and self.final_art is None:
            self.final_art=self.make_art(self.paper,self.design_image('917',(160,158)),160,158,
                                         ((self.final_sheet,CREAM,EDGE),(self.preview,'white','')))
        self.view=view
        self.paper.pack_configure(padx=(69,89) if view=='archive' else 24)
        self.draw_banner()
        self.win.after_idle(self.paint_paper)
        self.memo_footer.pack_forget()
        if self.final_art:
            self.final_art.place_forget()
        self.page.pack_configure(padx=2 if view=='archive' else 36,
                                 pady=(24,0 if view=='memo' else 8))
        for k,page in [('memo',self.memo_page),('final',self.final_page),('archive',self.archive_page),('calendar',self.calendar)]:
            if page is None:
                continue
            page.pack_forget()
            if k==view:
                page.pack(fill='both',expand=True)
        actions={'memo':('ChatGPT에서 대화하기',self.send_to_chatgpt),'final':('Obsidian에 저장',self.save_experience),
                 'archive':('Obsidian에서 열기',self.open_record)}
        if view=='calendar':
            self.action.pack_forget()
            self.action_row.pack_forget()
            self.win.after_idle(lambda:self.calendar.refresh() if self.view=='calendar' else None)
            return
        if not self.action_row.winfo_manager():
            self.action_row.pack(side='bottom',fill='x',padx=40,before=self.page)
        self.action.pack(side='right')
        self.status_label.configure(wraplength=205 if view=='final' else 310)
        self.status_label.pack_configure(padx=(115,0) if view=='final' else (0,0))
        label,fn=actions[view]
        self.action.configure(text=label,command=fn)
        if view=='memo':
            self.memo_footer.pack(side='bottom',fill='x',before=self.page)
            self.redraw_tags()
        if view=='final':
            self.final_art.place(x=-24,rely=1,y=24,anchor='sw')
            if self.dirty_after is not None:
                self.flush()
            self.refresh_capture_choices()
        if view=='archive':
            self.win.after_idle(lambda:self.refresh_archive() if self.view=='archive' else None)


    def _entry(self, parent, var):
        return tk.Entry(parent,textvariable=var,bg='#fff8eb',fg=BROWN,relief='flat',bd=0,highlightthickness=1,highlightbackground='#dfd0ad',
                        insertbackground=BROWN,font=cute_font(self.win,11))

    def _build_memo(self):
        from tkinter import font as tkfont
        tk.Label(self.memo_page,text='프로젝트 · 동아리',bg='#fffdf5',fg='#31563d',
                 font=cute_font(self.win,12,True)).pack(anchor='w',pady=(0,7))
        tag_row=tk.Frame(self.memo_page,bg=PAPER)
        tag_row.pack(fill='x')
        self.button(tag_row,'+ 새 태그',self.new_tag,'#ffefae').pack(side='left',padx=(0,8),pady=5)
        tk.Frame(tag_row,bg=EDGE,width=1).pack(side='left',fill='y',pady=10,padx=(0,8))
        chips=tk.Canvas(tag_row,height=48,bg=PAPER,highlightthickness=0)
        chips.pack(fill='x')
        scroll=tk.Scrollbar(self.memo_page,orient='horizontal',command=chips.xview)
        chips.configure(xscrollcommand=scroll.set)
        def draw_tags(event=None):
            chips.delete('all')
            font=tkfont.Font(root=self.win,family='Malgun Gothic',size=10,weight='bold')
            names=self.app.store.project_names() if self.app.store else []
            colors=[('#c5ffba','#37812a'),('#ffbdbd','#ad4848'),('#ffe7ba','#a86727')]
            self.project_colors={name:colors[i%len(colors)] for i,name in enumerate(names)}
            x=3
            for i,name in enumerate(names):
                active=self.project_var.get()==name
                label=('✓ ' if active else '')+name
                width=font.measure(label)+22
                color,border=self.project_colors[name]
                tag='chip'+str(i)
                roundrect(chips,x,5,x+width,41,8,fill=color,outline=border,width=2 if active else 1,tags=tag)
                chips.create_text(x+width/2,23,text=label,font=font,fill=BROWN,tags=tag)
                def choose(e,n=name):
                    self.project_var.set('' if self.project_var.get()==n else n)
                chips.tag_bind(tag,'<Button-1>',choose)
                chips.tag_bind(tag,'<Enter>',lambda e:chips.configure(cursor='hand2'))
                chips.tag_bind(tag,'<Leave>',lambda e:chips.configure(cursor=''))
                x+=width+7
            self.chip_font=font
            chips.configure(scrollregion=(0,0,x,48))
            if x>chips.winfo_width() and not scroll.winfo_manager():
                scroll.pack(fill='x',after=tag_row)
            elif x<=chips.winfo_width() and scroll.winfo_manager():
                scroll.pack_forget()
            self.draw_memo_footer()
        self.redraw_tags=draw_tags
        self.project_var.trace_add('write',lambda *_:draw_tags())
        chips.bind('<Configure>',draw_tags)
        sheet=tk.Frame(self.memo_page,bg=CREAM)
        sheet.pack(fill='both',expand=True,pady=(12,0))
        for edge,position in (('top',dict(relwidth=1,height=1)),('left',dict(relheight=1,width=1)),
                              ('right',dict(relx=1,relheight=1,width=1,anchor='ne'))):
            tk.Frame(sheet,bg=EDGE,name=f'border_{edge}').place(**position)
        self.raw=tk.Text(sheet,wrap='word',bg='white',fg=BROWN,relief='flat',bd=0,highlightthickness=0,
                  insertbackground=BROWN,font=cute_font(self.win,11),padx=14,pady=11,
                  selectbackground='#ffe6a5',undo=True,spacing2=4)
        self.raw.pack(fill='both',expand=True,padx=23,pady=(19,6))
        self.raw.bind('<<Modified>>',self.changed)
        self.button(tag_row,'임시저장',self.save_capture_draft,'#ffefae').pack(side='right',padx=(6,0),before=chips)

    def new_tag(self):
        if not self.app.store:
            messagebox.showinfo('프로젝트', '설정에서 Vault를 선택해 주세요.', parent=self.win)
            return
        dialog=ProjectTagDialog(self.win,self.app.store.add_project)
        if dialog.result:
            self.project_var.set(dialog.result)

    def _build_final(self):
        header=tk.Frame(self.final_page,bg=PAPER)
        header.pack(fill='x',pady=(0,21))
        tk.Label(header,text='경험 제목',bg=PAPER,fg=BROWN,
                 font=cute_font(self.win,12,True)).pack(anchor='w')
        tk.Entry(header,textvariable=self.title_var,bg=PAPER,fg=BROWN,relief='flat',
                 bd=0,highlightthickness=0,insertbackground=BROWN,
                 font=cute_font(self.win,16,True)).pack(fill='x',padx=(12,0),ipady=5,pady=(7,0))
        self.title_rule=ImageTk.PhotoImage(file=str(ASSETS/'figma_title_rule.png'),master=self.win)
        rule=tk.Canvas(header,bg=PAPER,height=self.title_rule.height(),highlightthickness=0)
        rule.pack(fill='x')
        rule.create_image(0,0,image=self.title_rule,anchor='nw')
        source_row=tk.Frame(header,bg=PAPER)
        source_row.pack(fill='x',pady=(8,0))
        tk.Label(source_row,text='해당 경험',bg=PAPER,fg=BROWN,
                 font=('Malgun Gothic',10,'bold')).pack(side='left',padx=(0,8))
        self.source_combo=ttk.Combobox(source_row,state='readonly',width=1,font=cute_font(self.win,10))
        self.source_combo.pack(side='left',fill='x',expand=True)
        self.source_combo.bind('<<ComboboxSelected>>',self.pick_capture)
        self.button(source_row,'+ 경험 추가',self.start_new_capture,'#ffefae').pack(side='right',padx=(7,0))
        sheet=tk.Frame(self.final_page,bg=CREAM,highlightbackground=EDGE,highlightthickness=1)
        self.final_sheet=sheet
        sheet.pack(fill='both',expand=True)
        self.preview=tk.Text(sheet,wrap='word',bg='white',fg=BROWN,relief='flat',bd=0,highlightthickness=0,
                  insertbackground=BROWN,font=cute_font(self.win,10),padx=12,pady=9,
                  undo=True)
        r=tk.Frame(sheet,bg=CREAM)
        r.pack(side='bottom',fill='x',padx=23,pady=(0,7))
        tk.Button(r,text='정리본 붙여넣기',command=self.paste_from_clipboard,
                bg='#ffe9b7',fg=BROWN,relief='flat',font=cute_font(self.win,9,True)).pack(side='right',padx=(7,0))
        tk.Button(r,text='빈 양식',command=self.make_template,
                bg='#f9ecd9',fg=BROWN,relief='flat',font=cute_font(self.win,9)).pack(side='right')
        self.preview.pack(fill='both',expand=True,padx=23,pady=(19,8))

    def changed(self,event=None):
        if self.raw.edit_modified():
            self.raw.edit_modified(False)
            self.schedule_save()

    def schedule_save(self):
        if self.dirty_after:
            self.win.after_cancel(self.dirty_after)
        self.dirty_after=self.win.after(850,self.flush)

    def refresh_capture_choices(self):
        store=self.app.store
        self.capture_choices=store.capture_sources() if store else []
        labels=['연결하지 않음']
        for capture in self.capture_choices:
            stamp=capture.created[:16].replace('T',' ') or '날짜 미확인'
            labels.append(f'{stamp} · {capture.title}')
        if self.final_source is None and not self.source_explicit:
            self.final_source=self.source_path
        index=next((i for i,capture in enumerate(self.capture_choices,1)
                    if capture.path==self.final_source),0)
        self.source_combo.configure(values=labels)
        if self.final_source is not None and not index:
            self.source_combo.set('연결한 원본을 찾을 수 없어요')
        else:
            self.source_combo.current(index)

    def pick_capture(self,event=None):
        index=self.source_combo.current()
        self.final_source=self.capture_choices[index-1].path if index>0 else None
        self.source_explicit=True
        self.pending_source=None

    def save_capture_draft(self):
        if not self.raw.get('1.0','end-1c').strip():
            self.status.set('임시저장할 메모를 먼저 적어 주세요.')
        elif self.flush():
            if self.final_source is None or not self.preview.get('1.0','end-1c').strip():
                self.final_source=self.source_path
            self.status.set('임시저장했어요. 완성노트의 해당 경험에서 선택할 수 있어요.')

    def start_new_capture(self):
        if self.raw.get('1.0','end-1c').strip() and not self.flush():
            self.select_view('memo')
            return
        self.raw.delete('1.0','end')
        self.raw.edit_modified(False)
        self.raw.edit_reset()
        self.session=None
        self.source_path=None
        self.select_view('memo')
        self.raw.focus_set()
        self.status.set('새 경험을 적어 주세요. 기존 메모는 완성노트에서 선택할 수 있어요.')

    def flush(self):
        if self.dirty_after is not None:
            self.win.after_cancel(self.dirty_after)
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
        if self.session_store is not self.app.store:
            self.session_store=self.app.store
            self.session=None
            self.source_path=None
        if self.session is None:self.session=self.app.store.new_session()
        try:
            previous=self.source_path
            self.source_path=self.app.store.autosave(self.session,content,project)
            if previous is not None and previous!=self.source_path:
                if self.final_source==previous:
                    self.final_source=self.source_path
                if self.pending_source==previous:
                    self.pending_source=self.source_path
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
        self.pending_source=None
        if self.flush():
            self.pending_source=self.source_path
            if not self.preview.get('1.0','end-1c').strip():
                self.final_source=self.source_path
                self.source_explicit=True
        related=self.app.store.related_notes(raw+' '+self.project_var.get()) if self.app.store else []
        prompt=make_gpt_prompt(raw,self.project_var.get(),related)
        prompt += ('\n\n[Experience Pet 플러그인]\n가능하다면 인터뷰가 끝난 뒤 검토한 경험 노트를 보여 주고, '
                   '사용자가 명시적으로 저장을 승인한 경우에만 save_experience_note 도구를 호출해. '
                   '플러그인이 연결되지 않았다면 저장에 성공한 척하지 말고 Markdown을 제공해.')
        if self.pending_source:
            prompt += f'\n플러그인으로 저장할 경우 원본 파일명 source_capture에는 {self.pending_source.name!r}을 사용해.'
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
        if self.pending_source:
            self.final_source=self.pending_source
            self.pending_source=None
            self.source_explicit=True
            self.refresh_capture_choices()
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
        title=self.title_var.get().strip()
        if not title:
            messagebox.showinfo('경험 제목 필요','완성노트의 경험 제목을 입력해 주세요.',parent=self.win)
            return
        source=next((capture for capture in self.app.store.capture_sources() if capture.path==self.final_source),None)
        if self.final_source is not None and source is None:
            messagebox.showwarning('원본 기록 확인','선택한 원본이 없어졌어요. 해당 경험에서 다시 선택해 주세요.',parent=self.win)
            self.refresh_capture_choices()
            return
        caption=f'\n경험 제목: {title}'
        if not messagebox.askyesno('경험 노트 확정','수치와 사실을 확인했어?\n확정한 내용으로 새 노트를 저장할게.'+caption,parent=self.win):
            return
        try:
            project=source.project if source else self.project_var.get()
            path=self.app.store.save_experience(title,body,project,source.path if source else None,
                                                infer_title=False)
        except Exception as exc:
            messagebox.showerror('저장 실패',str(exc),parent=self.win)
        else:
            self.status.set(f'✓ 새 경험 노트 저장: {path.name}')
            self.library_project.set('전체 프로젝트')
            self.archive_query.set('')
            self.new_archive_path=path
            self.select_view('archive')
            if messagebox.askyesno('저장 완료',f'Obsidian에 저장했어!\n{path.name}\n\n노트를 열어 볼까?',parent=self.win):
                self.open_obsidian(path)

    def hide(self):
        self.flush()
        self.win.withdraw()

    def show(self):
        self.win.deiconify()
        self.win.lift()
        self.win.focus_force()
