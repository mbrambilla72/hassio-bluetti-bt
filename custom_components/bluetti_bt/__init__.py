"""Bluetti Bluetooth Integration"""

from __future__ import annotations

import re
import logging
from typing import List

from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS, CONF_TYPE, CONF_NAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.exceptions import ConfigEntryNotReady

from .const import (
    CONF_ENCRYPTION,
    CONF_MAX_RETRIES,
    CONF_PERSISTENT_CONN,
    CONF_POLLING_INTERVAL,
    CONF_POLLING_TIMEOUT,
    CONF_USE_CONTROLS,
    DATA_COORDINATOR,
    DATA_POLLING_RUNNING,
    DOMAIN,
    MANUFACTURER,
)
from .bluetti_bt_lib.const import NOTIFY_UUID
from .coordinator import PollingCoordinator

PLATFORMS: List[Platform] = [Platform.BINARY_SENSOR, Platform.SENSOR]
_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Bluetti Powerstation from a config entry."""

    _LOGGER.debug("Init Bluetti BT Integration for device %s", entry.data.get(CONF_NAME))

    address = entry.data.get(CONF_ADDRESS)
    device_name = entry.data.get(CONF_NAME)
    use_controls = entry.data.get(CONF_USE_CONTROLS)
    polling_interval = entry.data.get(CONF_POLLING_INTERVAL, 60)
    persistent_conn = entry.data.get(CONF_PERSISTENT_CONN, False)
    polling_timeout = entry.data.get(CONF_POLLING_TIMEOUT, 120)
    max_retries = entry.data.get(CONF_MAX_RETRIES, 5)
    use_encryption = entry.data.get(CONF_ENCRYPTION, False)

    if address is None:
        return False

    if not bluetooth.async_address_present(hass, address):
        raise ConfigEntryNotReady("Bluetti device not present")

    # Create data structure
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault(entry.entry_id, {})
    hass.data[DOMAIN][entry.entry_id].setdefault(DATA_POLLING_RUNNING, False)
    # Register options update listener for automatic reload (no full HA restart needed)
    entry.async_on_unload(entry.add_update_listener(_update_listener))

    # Create coordinator for polling
    _LOGGER.debug("Creating coordinator")
    coordinator = PollingCoordinator(hass, address, device_name, polling_interval, persistent_conn, polling_timeout, max_retries, use_encryption)
    await coordinator.async_config_entry_first_refresh()
    hass.data[DOMAIN][entry.entry_id].setdefault(DATA_COORDINATOR, coordinator)

    _LOGGER.debug("Creating entities")
    # Build list of platforms to load without mutating global constant
    load_platforms: list[Platform] = list(PLATFORMS)
    if use_controls is True:
        _LOGGER.warning("You are using controls with this integration at your own risk!")
        load_platforms.append(Platform.SWITCH)
        load_platforms.append(Platform.SELECT)

    # Remember actually loaded platforms for proper unload
    hass.data[DOMAIN][entry.entry_id]["platforms"] = load_platforms

    # Setup platforms
    await hass.config_entries.async_forward_entry_setups(entry, load_platforms)

    _LOGGER.debug("Setup done")

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Unloading Bluetti BT Integration")

    # Determine which platforms were loaded (stored during setup)
    load_platforms: list[Platform] = hass.data[DOMAIN].get(entry.entry_id, {}).get("platforms", list(PLATFORMS))

    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, load_platforms)

    if unload_ok:
        # Stop coordinator
        coordinator = hass.data[DOMAIN][entry.entry_id].get(DATA_COORDINATOR)
        if coordinator:
            # Disconnect from device if persistent connection was used
            if coordinator.reader and coordinator.reader.client:
                try:
                    if coordinator.reader.client.is_connected:
                        if coordinator.reader.has_notifier:
                            await coordinator.reader.client.stop_notify(NOTIFY_UUID)
                            coordinator.reader.has_notifier = False
                        await coordinator.reader.client.disconnect()
                        _LOGGER.debug("Disconnected from device")
                except Exception as e:
                    _LOGGER.warning("Error disconnecting from device: %s", e)
        
        # Remove data
        hass.data[DOMAIN].pop(entry.entry_id)
    
    _LOGGER.debug("Unload complete: %s", unload_ok)
    return unload_ok

def device_info(entry: ConfigEntry) -> DeviceInfo:
    """Device info."""
    return DeviceInfo(
        identifiers={(DOMAIN, entry.data.get(CONF_ADDRESS))},
        name=entry.title,
        manufacturer=MANUFACTURER,
        model=entry.data.get(CONF_TYPE),
    )


def get_unique_id(name: str, sensor_type: str | None = None):
    """Generate an unique id."""
    res = re.sub("[^A-Za-z0-9]+", "_", name).lower()
    if sensor_type is not None:
        return f"{sensor_type}.{res}"
    return res

async def _update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update by reloading the entry."""
    _LOGGER.debug("Options updated for entry %s. Reloading integration.", entry.entry_id)
    await hass.config_entries.async_reload(entry.entry_id)