"""Install local MCP plugin and register a personal marketplace, without overwriting other plugins."""
from pathlib import Path
import json,shutil,subprocess,sys

HERE=Path(__file__).resolve().parent
SOURCE=HERE.parent/'plugins'/'experience-pet'
TARGET=Path.home()/'.codex'/'plugins'/'experience-pet'
MARKET=Path.home()/'.agents'/'plugins'/'marketplace.json'


def install():
    if not SOURCE.exists():
        raise RuntimeError('압축 해제한 패키지의 plugins/experience-pet 폴더가 필요합니다.')
    TARGET.parent.mkdir(parents=True,exist_ok=True)
    shutil.copytree(SOURCE,TARGET,dirs_exist_ok=True,ignore=shutil.ignore_patterns('.venv','__pycache__'))
    py=TARGET/'.venv'/'Scripts'/'python.exe'
    if not py.exists():
        subprocess.run([sys.executable,'-m','venv',str(TARGET/'.venv')],check=True)
    subprocess.run([str(py),'-m','pip','install','-r',str(TARGET/'requirements.txt')],check=True)
    MARKET.parent.mkdir(parents=True,exist_ok=True)
    if MARKET.exists():
        old=MARKET.read_text(encoding='utf-8')
        data=json.loads(old)
        if not isinstance(data,dict) or not isinstance(data.get('plugins',[]),list):
            raise RuntimeError('기존 개인 마켓플레이스 파일 구조를 파악하지 못했어요. 파일을 수정하지 않습니다.')
        MARKET.with_suffix('.json.backup').write_text(old,encoding='utf-8')
    else:
        data={'name':'my-local-plugins','interface':{'displayName':'My Local Plugins'},'plugins':[]}
    entry={'name':'experience-pet','source':{'source':'local','path':'./.codex/plugins/experience-pet'},
           'policy':{'installation':'AVAILABLE','authentication':'ON_INSTALL'},'category':'Productivity'}
    data['plugins']=[e for e in data['plugins'] if e.get('name')!='experience-pet']+[entry]
    MARKET.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    print('플러그인 설치됨:',TARGET)
    print('마켓플레이스 등록됨:',MARKET)
    print('ChatGPT Windows 앱을 완전히 재시작하고 Plugins > My Local Plugins에서 Experience Pet을 설치하세요.')
    print('자동 설치 및 ChatGPT 응답 읽기는 제공되지 않습니다. 플러그인을 설치해야 도구 호출이 활성화됩니다.')

if __name__=='__main__':
    try:install()
    except Exception as e:
        print('설치 실패:',e)
        raise SystemExit(1)
