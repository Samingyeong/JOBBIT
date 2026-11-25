"""Scrollable notebook rows with wrapping and artwork on the same canvas."""
import tkinter as tk


def rounded(canvas,x1,y1,x2,y2,r,fill,outline=''):
    return canvas.create_polygon(x1+r,y1,x2-r,y1,x2,y1,x2,y1+r,x2,y2-r,x2,y2,
                                 x2-r,y2,x1+r,y2,x1,y2,x1,y2-r,x1,y1+r,x1,y1,
                                 smooth=True,splinesteps=12,fill=fill,outline=outline)


class NoteRows(tk.Canvas):
    def __init__(self,parent,font,*,height=150,on_select=None,on_open=None,art=None):
        super().__init__(parent,bg='#fffdf5',height=height,highlightthickness=0,takefocus=True)
        self.font,self.on_select,self.on_open=font,on_select,on_open
        self.art=art
        self.labels=[]
        self.bounds=[]
        self.selected=None
        self.placeholder=''
        self.bind('<Configure>',self.draw)
        self.bind('<MouseWheel>',self.scroll)
        self.bind('<Button-1>',self.click)
        self.bind('<Double-Button-1>',self.open)
        self.bind('<Return>',self.open)
        for key,delta in (('<Up>',-1),('<Down>',1)):
            self.bind(key,lambda _,step=delta:self.step(step))

    def set_rows(self,labels,*,selected=0,placeholder=''):
        self.labels=labels
        self.selected=selected if labels else None
        self.placeholder=placeholder
        self.draw()
        self.reveal()

    def draw(self,event=None):
        width,height=self.winfo_width(),self.winfo_height()
        if width<=2 or height<=2:
            return
        self.delete('all')
        self.bounds=[]
        art=self.art if self.art and height>=self.art.height()+7 else None
        gutter=art.width()+5 if art else 0
        right=width-4
        text_width=max(30,right-gutter-20)
        top=5
        for index,label in enumerate(self.labels):
            text=self.create_text(13,top+5,text=label,width=text_width,anchor='nw',font=self.font,fill='#20201e')
            bottom=max(top+27,self.bbox(text)[3]+6)
            if index==self.selected or index%2:
                fill='#f8cc78' if index==self.selected else '#fffaeb'
                row=self.create_rectangle(4,top,right-2,bottom,outline='',fill=fill)
                self.tag_lower(row,text)
            self.bounds.append((top,bottom))
            top=bottom
        if not self.labels and self.placeholder:
            self.create_text(13,12,text=self.placeholder,width=text_width,anchor='nw',font=self.font,fill='#806d62')
        total=max(height,top+5)
        rounded(self,2,2,right,total-2,8,'#fff5dc','#ae926d')
        self.tag_lower(self.find_all()[-1])
        if art:
            self.create_image(width-3,art.height()+4,image=art,anchor='se')
        self.configure(scrollregion=(0,0,width,total),yscrollincrement=14)

    def scroll(self,event):
        self.yview_scroll(-2 if event.delta>0 else 2,'units')
        return 'break'

    def reveal(self):
        self.yview_moveto(0)
        if self.selected is not None and self.selected<len(self.bounds):
            _,bottom=self.bounds[self.selected]
            if bottom>self.winfo_height():
                self.yview_moveto((bottom-self.winfo_height()+15)/max(bottom,self.bounds[-1][1]))

    def choose(self,index):
        self.selected=index
        self.draw()
        if self.on_select:
            self.on_select()

    def click(self,event):
        self.focus_set()
        y=self.canvasy(event.y)
        for index,(top,bottom) in enumerate(self.bounds):
            if top<=y<bottom:
                self.choose(index)
                break

    def step(self,delta):
        if self.labels:
            self.choose(max(0,min(len(self.labels)-1,(self.selected or 0)+delta)))
            self.reveal()
        return 'break'

    def open(self,event=None):
        if self.selected is not None and self.on_open:
            self.on_open()
        return 'break'
