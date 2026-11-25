import unittest
from pathlib import Path
from PIL import Image
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
from sprites import SpriteAtlas,STATE_FRAMES,animation_frame
from win_alpha import rgba_to_premultiplied_bgra
from motion import PetMotion

ASSETS=Path(__file__).resolve().parents[1]/'app'/'assets'

class TestSprites(unittest.TestCase):
    def test_all_states_have_valid_frames(self):
        atlas=SpriteAtlas(ASSETS/'sprites')
        for state in STATE_FRAMES:
            frame=animation_frame(state,elapsed=2,progress=.5)
            self.assertIn(frame,atlas.sprites)
            rgba=atlas.get(frame,156,-1)
            self.assertEqual(rgba.size,(156,156))
            self.assertEqual(rgba.mode,'RGBA')

    def test_transparent_sprite_corners(self):
        atlas=SpriteAtlas(ASSETS/'sprites')
        for name,img in atlas.sprites.items():
            self.assertEqual(img.getpixel((0,0))[3],0,name)

    def test_premultiplied_alpha_hides_rgb_in_fully_transparent_pixels(self):
        image=Image.new('RGBA',(2,1))
        image.putpixel((0,0),(0,255,0,0))
        image.putpixel((1,0),(255,0,0,128))
        self.assertEqual(rgba_to_premultiplied_bgra(image),bytes([0,0,0,0,0,0,128,128]))

    def test_window_edge_hang_then_drop(self):
        pet=PetMotion(w=1920,h=1080,size=156,seed=8)
        pet.force('hang',now=0,window_rect=(100,80,1400,900))
        self.assertEqual(pet.state,'jump_perch')
        pet.tick(2,window_rect=(100,80,1400,900))
        self.assertEqual(pet.state,'hang')
        pet.tick(30,window_rect=(100,80,1400,900))
        self.assertEqual(pet.state,'drop')

if __name__=='__main__':unittest.main()
