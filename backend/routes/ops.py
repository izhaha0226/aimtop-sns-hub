from pathlib import Path
import re
import shlex
import subprocess

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from middleware.auth import get_current_user
from models.user import User

router = APIRouter(prefix="/api/v1/ops", tags=["ops"])


class OpenTerminalRequest(BaseModel):
    agent_key: str


def _build_agent_key(kind: str, target: Path) -> str:
    base = target.name.lstrip(".") or kind
    slug = re.sub(r"[^a-z0-9]+", "-", f"{kind}-{base}".lower()).strip("-")
    return slug or kind


def _discover_agent_homes() -> dict[str, Path]:
    home_root = Path.home()
    discovered: dict[str, Path] = {}

    for child in home_root.iterdir():
        if not child.is_dir():
            continue
        if child.name.startswith(".hermes") and (child / "config.yaml").exists():
            discovered[_build_agent_key("hermes", child)] = child

    openclaw_home = home_root / ".openclaw"
    if openclaw_home.exists():
        discovered[_build_agent_key("openclaw", openclaw_home)] = openclaw_home

    claude_home = home_root / ".claude"
    if claude_home.exists():
        discovered[_build_agent_key("claude", claude_home)] = claude_home

    return discovered


def _open_terminal(path: str) -> None:
    shell_command = f"cd {shlex.quote(path)}; clear"
    applescript_command = shell_command.replace("\\", "\\\\").replace('"', '\\"')
    script = (
        'tell application "Terminal"\n'
        'activate\n'
        f'do script "{applescript_command}"\n'
        'end tell'
    )
    subprocess.run(["osascript", "-e", script], check=True)


@router.post("/open-terminal")
async def open_terminal(
    payload: OpenTerminalRequest,
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="관리자만 터미널을 실행할 수 있습니다")

    targets = _discover_agent_homes()
    target = targets.get(payload.agent_key)
    if not target:
        raise HTTPException(status_code=400, detail="지원하지 않는 에이전트입니다")

    if not target.exists():
        raise HTTPException(status_code=404, detail="대상 폴더를 찾을 수 없습니다")

    try:
        _open_terminal(str(target))
    except subprocess.CalledProcessError as exc:
        raise HTTPException(status_code=500, detail=f"터미널 실행 실패: {exc}") from exc

    return {
        "ok": True,
        "agent_key": payload.agent_key,
        "path": str(target),
        "detected_count": len(targets),
    }
