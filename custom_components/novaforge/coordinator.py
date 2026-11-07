"""DataUpdateCoordinator that polls the NovaForge device HTTP API."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import timedelta
from typing import Any
from urllib.parse import quote_plus

import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class NovaForgePin:
    """A single pin exposed by the firmware.

    mode: "out" -> switch, "in" -> binary_sensor.
    key 即固件侧的引脚名（用户在 NovaForge 软件中填写的 label）。
    """

    key: str
    mode: str


class NovaForgeCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Polls GET /api/state and pushes pin changes via GET /api/set."""

    def __init__(
        self,
        hass: HomeAssistant,
        host: str,
        port: int,
        device_id: str,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}-{device_id}",
            update_interval=timedelta(seconds=10),
        )
        self.host = host
        self.port = port
        self.device_id = device_id
        self.base_url = f"http://{host}:{port}"
        self.device_name = device_id
        self.model: str | None = None
        self.sw_version: str | None = None

    def _apply_state(self, data: dict[str, Any]) -> dict[str, Any]:
        """Parse a firmware /api/state payload into coordinator data."""
        self.device_name = str(data.get("name") or self.device_id)
        self.model = data.get("model")
        self.sw_version = data.get("ver")
        pins: dict[str, NovaForgePin] = {}
        values: dict[str, Any] = {}
        for raw in data.get("pins") or []:
            key = str(raw.get("key") or "")
            if not key:
                continue
            pins[key] = NovaForgePin(key=key, mode=str(raw.get("mode") or "out"))
            values[key] = raw.get("value")
        return {"pins": pins, "values": values}

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch the latest state from the device."""
        session = async_get_clientsession(self.hass)
        try:
            async with asyncio.timeout(10):
                resp = await session.get(f"{self.base_url}/api/state")
                if resp.status != 200:
                    raise UpdateFailed(f"Device returned HTTP {resp.status}")
                data = await resp.json(content_type=None)
        except (TimeoutError, aiohttp.ClientError) as err:
            raise UpdateFailed(f"Error communicating with device: {err}") from err
        if not isinstance(data, dict) or not data.get("ok"):
            raise UpdateFailed("Invalid response from device")
        return self._apply_state(data)

    async def async_set_pin(self, key: str, value: int) -> None:
        """Set an output pin; /api/set returns the full state, applied directly."""
        session = async_get_clientsession(self.hass)
        url = f"{self.base_url}/api/set?key={quote_plus(key)}&value={int(value)}"
        try:
            async with asyncio.timeout(10):
                resp = await session.get(url)
                if resp.status != 200:
                    raise HomeAssistantError(f"Device returned HTTP {resp.status}")
                data = await resp.json(content_type=None)
        except (TimeoutError, aiohttp.ClientError) as err:
            raise HomeAssistantError(f"Error communicating with device: {err}") from err
        if isinstance(data, dict) and data.get("ok"):
            self.async_set_updated_data(self._apply_state(data))
