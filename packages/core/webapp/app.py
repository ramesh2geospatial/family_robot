"""
FamilyRobot Companion PWA — FastAPI backend.

Provides REST + WebSocket endpoints for:
- Family member enrollment (face + voice capture)
- Manual device control (lights, fan, etc.)
- Memory review / search
- System status
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from packages.core.governance.identity import UNKNOWN_USER

logger = logging.getLogger(__name__)

# ── Pydantic request / response models ───────────────────────────


class DeviceCommand(BaseModel):
    device_id: str
    action: str  # "on", "off", "set_level"
    value: Optional[int] = None  # for set_level (0-100)
    user_id: Optional[str] = None


class DeviceState(BaseModel):
    device_id: str
    state: dict


class EnrollRequest(BaseModel):
    name: str
    role: str = "adult"
    language: str = "en"


class MemorySearchRequest(BaseModel):
    query: str
    k: int = 5


class MemoryEntry(BaseModel):
    id: str
    text: str
    score: float = 0.0
    meta: dict = {}


class StatusResponse(BaseModel):
    name: str
    platform: str
    status: str
    enrolled_members: int
    active_reminders: int
    current_song: Optional[str] = None
    is_playing_music: bool = False
    last_speech_heard: Optional[str] = None
    last_speech_spoken: Optional[str] = None


class MediaCommand(BaseModel):
    action: str  # "play", "pause", "resume", "stop", "next"
    query: Optional[str] = None  # for "play"


# ── App state (injected by the orchestrator) ─────────────────────


class AppState:
    """Shared application state — injected at startup."""

    def __init__(self) -> None:
        self.home: Any = None
        self.memory: Any = None
        self.identity_store: Any = None
        self.acl: Any = None
        self.config: Any = None
        self.skill_registry: Any = None
        self.audit_log: Any = None


_state = AppState()


def get_state() -> AppState:
    return _state


def set_state(
    *,
    home: Any = None,
    memory: Any = None,
    identity_store: Any = None,
    acl: Any = None,
    config: Any = None,
    skill_registry: Any = None,
    audit_log: Any = None,
) -> None:
    if home is not None:
        _state.home = home
    if memory is not None:
        _state.memory = memory
    if identity_store is not None:
        _state.identity_store = identity_store
    if acl is not None:
        _state.acl = acl
    if config is not None:
        _state.config = config
    if skill_registry is not None:
        _state.skill_registry = skill_registry
    if audit_log is not None:
        _state.audit_log = audit_log


# ── FastAPI app ──────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("FamilyRobot PWA starting up")

    # If running standalone (e.g. via uvicorn in container), auto-wire adapters
    s = get_state()
    if s.home is None:
        logger.info("Standalone mode detected. Initializing webapp components...")
        import os

        from apps.familyrobot.wiring import wire_components
        from packages.core.config import load_config
        from packages.core.governance import (
            ACL,
            AuditLog,
            FamilyMember,
            IdentityStore,
            Role,
        )
        from packages.core.memory import MemoryStore, PersistenceContext

        platform = os.environ.get("FAMILYROBOT_PLATFORM", "desktop")
        config = load_config(platform=platform)

        s.config = config
        s.home = wire_components(config).home
        persistence = PersistenceContext(db_path=config.memory_db_path)
        s.memory = MemoryStore(persistence=persistence)
        s.identity_store = IdentityStore(persistence=persistence)
        s.acl = ACL()
        s.audit_log = AuditLog(log_path="data/audit.jsonl", persistence=persistence)

        # Enroll default mock users
        s.identity_store.enroll(
            FamilyMember(user_id="parent_default", name="Ramesh", role=Role.PARENT)
        )
        s.identity_store.enroll(
            FamilyMember(user_id="child_default", name="Arjun", role=Role.CHILD)
        )

    yield
    logger.info("FamilyRobot PWA shutting down")


app = FastAPI(
    title="FamilyRobot Companion",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static PWA files
_static_dir = Path(__file__).parent / "static"
if _static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")


# ── Routes: Status ───────────────────────────────────────────────


@app.get("/api/status", response_model=StatusResponse)
async def get_status():
    s = get_state()
    member_count = len(s.identity_store.list_members()) if s.identity_store else 0

    from packages.core.webapp.status_helper import read_robot_status
    r_status = read_robot_status()

    return StatusResponse(
        name=s.config.system.name if s.config else "FamilyRobot",
        platform=s.config.platform if s.config else "unknown",
        status=r_status.get("status", "idle"),
        enrolled_members=member_count,
        active_reminders=0,
        current_song=r_status.get("current_song"),
        is_playing_music=r_status.get("is_playing_music", False),
        last_speech_heard=r_status.get("last_speech_heard"),
        last_speech_spoken=r_status.get("last_speech_spoken"),
    )


@app.post("/api/media/command")
async def media_command(cmd: MediaCommand):
    """Write the media command to a shared JSON file for the main voice loop to execute."""
    import time
    import json

    cmd_file = Path("data/media_command.json")
    cmd_file.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "action": cmd.action,
        "query": cmd.query,
        "ts": time.time()
    }
    cmd_file.write_text(json.dumps(payload), encoding="utf-8")
    return {"status": "queued", "command": payload}


# ── Routes: Device Control ──────────────────────────────────────


@app.post("/api/device/command", response_model=DeviceState)
async def device_command(cmd: DeviceCommand):
    s = get_state()
    if s.home is None:
        raise HTTPException(status_code=503, detail="Home adapter not available")

    # Enforce ACL Check
    user = UNKNOWN_USER
    if s.identity_store and cmd.user_id:
        member = s.identity_store.get_member(cmd.user_id)
        if member:
            user = member

    if s.acl:
        acl_res = s.acl.check_device(user, cmd.device_id)
        if s.audit_log:
            s.audit_log.record(
                event="webapp_acl_check",
                user_id=user.user_id,
                user_role=user.role.value,
                details={"device_id": cmd.device_id, "action": cmd.action},
                allowed=acl_res.allowed,
            )
        if not acl_res.allowed:
            raise HTTPException(status_code=403, detail=acl_res.reason)

    if cmd.action == "on":
        ok = await s.home.set_switch(cmd.device_id, True)
    elif cmd.action == "off":
        ok = await s.home.set_switch(cmd.device_id, False)
    elif cmd.action == "set_level" and cmd.value is not None:
        ok = await s.home.set_level(cmd.device_id, cmd.value)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown action: {cmd.action}")

    if not ok:
        raise HTTPException(status_code=500, detail="Command failed")

    if s.audit_log:
        s.audit_log.record(
            event="webapp_device_command",
            user_id=user.user_id,
            user_role=user.role.value,
            details={
                "device_id": cmd.device_id,
                "action": cmd.action,
                "value": cmd.value,
            },
            allowed=True,
        )

    state = await s.home.get_state(cmd.device_id)
    return DeviceState(device_id=cmd.device_id, state=state)


@app.get("/api/device/{device_id}/state", response_model=DeviceState)
async def get_device_state(device_id: str):
    s = get_state()
    if s.home is None:
        raise HTTPException(status_code=503, detail="Home adapter not available")
    state = await s.home.get_state(device_id)
    return DeviceState(device_id=device_id, state=state)


# ── Routes: Enrollment ──────────────────────────────────────────


@app.post("/api/enroll")
async def enroll_member(req: EnrollRequest):
    """Enroll a new family member (name + role).

    Face/voice capture is done client-side; this endpoint registers
    the member in the identity store.
    """
    s = get_state()
    if s.identity_store is None:
        raise HTTPException(status_code=503, detail="Identity store not available")

    from packages.core.governance.identity import FamilyMember, Role

    try:
        role = Role(req.role)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid role: {req.role}")

    import uuid

    member = FamilyMember(
        user_id=str(uuid.uuid4()),
        name=req.name,
        role=role,
        language=req.language,
    )
    s.identity_store.enroll(member)

    if s.audit_log:
        s.audit_log.record(
            event="webapp_enroll",
            user_id="admin",
            user_role="parent",
            details={"user_id": member.user_id, "name": member.name, "role": req.role},
            allowed=True,
        )

    return {"user_id": member.user_id, "name": member.name, "role": member.role.value}


@app.get("/api/members")
async def list_members():
    s = get_state()
    if s.identity_store is None:
        return {"members": []}
    members = s.identity_store.list_members()
    return {
        "members": [
            {
                "user_id": m.user_id,
                "name": m.name,
                "role": m.role.value,
                "language": m.language,
            }
            for m in members
        ]
    }


# ── Routes: Memory ──────────────────────────────────────────────


@app.post("/api/memory/search")
async def search_memory(req: MemorySearchRequest):
    s = get_state()
    if s.memory is None:
        raise HTTPException(status_code=503, detail="Memory store not available")
    hits = await s.memory.search(req.query, k=req.k)

    if s.audit_log:
        s.audit_log.record(
            event="webapp_memory_search",
            user_id="unknown",
            user_role="guest",
            details={"query": req.query, "k": req.k, "results_count": len(hits)},
            allowed=True,
        )

    return {"results": hits}


@app.post("/api/memory/store")
async def store_memory(body: dict):
    s = get_state()
    if s.memory is None:
        raise HTTPException(status_code=503, detail="Memory store not available")
    text = body.get("text", "")
    if not text:
        raise HTTPException(status_code=400, detail="Text is required")
    meta = body.get("meta", {})
    mem_id = await s.memory.store(text, meta=meta)

    if s.audit_log:
        s.audit_log.record(
            event="webapp_memory_store",
            user_id="unknown",
            user_role="guest",
            details={"memory_id": mem_id, "text_len": len(text)},
            allowed=True,
        )

    return {"id": mem_id}


# ── Routes: PWA Shell ────────────────────────────────────────────


@app.get("/", response_class=HTMLResponse)
async def serve_pwa():
    index = _static_dir / "index.html"
    if index.exists():
        return FileResponse(str(index))
    return HTMLResponse(
        "<h1>FamilyRobot Companion</h1><p>PWA static files not found.</p>"
    )


@app.get("/manifest.json")
async def serve_manifest():
    manifest = _static_dir / "manifest.json"
    if manifest.exists():
        return FileResponse(str(manifest), media_type="application/json")
    raise HTTPException(status_code=404, detail="manifest.json not found")


# ── WebSocket: Real-time status ──────────────────────────────────


@app.websocket("/ws/status")
async def ws_status(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            s = get_state()
            member_count = (
                len(s.identity_store.list_members()) if s.identity_store else 0
            )
            await websocket.send_json(
                {
                    "status": "running",
                    "enrolled_members": member_count,
                }
            )
            await asyncio.sleep(5)
    except WebSocketDisconnect:
        pass
