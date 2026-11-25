"""Safe plain-Python functions reused by a local MCP tool process."""
from __future__ import annotations
from pathlib import Path
from vault_core import VaultStore, load_settings


def get_store():
    p = load_settings().get('vault_path', '')
    if not p:
        raise RuntimeError('Experience Pet 앱 설정에서 Career Vault 경로를 먼저 지정해 주세요.')
    return VaultStore(p)


def status():
    store = get_store()
    return {'connected': True, 'vault': str(store.root),
            'allowed': ['01 Projects', '02 Experiences', '03 Daily Logs/Experience Pet 캡처만']}


def _capfile(store: VaultStore, name: str):
    if not name or name != Path(name).name or '/' in name or '\\' in name:
        raise ValueError('원본 일기 파일 이름만 입력할 수 있습니다.')
    if not name.endswith('.md'):
        raise ValueError('Experience Pet이 생성한 경험일기만 읽을 수 있습니다.')
    base=(store.root/'03 Daily Logs').resolve()
    candidate=(base/name).resolve()
    if not candidate.is_relative_to(base) or not candidate.is_file():
        raise ValueError('지정한 경험일기가 존재하지 않습니다.')
    sample=candidate.read_text(encoding='utf-8')
    if 'type: daily_capture' not in sample or 'Experience Pet 자동 기록' not in sample:
        raise ValueError('Experience Pet 소유의 경험일기가 아닙니다.')
    return candidate


def recent_captures(limit: int=5):
    store=get_store()
    folder=store.root/'03 Daily Logs'
    if not folder.exists(): return []
    rows=[]
    for p in sorted(folder.glob('*.md'),key=lambda x:x.stat().st_mtime,reverse=True)[:max(1,min(int(limit),20))*3]:
        try:
            file=_capfile(store,p.name)
            raw=file.read_text(encoding='utf-8')
            rows.append({'file':file.name,'excerpt':raw.split('## 원본 메모')[-1].split('## 후속 정리')[0].strip()[:500]})
        except (ValueError,OSError,UnicodeError): continue
        if len(rows)>=max(1,min(int(limit),20)): break
    return rows


def read_capture(name: str):
    store=get_store()
    p=_capfile(store,name)
    return {'file':p.name,'content':p.read_text(encoding='utf-8')[:24000]}


def related(query: str,limit:int=4):
    store=get_store()
    return [{'title':title,'excerpt':excerpt} for _,title,excerpt in store.related_notes(query,limit=max(1,min(int(limit),8)))]


def save_note(title: str,body: str,project: str='',source_capture: str=''):
    store=get_store()
    if len(body)>50000: raise ValueError('노트가 너무 깁니다.')
    source_path=str(_capfile(store,source_capture)) if source_capture else None
    p=store.save_experience(title=title,body=body,project=project,source=source_path)
    return {'saved':True,'path':str(p),'note':p.name}
