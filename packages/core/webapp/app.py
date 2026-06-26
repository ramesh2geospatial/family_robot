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
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# ── Pydantic request / response models ───────────────────────────

class DeviceCommand(BaseModel):
    device_id: str
    action: str  # "on", "off", "set_level"
    value: Optional[int] = None  # for set_level (0-100)


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


# ── FastAPI app ──────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("FamilyRobot PWA starting up")
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
    return StatusResponse(
        name=s.config.system.name if s.config else "FamilyRobot",
        platform=s.config.platform if s.config else "unknown",
        status="running",
        enrolled_members=member_count,
        active_reminders=0,
    )


# ── Routes: Device Control ──────────────────────────────────────

@app.post("/api/device/command", response_model=DeviceState)
async def device_command(cmd: DeviceCommand):
    s = get_state()
    if s.home is None:
        raise HTTPException(status_code=503, detail="Home adapter not available")

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
    return {"user_id": member.user_id, "name": member.name, "role": member.role.value}


@app.get("/api/members")
async def list_members():
    s = get_state()
    if s.identity_store is None:
        return {"members": []}
    members = s.identity_store.list_members()
    return {
        "members": [
            {"user_id": m.user_id, "name": m.name, "role": m.role.value, "language": m.language}
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
    return {"id": mem_id}


# ── Routes: PWA Shell ────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def serve_pwa():
    index = _static_dir / "index.html"
    if index.exists():
        return FileResponse(str(index))
    return HTMLResponse("<h1>FamilyRobot Companion</h1><p>PWA static files not found.</p>")


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
            member_count = len(s.identity_store.list_members()) if s.identity_store else 0
            await websocket.send_json({
                "status": "running",
                "enrolled_members": member_count,
            })
            await asyncio.sleep(5)
    except WebSocketDisconnect:
        pass
