"""
Shared asynchronous MQTT client wrapper using aiomqtt.
"""

import asyncio
import logging
from typing import Any, Dict, Optional

from aiomqtt import Client

logger = logging.getLogger(__name__)


class MqttHomeClient:
    """
    Asynchronous self-healing MQTT client for home automation.
    Runs a background subscription loop and manages state caching.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 1883,
        username: Optional[str] = None,
        password: Optional[str] = None,
        use_tls: bool = False,
    ) -> None:
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.use_tls = use_tls

        self.states: Dict[str, str] = {}
        self._client: Optional[Client] = None
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._connected = asyncio.Event()
        self._listeners: Dict[str, Any] = {}

    def register_listener(self, prefix: str, callback: Any) -> None:
        """Register a callback for topics matching the given prefix."""
        self._listeners[prefix] = callback
        logger.info(f"Registered MQTT topic prefix listener for: {prefix}")

    async def start(self) -> None:
        """Start the background MQTT client loop."""
        self._running = True
        self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        """Stop the background MQTT client loop."""
        self._running = False
        self._connected.clear()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        self._client = None

    @property
    def is_connected(self) -> bool:
        """Return True if currently connected to the broker."""
        return self._client is not None and self._connected.is_set()

    async def wait_until_connected(self, timeout: float = 5.0) -> bool:
        """Wait until client connects to the broker, up to a timeout."""
        try:
            await asyncio.wait_for(self._connected.wait(), timeout=timeout)
            return True
        except asyncio.TimeoutError:
            return False

    async def _loop(self) -> None:
        """Background connection and subscription loop."""
        while self._running:
            try:
                # Configure client params
                tls_context = None
                if self.use_tls:
                    import ssl

                    tls_context = ssl.create_default_context()

                async with Client(
                    hostname=self.host,
                    port=self.port,
                    username=self.username,
                    password=self.password,
                    tls_context=tls_context,
                    timeout=5.0,
                ) as client:
                    self._client = client
                    self._connected.set()
                    logger.info(f"MQTT client connected to {self.host}:{self.port}")

                    # Subscribe to Tasmota stat topics
                    # stat/<device_topic>/POWER and stat/<device_topic>/RESULT
                    await client.subscribe("stat/+/POWER")
                    await client.subscribe("stat/+/RESULT")

                    # ESPHome generic state topics
                    await client.subscribe("+/switch/+/state")

                    # Zigbee2MQTT topics for Phase 3 sensors
                    await client.subscribe("zigbee2mqtt/#")

                    async for message in client.messages:
                        topic = str(message.topic)
                        payload = (
                            message.payload.decode()
                            if isinstance(message.payload, bytes)
                            else str(message.payload)
                        )
                        logger.debug(f"MQTT message: {topic} -> {payload}")

                        # Route to prefix listeners
                        for prefix, callback in self._listeners.items():
                            if topic.startswith(prefix):
                                try:
                                    if asyncio.iscoroutinefunction(callback):
                                        asyncio.create_task(callback(topic, payload))
                                    else:
                                        callback(topic, payload)
                                except Exception as err:
                                    logger.error(
                                        f"Error in MQTT listener callback: {err}"
                                    )

                        # Parse Tasmota topic
                        # stat/<device>/POWER
                        parts = topic.split("/")
                        if (
                            len(parts) >= 3
                            and parts[0] == "stat"
                            and parts[2] == "POWER"
                        ):
                            device_name = parts[1]
                            self.states[device_name] = payload
                        elif (
                            len(parts) >= 3
                            and parts[0] == "stat"
                            and parts[2] == "RESULT"
                        ):
                            # RESULT often contains POWER status in JSON
                            try:
                                import json

                                data = json.loads(payload)
                                if "POWER" in data:
                                    self.states[parts[1]] = data["POWER"]
                            except Exception:
                                pass
                        # Parse ESPHome topic
                        # <device>/switch/<name>/state
                        elif (
                            len(parts) == 4
                            and parts[1] == "switch"
                            and parts[3] == "state"
                        ):
                            device_name = f"{parts[0]}_{parts[2]}"
                            self.states[device_name] = payload

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(
                    f"MQTT connection lost/failed to {self.host}:{self.port} ({e}). "
                    "Retrying in 10s..."
                )
                self._client = None
                self._connected.clear()
                await asyncio.sleep(10)

    async def publish(self, topic: str, payload: str) -> bool:
        """Publish a payload to a topic."""
        if self._client is None or not self._connected.is_set():
            logger.warning(f"MQTT client not connected; dropping publish to {topic}")
            return False
        try:
            await self._client.publish(topic, payload=payload)
            return True
        except Exception as e:
            logger.error(f"MQTT publish to {topic} failed: {e}")
            return False
