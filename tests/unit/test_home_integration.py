"""
Unit and contract tests for real home automation integration (MQTT, Kasa, Broadlink).
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from packages.core.config import AppConfig, SmartDeviceConfig
from packages.core.home.adapter import RealHomeAdapter
from packages.core.home.mqtt_client import MqttHomeClient
from packages.core.ports.home import HomePort


@pytest.fixture
def mock_config() -> AppConfig:
    config = AppConfig()
    config.home_type = "real"
    config.home_devices = {
        "living_room_light": SmartDeviceConfig(type="tasmota", address="living_light"),
        "bedroom_light": SmartDeviceConfig(type="mock", address="bedroom_light"),
        "fan": SmartDeviceConfig(type="kasa", address="192.168.1.100"),
        "tv": SmartDeviceConfig(
            type="broadlink",
            address="192.168.1.101",
            ir_commands={"ON": "26005000", "MUTE": "26002000"},
        ),
    }
    return config


@pytest.mark.asyncio
async def test_mqtt_client_loop_and_parse():
    """Verify MqttHomeClient connects, subscribes, and updates state cache."""
    # Mock aiomqtt.Client context manager
    with patch("packages.core.home.mqtt_client.Client") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        # Mock messages generator
        mock_message_1 = MagicMock()
        mock_message_1.topic = "stat/living_light/POWER"
        mock_message_1.payload = b"ON"

        mock_message_2 = MagicMock()
        mock_message_2.topic = "stat/living_light/RESULT"
        mock_message_2.payload = b'{"POWER": "OFF"}'

        mock_message_3 = MagicMock()
        mock_message_3.topic = "esphome/switch/relay/state"
        mock_message_3.payload = b"ON"

        # Make messages iterator yield these and then block/exit
        class AsyncIterator:
            def __init__(self, items):
                self.items = items
                self.idx = 0

            def __aiter__(self):
                return self

            async def __anext__(self):
                if self.idx < len(self.items):
                    val = self.items[self.idx]
                    self.idx += 1
                    return val
                # Yield control then raise stop iteration to stop loop
                await asyncio.sleep(0.01)
                raise StopAsyncIteration

        mock_client.messages = AsyncIterator(
            [mock_message_1, mock_message_2, mock_message_3]
        )

        client = MqttHomeClient(host="localhost", port=1883)
        await client.start()

        # Let loop run and consume messages
        await asyncio.sleep(0.05)

        # Assert states updated
        assert client.states.get("living_light") == "OFF"  # RESULT overrode it

        await client.stop()


@pytest.mark.asyncio
async def test_mqtt_client_publish():
    """Verify MqttHomeClient publish function calls the underlying library."""
    with patch("packages.core.home.mqtt_client.Client") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        client = MqttHomeClient()
        await client.start()
        # Set connection state
        client._client = mock_client
        client._connected.set()

        ok = await client.publish("cmnd/light/POWER", "ON")
        assert ok is True
        mock_client.publish.assert_called_once_with("cmnd/light/POWER", payload="ON")

        await client.stop()


@pytest.mark.asyncio
async def test_real_home_adapter_mock_routing(mock_config):
    """Verify RealHomeAdapter executes mock commands successfully."""
    adapter = RealHomeAdapter(config=mock_config)
    assert isinstance(adapter, HomePort)

    # Initial state
    assert await adapter.get_state("bedroom_light") == {}

    # Turn on
    ok = await adapter.set_switch("bedroom_light", on=True)
    assert ok is True
    state = await adapter.get_state("bedroom_light")
    assert state.get("on") is True

    # Dim level
    ok = await adapter.set_level("bedroom_light", pct=60)
    assert ok is True
    state = await adapter.get_state("bedroom_light")
    assert state.get("pct") == 60


@pytest.mark.asyncio
async def test_real_home_adapter_tasmota_routing(mock_config):
    """Verify RealHomeAdapter correctly routes Tasmota commands via MQTT client."""
    mock_mqtt = AsyncMock(spec=MqttHomeClient)
    # Simulate states cache returns ON
    mock_mqtt.states = {"living_light": "ON"}
    mock_mqtt.publish.return_value = True

    adapter = RealHomeAdapter(config=mock_config, mqtt_client=mock_mqtt)

    # State check
    state = await adapter.get_state("living_room_light")
    assert state.get("on") is True

    # Turn off command
    ok = await adapter.set_switch("living_room_light", on=False)
    assert ok is True
    mock_mqtt.publish.assert_called_with("cmnd/living_light/POWER", "OFF")

    # Dimmer command
    ok = await adapter.set_level("living_room_light", pct=75)
    assert ok is True
    mock_mqtt.publish.assert_called_with("cmnd/living_light/Dimmer", "75")


@pytest.mark.asyncio
async def test_real_home_adapter_kasa_routing(mock_config):
    """Verify RealHomeAdapter commands TP-Link Kasa plugs and bulbs."""
    with patch("packages.core.home.adapter.kasa") as mock_kasa:
        mock_plug = AsyncMock()
        mock_plug.is_on = True
        mock_kasa.SmartPlug.return_value = mock_plug

        mock_bulb = AsyncMock()
        mock_kasa.SmartBulb.return_value = mock_bulb

        adapter = RealHomeAdapter(config=mock_config)

        # Switch ON
        ok = await adapter.set_switch("fan", on=True)
        assert ok is True
        mock_kasa.SmartPlug.assert_called_with("192.168.1.100")
        mock_plug.update.assert_called_once()
        mock_plug.turn_on.assert_called_once()

        # Get State
        state = await adapter.get_state("fan")
        assert state.get("on") is True

        # Level dimming
        ok = await adapter.set_level("fan", pct=40)
        assert ok is True
        mock_kasa.SmartBulb.assert_called_with("192.168.1.100")
        mock_bulb.update.assert_called_once()
        mock_bulb.set_brightness.assert_called_once_with(40)


@pytest.mark.asyncio
async def test_real_home_adapter_broadlink_routing(mock_config):
    """Verify RealHomeAdapter transmits IR codes via Broadlink RM."""
    with patch("packages.core.home.adapter.broadlink") as mock_broadlink:
        mock_dev = MagicMock()
        mock_broadlink.hello.return_value = mock_dev

        adapter = RealHomeAdapter(config=mock_config)

        # Send MUTE command
        ok = await adapter.send_ir("tv", command="MUTE")
        assert ok is True
        mock_broadlink.hello.assert_called_once_with("192.168.1.101")
        mock_dev.auth.assert_called_once()
        mock_dev.send_data.assert_called_once_with(bytes.fromhex("26002000"))

        # Switch ON falls back to sending ON command
        ok = await adapter.set_switch("tv", on=True)
        assert ok is True
        mock_dev.send_data.assert_any_call(bytes.fromhex("26005000"))
