import pathlib
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'app'))
from vault import VaultStore,make_gpt_prompt,safe_rel
from motion import PetMotion
from mcp_bridge import valid_endpoint

class TestVault(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=pathlib.Path(self.tmp.name)
        (self.root/'01 Projects').mkdir()
        (self.root/'02 Experiences').mkdir()
        self.store=VaultStore(self.tmp.name)
    def tearDown(self):self.tmp.cleanup()
    def test_autosave_same_session_only(self):
        s=self.store.new_session()
        a=self.store.autosave(s,'오늘 첫 메모','키오스크')
        b=self.store.autosave(s,'내용 수정','키오스크')
        self.assertEqual(a,b)
        self.assertEqual(len(list((self.root/'03 Daily Logs').glob('*.md'))),1)
        self.assertIn('내용 수정',a.read_text(encoding='utf-8'))
        self.assertNotIn('오늘 첫 메모',a.read_text(encoding='utf-8'))
    def test_new_session_creates_unique_file(self):
        a=self.store.autosave(self.store.new_session(),'하나','DED')
        b=self.store.autosave(self.store.new_session(),'둘','DED')
        self.assertNotEqual(a,b)
        self.assertTrue(a.exists() and b.exists())

    def test_autosave_recovers_deleted_capture(self):
        session=self.store.new_session()
        original=self.store.autosave(session,'기존 메모')
        original.unlink()
        recovered=self.store.autosave(session,'복구할 메모')
        self.assertIn('복구할 메모',recovered.read_text(encoding='utf-8'))
        self.assertEqual(recovered,self.store.autosave(session,'이어서 저장할 메모'))

    def test_autosave_follows_renamed_capture_without_overwriting_other_note(self):
        session=self.store.new_session()
        original=self.store.autosave(session,'기존 메모')
        renamed=original.rename(original.with_name('이름을 바꾼 메모.md'))
        original.write_text('별도로 만든 노트',encoding='utf-8')
        saved=self.store.autosave(session,'이어서 쓴 메모')
        self.assertEqual(saved,renamed)
        self.assertIn('이어서 쓴 메모',renamed.read_text(encoding='utf-8'))
        self.assertEqual(original.read_text(encoding='utf-8'),'별도로 만든 노트')

    def test_experience_save_never_overwrites(self):
        a=self.store.save_experience('충돌 예방','## 결과\n충돌 0','키오스크')
        b=self.store.save_experience('충돌 예방','## 결과\n충돌 0','키오스크')
        self.assertNotEqual(a,b)
        self.assertIn('status: reviewed',a.read_text(encoding='utf-8'))
    def test_restricts_paths(self):
        for name in ('../secrets.txt','/tmp/secret.txt','C:\\evil.txt'):
            with self.assertRaises(ValueError):safe_rel(name)
    def test_restricts_windows_rooted_and_ambiguous_paths(self):
        # A forward-slash rooted path is NOT considered absolute by
        # pathlib.Path.is_absolute() on Windows without a drive letter.
        # These assertions must pass identically on Windows/Linux.
        forbidden = (
            '/tmp/secret.txt', '/Windows/System32/secret.txt',
            r'C:\\secret.txt', 'C:relative\\secret.txt',
            '//server/share/secret.txt', r'\\server\\share\\secret.txt',
            'a/../../secret.txt', './local.md', 'a/./local.md',
            'a//local.md', r'\\Windows\\System32',
        )
        for name in forbidden:
            with self.subTest(name=name):
                with self.assertRaises(ValueError):
                    safe_rel(name)
        self.assertEqual(str(safe_rel('02 Experiences/정리.md')),
                         str(pathlib.Path('02 Experiences') / '정리.md'))

    def test_context_is_scoped_to_projects_experiences(self):
        (self.root/'01 Projects'/'DED.md').write_text('# DED CNC 좌표 문제',encoding='utf-8')
        (self.root/'02 Experiences'/'CNC.md').write_text('# CNC 32bit DLL',encoding='utf-8')
        (self.root/'04 Applications').mkdir()
        (self.root/'04 Applications'/'CNC.md').write_text('이것은 검색 결과에 없어야 함',encoding='utf-8')
        docs=self.store.related_notes('CNC DED')
        self.assertEqual(len(docs),2)
        self.assertTrue(all('이것은 검색 결과에 없어야 함' not in x[2] for x in docs))
    def test_prompt_does_not_invent_results(self):
        p=make_gpt_prompt('문제 해결 진행 중','DED',[])
        self.assertIn('미확인',p)
        self.assertIn('질문을 하나씩',p)
    def test_mcp_endpoint_safety(self):
        self.assertTrue(valid_endpoint('http://127.0.0.1:27123/mcp/'))
        self.assertFalse(valid_endpoint('https://example.com/mcp/'))
        self.assertFalse(valid_endpoint('file:///etc/passwd'))

    def test_roam_and_jump_states(self):
        m=PetMotion(1920,1080,156,seed=1)
        m.force('crawl',10)
        a=m.tick(10.2)
        self.assertEqual(a['state'],'crawl')
        m.force('jump',15)
        b=m.tick(15.4)
        self.assertEqual(b['state'],'jump')
        self.assertLess(b['y'],m.ground_y)

if __name__=='__main__':unittest.main()
