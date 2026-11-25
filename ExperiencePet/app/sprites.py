"""Image sprites for Experience Pet. Explicit frames instead of image rotation."""
from pathlib import Path
from PIL import Image

NAMES = [
    'walk_1','walk_2','walk_3','walk_4',
    'crawl','idle','sit','sleep',
    'crouch','jump','land','perch',
    'speech','hop','run_with_dog','idle_with_dog',
]

NAMES += ['stride_a', 'stride_b', 'sprint', 'dizzy', 'tumble', 'cry']

NAMES += ['cling_0','cling_1']
STATE_FRAMES = {
    'cling': ('cling_0','cling_1'),
    'idle': ('idle','idle_with_dog','idle'),
    'walk': ('stride_a','stride_b'),
    'crawl': ('crawl',),
    'held': ('jump',),
    'dizzy': ('dizzy',),
    'flight': ('tumble',),
    'fallen': ('tumble',),
    'cry': ('cry',),
    'rest': ('sit',),
    'sleep': ('sleep',),
    'jump': ('crouch','jump','jump','land'),
    'jump_perch': ('crouch','jump','jump','perch'),
    'perch': ('perch',),
    'hang': ('perch',),
    'drop': ('perch','jump','land'),
    'run_dog': ('sprint','stride_b'),
    'speech': ('speech',),
}


def animation_frame(state: str, elapsed: float, progress: float = 0.0) -> str:
    frames = STATE_FRAMES.get(state, STATE_FRAMES['idle'])
    if len(frames) == 1:
        return frames[0]
    if state in ('jump','jump_perch','drop'):
        return frames[min(len(frames)-1, int(max(0,min(0.999,progress))*len(frames)))]
    if state == 'idle':
        return frames[int(max(0,elapsed)//4) % len(frames)]
    fps = 7.5 if state == 'run_dog' else 5.7 if state == 'walk' else 3.5
    return frames[int(max(0,elapsed)*fps) % len(frames)]


class SpriteAtlas:
    def __init__(self, root: Path):
        self.root=Path(root)
        self.sprites={}
        for name in NAMES:
            path=self.root / f'{name}.png'
            if not path.exists():
                raise FileNotFoundError(f'누락된 모션 이미지: {path}')
            self.sprites[name] = Image.open(path).convert('RGBA')
        self.cache={}

    def get(self, name: str, size: int, face: int = 1):
        key=(name,int(size),-1 if face < 0 else 1)
        if key not in self.cache:
            img=self.sprites[name]
            # Preserve the source's original aspect ratio. All sprites share a square cell.
            resized=img.resize((size,size),Image.Resampling.LANCZOS)
            if face < 0:
                resized=resized.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
            self.cache[key]=resized
        return self.cache[key]

    def clear_cache(self):
        self.cache.clear()
