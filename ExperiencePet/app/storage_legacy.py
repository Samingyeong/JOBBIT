"""Storage layer for the desktop pet. Standard library except optional mcp SDK."""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
import re
import uuid
from urllib.parse import urlparse
from datetime import datetime
from dataclasses import dataclass

APP_DIR = Path.home() / '.experience-pet'
SETTINGS_PATH = APP_DIR / 'settings.json'
PENDING_DIR = APP_DIR / 'pending'


@dataclass
class Capture:
    kind: str
    project: str
    text: str
    situation: str = ''
    problem: str = ''
    judgment: str = ''
    action: str = ''
    verification: str = ''
    insight: str = ''


def default_config():
    return {
        'mode': 'local',  # local | mcp
        'vault_path': '',
        'mcp_url': 'http://127.0.0.1:27123/mcp/',
        'mcp_api_key': '',
        'roam': True,
    }


def load_config():
    cfg = default_config()
    try:
        data = json.loads(SETTINGS_PATH.read_text(encoding='utf-8'))
        for name in cfg:
            if name in data:
                cfg[name] = data[name]
    except (FileNotFoundError, OSError, ValueError):
        pass
    return cfg


def save_config(config):
    APP_DIR.mkdir(parents=True, exist_ok=True)
    tmp = SETTINGS_PATH.with_suffix('.tmp')
    tmp.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding='utf-8')
    os.replace(tmp, SETTINGS_PATH)
    if os.name != 'nt':
        os.chmod(SETTINGS_PATH, 0o600)


def safe_yaml_string(value: str) -> str:
    return json.dumps(value or '', ensure_ascii=False)


def build_document(capture: Capture, now: datetime | None = None):
    now = now or datetime.now()
    suffix = uuid.uuid4().hex[:8]
    filename = f'{now:%Y-%m-%d_%H-%M-%S}_{suffix}.md'
    rel_path = f'03 Daily Logs/{filename}'
    title = capture.text.strip().splitlines()[0][:65] if capture.text.strip() else '오늘의 경험 기록'
    # no Markdown content injection protection needed: user's own note
    header = [
        '---',
        'type: daily_capture',
        f'created: {now:%Y-%m-%dT%H:%M:%S}',
        f'project: {safe_yaml_string(capture.project.strip())}',
        f'kind: {safe_yaml_string(capture.kind)}',
        'status: inbox',
        'tags: [career, experience-log]',
        '---',
        '',
        f'# {title}',
        '',
        f'> 기록 시각: {now:%Y-%m-%d %H:%M}',
        '',
    ]
    if capture.project.strip():
        header.extend([f'프로젝트: {capture.project.strip()}', ''])
    if capture.text.strip():
        header.extend(['## 자유 기록', '', capture.text.strip(), ''])
    for heading, value in [
        ('상황', capture.situation), ('문제', capture.problem),
        ('판단', capture.judgment), ('실행', capture.action),
        ('검증', capture.verification), ('깨달음', capture.insight)
    ]:
        if value.strip():
            header.extend([f'## {heading}', '', value.strip(), ''])
    header.extend(['## 경험으로 발전시키기', '', '- [ ] 사실과 추정 구분', '- [ ] 비교했던 대안 및 실패한 시도 기록', '- [ ] 증거(커밋/이슈/수치/피드백) 연결', '- [ ] [[02 Experiences]]로 정리', ''])
    return rel_path, '\n'.join(header)


def local_save(vault_path: str, rel_path: str, markdown: str):
    if not vault_path:
        raise ValueError('옵시디언 Vault 경로를 먼저 설정해 주세요.')
    root = Path(vault_path).expanduser().resolve(strict=True)
    if not root.is_dir():
        raise ValueError('Vault 경로가 폴더가 아닙니다.')
    parts = Path(rel_path).parts
    if Path(rel_path).is_absolute() or not parts or any(part in ('..', '.') for part in parts):
        raise ValueError('올바르지 않은 노트 경로입니다.')
    dest = root.joinpath(*parts)
    dest.parent.mkdir(parents=True, exist_ok=True)
    # x means create-only: never replace a user's existing note.
    with dest.open('x', encoding='utf-8', newline='\n') as f:
        f.write(markdown)
    return dest



def valid_local_mcp_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        return (parsed.scheme in ('http', 'https') and
                parsed.hostname in ('127.0.0.1', 'localhost') and
                parsed.port is not None and parsed.username is None and
                parsed.password is None and parsed.path.rstrip('/') == '/mcp')
    except ValueError:
        return False

async def _mcp_write_async(url: str, api_key: str, rel_path: str, markdown: str):
    if not valid_local_mcp_url(url):
        raise ValueError('보안을 위해 로컬 MCP 주소(127.0.0.1 또는 localhost)만 허용합니다.')
    if not api_key.strip():
        raise ValueError('Obsidian Local REST API의 API 키가 필요합니다.')
    try:
        from mcp import ClientSession
        from mcp.client.streamable_http import streamablehttp_client
    except ImportError as exc:
        raise RuntimeError('MCP 패키지가 없습니다. install.bat을 실행해 주세요.') from exc
    headers = {'Authorization': f'Bearer {api_key.strip()}'}
    # Only enable local HTTP default in documented plugin. For HTTPS, trust its CA
    # through normal platform trust store; never disable TLS verification.
    async with streamablehttp_client(url, headers=headers, timeout=12) as (reader, writer, _):
        async with ClientSession(reader, writer) as session:
            await session.initialize()
            result = await session.call_tool('vault_write', arguments={'path': rel_path, 'content': markdown, 'ifNoneMatch': '*'})
            if getattr(result, 'isError', False):
                errors = '; '.join(getattr(block, 'text', '') for block in result.content)
                raise RuntimeError(f'MCP 노트 저장 실패: {errors[:500]}')
    return rel_path


def mcp_save(url: str, api_key: str, rel_path: str, markdown: str):
    return asyncio.run(_mcp_write_async(url, api_key, rel_path, markdown))


def save_capture(config: dict, capture: Capture):
    rel_path, markdown = build_document(capture)
    if config['mode'] == 'mcp':
        path = mcp_save(config['mcp_url'], config['mcp_api_key'], rel_path, markdown)
        return 'MCP', str(path)
    dest = local_save(config['vault_path'], rel_path, markdown)
    return 'LOCAL', str(dest)


def save_pending(capture: Capture, error_message: str):
    """Save failed submissions; never claim that this was sent to Obsidian."""
    PENDING_DIR.mkdir(parents=True, exist_ok=True)
    name = f'{datetime.now():%Y-%m-%d_%H-%M-%S}_{uuid.uuid4().hex[:8]}.json'
    obj = {'capture': capture.__dict__, 'error': str(error_message), 'when': datetime.now().isoformat()}
    path = PENDING_DIR / name
    with path.open('x', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    return path
