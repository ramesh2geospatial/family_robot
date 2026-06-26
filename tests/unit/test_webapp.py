"""
Unit tests for the Companion PWA (FastAPI backend).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from packages.core.webapp.app import app, set_state, AppState, _state


# Reset state before each test
@pytest.fixture(autouse=True)
def reset_state():
    _state.home = None
    _state.memory = None
    _state.identity_store = None
    _state.acl = None
    _state.config = None
    _state.skill_registry = None
    yield


@pytest.fixture
def mock_home():
    home = AsyncMock()
    home.set_switch = AsyncMock(return_value=True)
    home.set_level = AsyncMock(return_value=True)
    home.get_state = AsyncMock(return_value={"on": True})
    return home


@pytest.fixture
def mock_memory():
    mem = AsyncMock()
    mem.store = AsyncMock(return_value="mem-123")
    mem.search = AsyncMock(return_value=[
        {"id": "m1", "text": "test memory", "score": 0.9}
    ])
    return mem


@pytest.fixture
def mock_identity_store():
    from packages.core.governance.identity import IdentityStore
    return IdentityStore()


@pytest.fixture
def mock_config():
    cfg = MagicMock()
    cfg.system.name = "FamilyRobot"
    cfg.platform = "desktop"
    return cfg


# ── Status endpoint ──────────────────────────────────────────────

@pytest.mark.unit
def test_status_endpoint(mock_config, mock_identity_store):
    from fastapi.testclient import TestClient
    set_state(config=mock_config, identity_store=mock_identity_store)
    client = TestClient(app)
    res = client.get("/api/status")
    assert res.status_code == 200
    data = res.json()
    assert data["name"] == "FamilyRobot"
    assert data["status"] == "running"
    assert data["platform"] == "desktop"


# ── Device control ───────────────────────────────────────────────

@pytest.mark.unit
def test_device_on(mock_home):
    from fastapi.testclient import TestClient
    set_state(home=mock_home)
    client = TestClient(app)
    res = client.post("/api/device/command", json={
        "device_id": "living_room_light", "action": "on"
    })
    assert res.status_code == 200
    mock_home.set_switch.assert_called_once_with("living_room_light", True)


@pytest.mark.unit
def test_device_off(mock_home):
    from fastapi.testclient import TestClient
    set_state(home=mock_home)
    client = TestClient(app)
    res = client.post("/api/device/command", json={
        "device_id": "fan", "action": "off"
    })
    assert res.status_code == 200
    mock_home.set_switch.assert_called_once_with("fan", False)


@pytest.mark.unit
def test_device_set_level(mock_home):
    from fastapi.testclient import TestClient
    mock_home.get_state = AsyncMock(return_value={"pct": 75})
    set_state(home=mock_home)
    client = TestClient(app)
    res = client.post("/api/device/command", json={
        "device_id": "fan", "action": "set_level", "value": 75
    })
    assert res.status_code == 200
    mock_home.set_level.assert_called_once_with("fan", 75)


@pytest.mark.unit
def test_device_no_home():
    from fastapi.testclient import TestClient
    client = TestClient(app)
    res = client.post("/api/device/command", json={
        "device_id": "light", "action": "on"
    })
    assert res.status_code == 503


@pytest.mark.unit
def test_get_device_state(mock_home):
    from fastapi.testclient import TestClient
    set_state(home=mock_home)
    client = TestClient(app)
    res = client.get("/api/device/living_room_light/state")
    assert res.status_code == 200
    assert res.json()["device_id"] == "living_room_light"


# ── Enrollment ───────────────────────────────────────────────────

@pytest.mark.unit
def test_enroll_member(mock_identity_store):
    from fastapi.testclient import TestClient
    set_state(identity_store=mock_identity_store)
    client = TestClient(app)
    res = client.post("/api/enroll", json={
        "name": "Aarav", "role": "child", "language": "hi"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["name"] == "Aarav"
    assert data["role"] == "child"
    assert len(mock_identity_store.list_members()) == 1


@pytest.mark.unit
def test_enroll_invalid_role(mock_identity_store):
    from fastapi.testclient import TestClient
    set_state(identity_store=mock_identity_store)
    client = TestClient(app)
    res = client.post("/api/enroll", json={
        "name": "Test", "role": "superadmin"
    })
    assert res.status_code == 400


@pytest.mark.unit
def test_list_members(mock_identity_store):
    from fastapi.testclient import TestClient
    from packages.core.governance.identity import FamilyMember, Role
    mock_identity_store.enroll(FamilyMember(user_id="u1", name="Papa", role=Role.PARENT))
    set_state(identity_store=mock_identity_store)
    client = TestClient(app)
    res = client.get("/api/members")
    assert res.status_code == 200
    assert len(res.json()["members"]) == 1


# ── Memory ───────────────────────────────────────────────────────

@pytest.mark.unit
def test_search_memory(mock_memory):
    from fastapi.testclient import TestClient
    set_state(memory=mock_memory)
    client = TestClient(app)
    res = client.post("/api/memory/search", json={"query": "test", "k": 3})
    assert res.status_code == 200
    assert len(res.json()["results"]) == 1


@pytest.mark.unit
def test_store_memory(mock_memory):
    from fastapi.testclient import TestClient
    set_state(memory=mock_memory)
    client = TestClient(app)
    res = client.post("/api/memory/store", json={"text": "remember this"})
    assert res.status_code == 200
    assert res.json()["id"] == "mem-123"


@pytest.mark.unit
def test_store_memory_empty():
    from fastapi.testclient import TestClient
    set_state(memory=AsyncMock())
    client = TestClient(app)
    res = client.post("/api/memory/store", json={"text": ""})
    assert res.status_code == 400


# ── PWA Shell ────────────────────────────────────────────────────

@pytest.mark.unit
def test_pwa_index():
    from fastapi.testclient import TestClient
    client = TestClient(app)
    res = client.get("/")
    assert res.status_code == 200
    # Should return HTML (either the static file or the fallback)
    assert "FamilyRobot" in res.text
