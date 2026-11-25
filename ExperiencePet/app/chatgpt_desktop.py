"""Official ChatGPT Desktop app deep link for pre-filling a local chat.

Opens a composer; does NOT send content or extract ChatGPT outputs.
"""
from __future__ import annotations
import os,sys
from urllib.parse import urlencode


def make_deeplink(prompt:str,workspace:str='') -> str:
    if len(prompt)>10000:
        raise ValueError('Windows 딥링크 길이 제한을 피하기 위해 10,000자 이하만 허용합니다.')
    params={'prompt':prompt}
    if workspace: params['path']=workspace
    return 'codex://new?'+urlencode(params)


def open_interview(prompt:str,workspace:str='') -> bool:
    if sys.platform != 'win32':return False
    try:
        os.startfile(make_deeplink(prompt,workspace))
        return True
    except (OSError,ValueError):
        return False
