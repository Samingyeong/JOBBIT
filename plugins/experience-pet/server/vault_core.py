"""Safe local-first Obsidian vault handling.
Only writes inside a user-selected Vault, never modifies non-owned notes.
"""
from __future__ import annotations
from experience_format import normalize, split_note, SECTIONS
from datetime import datetime
from pathlib import Path, PurePosixPath, PureWindowsPath
import json
import os
import re
import threading
import uuid

DEFAULT_NAME = 'Career_Experience_Vault'
APP_DATA = Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'ExperiencePet'
SETTINGS = APP_DATA / 'settings.json'

DEFAULTS = {
    'vault_path': '', 'roam': True, 'always_on_top': True,
    'startup': True, 'size': 156, 'speed': 3, 'speech': True,
    'hide_fullscreen': True, 'use_mcp': False,
    'mcp_url': 'http://127.0.0.1:27123/mcp/',
}


def load_settings() -> dict:
    result = dict(DEFAULTS)
    try:
        obj = json.loads(SETTINGS.read_text(encoding='utf-8'))
        if isinstance(obj, dict):
            result.update({k: v for k, v in obj.items() if k in result})
    except (FileNotFoundError, OSError, ValueError):
        pass
    return result


def store_settings(settings: dict) -> None:
    APP_DATA.mkdir(parents=True, exist_ok=True)
    tmp = SETTINGS.with_suffix('.tmp')
    tmp.write_text(json.dumps({k:settings.get(k,v) for k,v in DEFAULTS.items()},ensure_ascii=False, indent=2), encoding='utf-8')
    os.replace(tmp, SETTINGS)


def yaml_value(value):
    return json.dumps(str(value or ''), ensure_ascii=False)


def safe_rel(rel: str) -> Path:
    """Return a vault-relative path, rejecting Windows *and* POSIX roots.

    Windows Path('/tmp/secret.txt').is_absolute() is False, even though
    that path is rooted and escapes a drive-relative directory.  Validate
    both syntaxes regardless of which OS is running the tests/app.
    """
    if not isinstance(rel, str) or not rel:
        raise ValueError('Vault 안의 상대 경로만 사용 가능합니다.')
    posix = PurePosixPath(rel)
    windows = PureWindowsPath(rel)
    components = rel.split('/')
    if (
        posix.root or windows.root or windows.drive
        or '\\' in rel or ':' in rel
        or any(segment in ('', '.', '..') for segment in components)
        or any(ord(ch) < 32 for ch in rel)
    ):
        raise ValueError('Vault 안의 안전한 상대 경로만 사용 가능합니다.')
    return Path(rel)


def title_slug(name: str):
    s = re.sub(r'[^\w가-힣\- ]+', '', name, flags=re.UNICODE).strip().replace(' ','-')
    return s[:55] or '새로운-경험'


def readable_title(value):
    line = next((line.strip() for line in value.splitlines() if line.strip()), '새 기록')
    line = re.sub(r'^#+\\s*|^경험 노트\\s*[｜|:：]\\s*', '', line)
    line = re.sub(r'[<>:"/\\\\|?*#\\[\\]\\^\\x00-\\x1f]', ' ', line)
    line = ' '.join(line.split())[:48].rstrip(' .') or '새 기록'
    return line + ' 기록' if PureWindowsPath(line).is_reserved() else line

class VaultStore:
    def __init__(self, vault: str):
        path = Path(vault).expanduser().resolve()
        if not path.exists() or not path.is_dir():
            raise ValueError('옵시디언 Vault 폴더를 설정해 주세요.')
        nested = path / DEFAULT_NAME
        self.root = nested if (nested / "01 Projects").is_dir() else path
        self.lock = threading.RLock()
        self.sessions = {}  # session -> ONLY the file the app owns

    def _owned_path(self, rel: str) -> Path:
        p = (self.root / safe_rel(rel)).resolve()
        if not p.is_relative_to(self.root):
            raise ValueError('Vault 외부 경로는 사용할 수 없습니다.')
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    def project_names(self):
        folder = self.root / '01 Projects'
        return sorted((p.stem for p in folder.glob('*.md') if p.is_file()), key=str.casefold)

    def add_project(self, name):
        name = name.strip()
        if (not name or len(name) > 120 or name.endswith('.') or
                PureWindowsPath(name).is_reserved() or
                any(c in '<>:"/\\\\|?*#[]^' or ord(c) < 32 for c in name)):
            raise ValueError('프로젝트 이름을 확인해 주세요.')
        existing = next((p for p in self.project_names() if p.casefold() == name.casefold()), None)
        if existing:
            return existing
        path = self._owned_path(f'01 Projects/{name}.md')
        try:
            with path.open('x', encoding='utf-8') as f:
                f.write(f'---\ntype: project\n---\n# {name}\n\n## 연결 경험\n')
        except FileExistsError:
            pass
        return path.stem

    def new_session(self):
        session = uuid.uuid4().hex[:10]
        self.sessions[session] = None
        return session

    def reserve_note(self, folder, title):
        stem = readable_title(title)
        number = 1
        while True:
            name = stem if number == 1 else f'{stem} ({number})'
            path = self._owned_path(f'{folder}/{name}.md')
            try:
                path.touch(exist_ok=False)
                return path
            except FileExistsError:
                number += 1

    def raw_content(self, text: str, project: str, session: str):
        now = datetime.now()
        return ('---\n'
                'type: daily_capture\n'
                f'created: {now.isoformat(timespec="seconds")}\n'
                f'project: {yaml_value(project)}\n'
                'status: inbox\n'
                'tags: [career, experience-log]\n'
                '---\n\n'
                f'# {readable_title(text)}\n\n'
                f'> Experience Pet 자동 기록 · 세션 {session}\n\n'
                '## 원본 메모\n\n'
                f'{text.strip()}\n\n'
                '## 후속 정리\n\n'
                '- [ ] ChatGPT와 3~5개 핵심 질문으로 경험 정리\n'
                '- [ ] 근거·수치·피드백 확인\n'
                '- [ ] 완성된 경험 노트 검토 후 저장\n')

    def autosave(self, session: str, text: str, project: str = ''):
        if not text.strip():
            return None
        if session not in self.sessions:
            raise ValueError('존재하지 않는 세션입니다.')
        with self.lock:
            if not self.sessions[session]:
                reserved = self.reserve_note('03 Daily Logs', text)
                self.sessions[session] = reserved.relative_to(self.root).as_posix()
            path = self._owned_path(self.sessions[session])
            contents = self.raw_content(text, project, session)
            tmp = path.with_name(path.name+'.tmp')
            tmp.write_text(contents, encoding='utf-8')
            os.replace(tmp, path)  # atomic update of app-owned daily capture only
            return path

    def save_experience(self, title: str, body: str, project: str, source: str | None = None):
        if body.strip():
            parsed_title, body = normalize(body)
            if parsed_title and title.strip() in ('','오늘의 경험'):
                title=parsed_title
        if not title.strip() or not body.strip():
            raise ValueError('제목과 경험 본문을 입력해 주세요.')
        project = self.add_project(project) if project.strip() else ''
        project_link = f'[[{project}]]' if project else ''
        header = ['---', 'type: experience',
                  f'created: {datetime.now().isoformat(timespec="seconds")}',
                  f'project: {yaml_value(project_link)}',
                  'status: reviewed', 'competencies: []', 'role: ""', 'evidence: 확인필요',
                  'tags: [career, experience]']
        if source:
            source_p=Path(source).resolve()
            if source_p.parent==self.root/'03 Daily Logs':
                try:
                    meta,_=split_note(source_p.read_text(encoding='utf-8-sig'))
                    stamp=re.search(r'^created:[ \t]*["\x27]?(\d{4}-\d\d-\d\d)',meta,re.M)
                    if stamp:
                        header.append(f'capture_date: {datetime.fromisoformat(stamp[1]).date().isoformat()}')
                except (OSError,ValueError):
                    pass
        header.extend(['---','',f'# {title.strip()}',''])
        header.extend([body.strip(), '', '> 작성 후 확인: 성과 수치와 개인 역할이 실제 자료와 일치하는지 검증하세요.', ''])
        with self.lock:
            dest = self.reserve_note('02 Experiences', title)
            with dest.open('w', encoding='utf-8') as f:
                f.write('\n'.join(header))
            if project:
                project_file = self._owned_path(f'01 Projects/{project}.md')
                content = project_file.read_text(encoding='utf-8-sig')
                heading = re.search(r'^## 연결 경험[ \t]*$', content, re.M)
                link = f'- [[02 Experiences/{dest.stem}|{title.strip()}]]'
                if heading:
                    content = content[:heading.end()] + '\n' + link + content[heading.end():]
                else:
                    content = content.rstrip() + '\n\n## 연결 경험\n' + link + '\n'
                temp = project_file.with_name(project_file.name + '.' + uuid.uuid4().hex + '.tmp')
                try:
                    temp.write_text(content, encoding='utf-8')
                    os.replace(temp, project_file)
                except OSError:
                    dest.unlink(missing_ok=True)
                    raise
                finally:
                    temp.unlink(missing_ok=True)
        return dest

    def related_notes(self, subject: str, limit: int = 4):
        """Search ONLY project and experience notes. Tiny, local, no network index."""
        tokens = set(re.findall(r'[\w가-힣]{2,}', subject.lower()))
        docs = []
        for folder in ('01 Projects', '02 Experiences'):
            p = self.root/folder
            if not p.exists():
                continue
            for file in p.glob('*.md'):
                try:
                    content = file.read_text(encoding='utf-8')[:3500]
                except OSError:
                    continue
                hay = f'{file.stem} {content}'.lower()
                score = sum(3 if tok in file.stem.lower() else 1 for tok in tokens if tok in hay)
                if score:
                    # Don't include raw YAML or huge pages in copy/paste prompt
                    snippet = re.sub(r'\A---\n.*?\n---\n', '', content, flags=re.S).strip()[:1050]
                    docs.append((score, file.stem, snippet))
        docs.sort(key=lambda x:(-x[0],x[1]))
        return docs[:limit]


def make_gpt_prompt(text: str, project: str, related):
    refs = '\n\n'.join(f'### {name}\n{content}' for _,name,content in related)
    return f'''너는 나의 자소서 경험 기록 인터뷰어야. 이 대화에서는 자소서를 바로 쓰지 말고, 내 경험을 검증 가능한 원자료로 정리해 줘.

본인의 실제 한 사건을 대상으로 질문한다. 다른 사람의 합격 사례와 그 수치는 작성 방식 참고 자료이며 본인의 경험에서 제외한다. 원래 사용자 행동, 직접 관찰한 문제, 내가 제안한 결정과 버린 대안, 팀원·AI와 구분되는 본인 기여를 확인한다. 제품 개선이면 도입 뒤 사용 흐름이 어떻게 바뀌었는지, AI 서비스면 코드·모델·사람의 역할과 오판을 발견한 사례를, 에이전트 협업이면 실패를 발견한 검증 장치와 실제 수정한 규칙을 묻는다. 수치는 기간·분모·출처가 있는지, 결과가 팀 성과인지 본인 성과인지 확인한다. 빠진 것 중 결론을 가장 크게 바꿀 질문 하나만 한다. 정리할 때는 일기 원문·관련 노트에서 확인한 사실과 추가 확인 사항을 구분하고, 첫 문장에 행동과 확인된 변화를 쓴다.

규칙:
1. 첫 답변은 핵심 꼬리질문 1개만 해. 최대 3~5개 질문으로 상황/진짜 문제/선택지와 기각 이유/실행/검증/결과/깨달음을 확인해.
2. 내가 답한 것과 과거 메모에 나온 사실만 사용해. 수치·성과·기술·직책을 만들어내지 말고, 모르는 항목은 '미확인'으로 남겨.
3. 내 판단이 수정된 순간, 실패한 접근법, 사용자의 피드백, 반례, 정량 근거를 우선 질문해.
4. 충분한 정보가 모이면 '경험 노트로 정리할까?'라고 물어. 내가 동의하면 아래 형식으로 Markdown 결과를 작성해.
5. 최종본만 복사할 수 있게 하나의 markdown 코드 블록으로 제공해. 첫 줄은 # 경험 제목, 그 아래에는 {", ".join("## "+heading for heading in SECTIONS)} 제목을 이 순서로 써. 각 제목 아래에는 빈 줄을 두고 문단이나 목록을 작성해. YAML 속성은 기록장이 붙여. 없는 근거는 미확인으로 써.\n동아리나 팀 활동이면 내가 관찰한 점과 다음 활동에 적용할 인사이트를 한 번 물어봐.\n6. 결과가 확정되지 않은 업무라면 진행 중임을 명시해.

프로젝트: {project or '(미정)'}

오늘의 원본 기록:
{text.strip()}

관련 경험·프로젝트의 참고 노트 (틀릴 수 있으므로 사용자 답변 우선):
{refs or '(없음)'}

지금부터 질문을 하나씩 시작해 줘.'''
