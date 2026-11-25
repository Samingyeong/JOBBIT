"""ChatGPT Desktop local MCP server; no ChatGPT account tokens or OpenAI API."""
from __future__ import annotations
import json
from mcp.server.fastmcp import FastMCP
from bridge_core import status,recent_captures,read_capture as read_daily_capture,related,save_note

mcp=FastMCP('Experience Pet Career Vault')

@mcp.tool()
def get_vault_status() -> dict:
    """Check the configured local Obsidian Career Vault."""
    return status()

@mcp.tool()
def list_recent_captures(limit:int=5) -> list[dict]:
    """List recent Experience Pet raw daily captures. Reads no other vault folders."""
    return recent_captures(limit)

@mcp.tool()
def read_capture(capture_name:str) -> dict:
    """Read only an Experience Pet owned daily capture by filename (not path)."""
    return read_daily_capture(capture_name)

@mcp.tool()
def search_career_notes(query:str,limit:int=4) -> list[dict]:
    """Search only Project and Experience notes for interview context."""
    return related(query,limit)

@mcp.tool()
def save_experience_note(title:str,markdown:str,project:str='',source_capture:str='') -> dict:
    """CREATE a new reviewed Obsidian Experience note, NEVER overwrite existing notes. Call only AFTER user previews the entire note and explicitly approves saving. Returns actual destination path."""
    return save_note(title,markdown,project,source_capture)

if __name__=='__main__':
    mcp.run(transport='stdio')
