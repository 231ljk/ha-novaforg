"""Switch platform for NovaForge output pins."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import NovaForgeCoordinator, NovaForgePin


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up switches for all output pins, including pins added later."""
    coordinator: NovaForgeCoordinator = hass.data[DOMAIN][entry.entry_id]
    added: set[str] = set()

    @callback
    def _async_add_new() -> None:
        entities: list[NovaForgeSwitch] = []
        for key, pin in coordinator.data["pins"].items():
            if pin.mode != "out" or key in added:
                continue
            added.add(key)
            entities.append(NovaForgeSwitch(coordinator, pin))
        if entities:
            async_add_entities(entities)

    _async_add_new()
    entry.async_on_unload(coordinator.async_add_listener(_async_add_new))


class NovaForgeSwitch(CoordinatorEntity[NovaForgeCoordinator], SwitchEntity):
    """An output pin exposed as a switch."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: NovaForgeCoordinator, pin: NovaForgePin) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._key = pin.key
        self._attr_name = pin.key
        self._attr_unique_id = f"{coordinator.device_id}:{pin.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.device_id)},
            name=coordinator.device_name,
            manufacturer="NovaForge",
            model=coordinator.model,
            sw_version=coordinator.sw_version,
            configuration_url=f"{coordinator.base_url}/",
        )

    @property
    def is_on(self) -> bool | None:
        """Return the current pin value."""
        value = self.coordinator.data["values"].get(self._key)
        return None if value is None else bool(value)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the pin on."""
        await self.coordinator.async_set_pin(self._key, 1)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the pin off."""
        await self.coordinator.async_set_pin(self._key, 0)
