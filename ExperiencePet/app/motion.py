"""Pure movement planner for a desktop pet with frame-based animations.

The pet roams across the desktop and occasionally jumps toward the top edge of
an external application window. It does not inspect browser DOM, tabs or pages.
"""
from __future__ import annotations
import math
import random
from sprites import animation_frame

BUBBLES=['부리부리~','오늘도 기록하자!','오호라~','흰둥아 가자!','끄적끄적~','헤헤!']
MOVING = ('walk','crawl','run_dog')
JUMPING = ('jump','jump_perch','drop')


class PetMotion:
    def __init__(self, w=1920, h=1080, size=156, speed=3.0, seed=None):
        self.screen_w,self.screen_h,self.size=w,h,size
        self.rng=random.Random(seed)
        self.x=max(8,int(w*.6))
        self.ground_y=max(6,h-size-85)
        self.y=self.ground_y
        self.target_x=self.x
        self.face=1
        self.speed=speed
        self.state='idle'
        self.started=0.0
        self.end=2.5
        self.jump_from=None
        self.jump_to=None
        self.bubble=''
        self.bubble_until=0.0
        self.paused=False

    def resize(self,size):
        self.size=int(size)
        self.ground_y=max(6,self.screen_h-self.size-85)
        self.y=min(self.y,self.ground_y)
        self.x=min(self.x,max(0,self.screen_w-self.size-112))

    def _set(self,state,now,length):
        self.state=state
        self.started=now
        self.end=now+length
        if self.rng.random()<.28 or state=='run_dog':
            self.bubble='흰둥아 가자!' if state=='run_dog' else self.rng.choice(BUBBLES)
            self.bubble_until=now+2.5

    def force(self,state,now,window_rect=None):
        durations={'walk':5,'crawl':4,'jump':1.15,'rest':5,'sleep':8,
                   'run_dog':5,'perch':5,'hang':5,'idle':3,'speech':3}
        if state=='hang' and window_rect is not None:
            self._start_perch(now,window_rect)
            return
        self._set(state,now,durations.get(state,3))
        if state in MOVING:
            self.target_x=self.rng.randint(15,max(16,self.screen_w-self.size-120))
        if state=='jump':
            self.jump_from=(self.x,self.y)
            dest=self.x+self.rng.randint(-170,170)
            self.jump_to=(max(4,min(dest,self.screen_w-self.size-110)),self.ground_y)

    def _start_perch(self,now,window_rect):
        left,top,right,bottom=window_rect
        if right-left<350 or bottom-top<120:
            return False
        # The top border of the foreground application window, not a browser DOM tab.
        tx=min(max(left+min(140,(right-left)//3),5),self.screen_w-self.size-105)
        ty=max(4,min(top - int(self.size*.50) if top>90 else top+6,self.ground_y))
        self.jump_from=(self.x,self.y)
        self.jump_to=(tx,ty)
        self.face=1 if tx>self.x else -1
        self._set('jump_perch',now,1.45)
        return True

    def _next(self,now,window_rect):
        r=self.rng.random()
        if r<.12:
            self._set('sleep',now,self.rng.uniform(4,9))
        elif r<.26:
            self._set('rest',now,self.rng.uniform(2,5))
        elif r<.46:
            self._set('crawl',now,self.rng.uniform(3,7))
            self.target_x=self.rng.randint(15,max(16,self.screen_w-self.size-105))
        elif r<.60:
            self._set('run_dog',now,self.rng.uniform(3,6))
            self.target_x=self.rng.randint(15,max(16,self.screen_w-self.size-105))
        elif r<.74:
            self.jump_from=(self.x,self.y)
            tx=self.x+self.rng.randint(-150,150)
            self.jump_to=(max(4,min(tx,self.screen_w-self.size-110)),self.ground_y)
            self._set('jump',now,1.15)
        elif r<.82:
            self._set('speech',now,self.rng.uniform(1.5,3))
            self.bubble='부리부리~'
            self.bubble_until=now+2.4
        else:
            self._set('walk',now,self.rng.uniform(3,7))
            self.target_x=self.rng.randint(15,max(16,self.screen_w-self.size-105))

    def release(self, now, vx, vy):
        self.vx = max(-1900, min(1900, vx))
        self.vy = max(-1400, min(1400, vy))
        self.face = (1 if vx > 0 else -1) if abs(vx) > 35 else self.face
        self.last_flight = now
        self.hard_hit = False
        self.state = 'flight'
        self.started = now
        self.bubble = ''

    def flight_tick(self, now):
        dt = min(.08, max(0, now - self.last_flight))
        self.last_flight = now
        self.vy += 1650 * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        inset = (306 - self.size) / 2
        left, right = -inset, self.screen_w - self.size - inset
        if self.x < left or self.x > right:
            self.hard_hit |= abs(self.vx) > 420
            self.x = max(left, min(right, self.x))
            self.vx *= -.32
        if self.y < -57:
            self.y = -57
            self.vy = abs(self.vy) * .3
        if self.y >= self.ground_y:
            self.y = self.ground_y
            self.hard_hit |= abs(self.vy) > 500 or abs(self.vx) > 520
            self._set('fallen' if self.hard_hit else 'rest', now, .52)
            self.bubble = ''
        return self.visual(now)

    def tick(self,now,window_rect=None):
        if self.state == 'flight':
            return self.flight_tick(now)
        if self.state in ('fallen', 'cry'):
            if now >= self.end:
                if self.state == 'fallen':
                    self._set('cry', now, 1.1)
                else:
                    self._set('idle', now, 2)
                self.bubble = ''
            return self.visual(now)
        if self.paused:
            return self.visual(now)
        if self.state=='jump_perch' and now>=self.end:
            self.y=float(self.jump_to[1])
            self._set('hang',now,self.rng.uniform(3,6))
        elif self.state in ('hang','perch') and now>=self.end:
            self.jump_from=(self.x,self.y)
            self.jump_to=(self.x,self.ground_y)
            self._set('drop',now,.95)
        elif self.state=='drop' and now>=self.end:
            self.y=self.ground_y
            self._set('crawl',now,self.rng.uniform(3,6))
            self.target_x=self.rng.randint(15,max(16,self.screen_w-self.size-105))
        elif now>=self.end:
            if self.state not in ('hang','perch'):
                self.y=self.ground_y
            self._next(now,window_rect)

        if self.state in MOVING:
            delta=self.target_x-self.x
            if abs(delta)>1:
                self.face=1 if delta>0 else -1
                factor=1.6 if self.state=='run_dog' else .66 if self.state=='crawl' else 1
                self.x+=min(abs(delta),self.speed*factor)*self.face
        elif self.state in JUMPING and self.jump_from and self.jump_to:
            d=max(.01,self.end-self.started)
            p=min(1,max(0,(now-self.started)/d))
            x0,y0=self.jump_from;x1,y1=self.jump_to
            self.x=x0+(x1-x0)*p
            self.y=y0+(y1-y0)*p - (90 if self.state=='jump' else 170)*math.sin(math.pi*p)
        if self.bubble_until<now:self.bubble=''
        self.x=min(max(0,self.x),max(0,self.screen_w-self.size-110))
        self.y=min(max(3,self.y),self.ground_y)
        return self.visual(now)

    def visual(self,now):
        moving=self.state in MOVING
        elapsed=max(0,now-self.started)
        progress=min(1,max(0,elapsed/max(.01,self.end-self.started)))
        bounce= (math.sin(now*14)*2.0 if moving else 0.0)
        return {'x':int(self.x),'y':int(self.y+bounce),
                'frame':animation_frame(self.state,elapsed,progress),
                'state':self.state,'face':self.face,
                'speech':self.bubble,'moving':moving}
