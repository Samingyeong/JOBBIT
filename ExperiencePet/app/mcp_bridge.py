"""Optional direct MCP client for checking the Obsidian Local REST API plugin.
This does NOT expose the ChatGPT desktop conversation to other processes.
Credentials are never persisted to a file by Experience Pet.
"""
from __future__ import annotations
import asyncio
from urllib.parse import urlparse


def valid_endpoint(url):
    try:
        parsed=urlparse(url)
        return (parsed.scheme in ('http','https') and
            parsed.hostname in ('127.0.0.1','localhost') and
            parsed.username is None and parsed.password is None and
            parsed.port is not None and parsed.path.rstrip('/')=='/mcp')
    except ValueError:return False


async def _check(url,key):
    if not valid_endpoint(url):
        raise ValueError('127.0.0.1/localhost의 MCP 주소만 연결할 수 있습니다.')
    if not key.strip():
        raise ValueError('Obsidian 플러그인 API 키가 필요합니다.')
    try:
        from mcp import ClientSession
        from mcp.client.streamable_http import streamablehttp_client
    except ImportError as exc:
        raise RuntimeError('MCP 선택 구성요소가 없습니다. requirements-mcp.txt를 설치하세요.') from exc
    async with streamablehttp_client(url,headers={'Authorization':f'Bearer {key.strip()}'},timeout=12) as (reader,writer,_):
        async with ClientSession(reader,writer) as session:
            await session.initialize()
            response=await session.list_tools()
            names=[tool.name for tool in response.tools]
            if 'vault_write' not in names or 'vault_read' not in names:
                raise RuntimeError('MCP는 연결됐지만 vault_read/vault_write 도구가 없습니다.')
            return names


def check_connection(url,key):
    return asyncio.run(_check(url,key))
