import tempfile,unittest,pathlib,sys
from unittest.mock import patch
HERE=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import bridge_core

class TestBridge(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=pathlib.Path(self.tmp.name)
        for f in ('01 Projects','02 Experiences','03 Daily Logs'):(self.root/f).mkdir(parents=True)
        self.patch=patch('bridge_core.get_store',return_value=bridge_core.VaultStore(str(self.root)))
        self.patch.start()
    def tearDown(self):
        self.patch.stop();self.tmp.cleanup()
    def test_scope_rejects_other_file(self):
        p=self.root/'03 Daily Logs'/'secret.md'
        p.write_text('secret',encoding='utf-8')
        with self.assertRaises(ValueError):bridge_core.read_capture('secret.md')
        with self.assertRaises(ValueError):bridge_core.read_capture('../secret.md')
    def test_vault_core_rejects_rooted_paths_on_windows(self):
        from vault_core import safe_rel
        for path in ('/tmp/secret.txt', 'C:relative/file.md', '../secret.md', '//server/share/file.md'):
            with self.subTest(path=path):
                with self.assertRaises(ValueError):
                    safe_rel(path)

    def test_capture_and_save(self):
        store=bridge_core.get_store()
        p=store.autosave(store.new_session(),'나는 협업 개선을 했다','프로젝트')
        self.assertEqual(bridge_core.read_capture(p.name)['file'],p.name)
        result=bridge_core.save_note('개선 경험','## 문제\n테스트','프로젝트',p.name)
        self.assertTrue(result['saved'])
        self.assertTrue(pathlib.Path(result['path']).exists())
    def test_search_only_career(self):
        (self.root/'01 Projects'/'A.md').write_text('협업',encoding='utf-8')
        (self.root/'03 Daily Logs'/'A.md').write_text('협업',encoding='utf-8')
        self.assertEqual(len(bridge_core.related('협업')),1)

if __name__=='__main__': unittest.main()
