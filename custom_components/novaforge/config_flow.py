"""Config flow for the NovaForge integration."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant.components.zeroconf import ZeroconfServiceInfo
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_DEVICE_ID, DEFAULT_PORT, DOMAIN

_LOGGER = logging.getLogger(__name__)


async def _fetch_state(
    hass: HomeAssistant, host: str, port: int
) -> dict[str, Any] | None:
    """Fetch /api/state; return None if unreachable or not NovaForge firmware."""
    session = async_get_clientsession(hass)
    try:
        async with asyncio.timeout(10):
            resp = await session.get(f"http://{host}:{port}/api/state")
            if resp.status != 200:
                return None
            data = await resp.json(content_type=None)
    except (TimeoutError, aiohttp.ClientError, ValueError) as err:
        _LOGGER.debug("Cannot reach NovaForge device at %s:%s: %s", host, port, err)
        return None
    if not isinstance(data, dict) or data.get("fw") != "novaforge":
        return None
    return data


class NovaForgeConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle zeroconf discovery and manual setup for NovaForge devices."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._host: str | None = None
        self._port: int = DEFAULT_PORT
        self._device_id: str | None = None
        self._name: str | None = None

    async def async_step_zeroconf(
        self, discovery_info: ZeroconfServiceInfo
    ) -> ConfigFlowResult:
        """Handle a device discovered via _novaforge._tcp.local. mDNS."""
        props = {str(k).lower(): v for k, v in discovery_info.properties.items()}
        device_id = props.get("id")
        if not device_id:
            return self.async_abort(reason="no_device_id")

        self._device_id = str(device_id)
        self._host = str(discovery_info.host)
        self._port = discovery_info.port or DEFAULT_PORT
        self._name = str(props.get("name") or self._device_id)

        # 硬件 ID 是唯一键：同名设备、改名都不会冲突；
        # 已配置设备 IP 变化时自动更新地址
        await self.async_set_unique_id(self._device_id)
        self._abort_if_unique_id_configured(
            updates={CONF_HOST: self._host, CONF_PORT: self._port}
        )

        self.context["title_placeholders"] = {"name": self._name}
        return await self.async_step_zeroconf_confirm()

    async def async_step_zeroconf_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask the user to confirm adding a discovered device."""
        if user_input is not None:
            return self._create_entry()
        self._set_confirm_only()
        return self.async_show_form(
            step_id="zeroconf_confirm",
            description_placeholders={
                "name": self._name or "NovaForge",
                "id": self._device_id or "",
            },
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle manual setup by IP address."""
        errors: dict[str, str] = {}
        if user_input is not None:
            host = str(user_input[CONF_HOST]).strip()
            port = int(user_input.get(CONF_PORT) or DEFAULT_PORT)
            data = await _fetch_state(self.hass, host, port)
            if data is None:
                errors["base"] = "cannot_connect"
            elif not data.get("id"):
                return self.async_abort(reason="no_device_id")
            else:
                self._device_id = str(data["id"])
                self._host = host
                self._port = port
                self._name = str(data.get("name") or self._device_id)
                await self.async_set_unique_id(self._device_id)
                self._abort_if_unique_id_configured(
                    updates={CONF_HOST: host, CONF_PORT: port}
                )
                return self._create_entry()
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST): str,
                    vol.Optional(CONF_PORT, default=DEFAULT_PORT): vol.Coerce(int),
                }
            ),
            errors=errors,
        )

    def _create_entry(self) -> ConfigFlowResult:
        """Create the config entry."""
        return self.async_create_entry(
            title=self._name or self._device_id or "NovaForge",
            data={
                CONF_HOST: self._host,
                CONF_PORT: self._port,
                CONF_DEVICE_ID: self._device_id,
            },
        )
