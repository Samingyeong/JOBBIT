import pathlib,sys,unittest
from urllib.parse import parse_qs,urlparse
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'app'))
from chatgpt_desktop import make_deeplink
class TestDeeplink(unittest.TestCase):
    def test_prompt_and_path(self):
        url=make_deeplink('오늘 협업 문제는?','C:/Career Vault')
        self.assertTrue(url.startswith('codex://new?'))
        params=parse_qs(urlparse(url).query)
        self.assertEqual(params['prompt'],['오늘 협업 문제는?'])
        self.assertEqual(params['path'],['C:/Career Vault'])
if __name__=='__main__':unittest.main()
