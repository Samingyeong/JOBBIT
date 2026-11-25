"""One Markdown outline for interview prompts, imports and saved notes."""
import re
from pathlib import Path
from urllib.parse import quote

SECTIONS = {
    '상황과 문제': ('상황','문제 정의','맥락','원래 목표와 제약','관찰과 원인 확인','원래 문제','사용자와 업무의 원래 흐름','관찰한 현상과 진짜 문제'),
    '선택과 판단': ('시도와 대안','선택 근거','판단','선택지 비교','첫 가설과 반례','선택지와 판단'),
    '실행': ('구체적 실행','수정한 설계','실행과 변화','실행 타임라인 (시도와 실패 포함)'),
    '검증과 결과': ('결과','실행·결과','확인된 결과와 남은 질문','검증과 성과'),
    '배운 점': ('깨달음과 변화','배움','임시 배움','깨달음과 다음 행동'),
    '활용 역량': ('자소서 활용 역량','자소서 질문'),
    '근거와 미확인 사항': ('미확인 사항','추가 증거 필요','기록할 것','증거 확보','추가로 기록할 인터뷰 질문','근거 링크'),
}
ALIASES = {alias:key for key,names in SECTIONS.items() for alias in (key,*names)}

def split_note(text):
    match = re.match(r'\A---\r?\n(.*?)\r?\n---(?:\r?\n|$)', text, re.S)
    return (match[1],text[match.end():].strip()) if match else ('',text.strip())

def normalize(text):
    text=text.strip()
    fence=re.fullmatch(r'~~~(?:markdown|md)?\s*\n(.*?)\n~~~|\x60{3}(?:markdown|md)?[ \t]*\n(.*?)\n\x60{3}',text,re.S|re.I)
    if fence:
        text=next(g for g in fence.groups() if g is not None)
    meta,body=split_note(text)
    title=''
    lines=body.splitlines()
    if lines and lines[0].startswith('# '):
        title=lines.pop(0)[2:].strip()
    parts={k:[] for k in SECTIONS}
    group=next(iter(parts))
    fenced=False
    for line in lines:
        if line.lstrip().startswith(('\x60\x60\x60','~~~')):
            fenced=not fenced
        key=re.sub(r'^\d+[.)]\s*','',re.sub(r'^#{1,6}\s+','',line.strip()).strip('*').rstrip(':')).strip()
        if not fenced and key in ALIASES:
            group=ALIASES[key]
            parts[group].append('')
        elif not fenced and re.match(r'^> 원본:[ \t]*\[\[03 Daily Logs/',line):
            continue
        elif not fenced and line.startswith('> 원본:'):
            parts['근거와 미확인 사항'].append(line)
        else:
            if line.startswith('## ') and not fenced:
                line='#'+line
            parts[group].append(line)
    formatted=[]
    for k,values in parts.items():
        content='\n'.join(values).strip()
        if content=='미확인':
            content=''
        formatted.append('## '+k+'\n\n'+(content or '미확인'))
    return title,'\n\n'.join(formatted)

def obsidian_uri(path):
    return 'obsidian://open?path='+quote(str(Path(path).resolve()),safe='')

def history(root):
    roots=[root]
    if root.name=='Career_Experience_Vault' and (root.parent/'.obsidian').is_dir():
        roots.append(root.parent)
    for base in roots:
        for path in sorted((base/'02 Experiences').glob('*.md'),reverse=True):
            meta,body=split_note(path.read_text(encoding='utf-8-sig'))
            prop=re.search(r'^project:\s*([^\n]*)',meta,re.M)
            project=prop[1].strip().strip('"\'').removeprefix('[[').removesuffix(']]') if prop else ''
            title=re.search(r'^# (.+)',body,re.M)
            yield project,title[1] if title else path.stem,path,body
