import logging
from homeassistant import config_entries, core

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def update_listener(hass, entry):
    _LOGGER.info(entry.data)
    _LOGGER.info(entry.options)


async def async_setup_entry(
    hass: core.HomeAssistant, entry: config_entries.ConfigEntry
) -> bool:
    """Set up platform from a ConfigEntry."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data

    await hass.config_entries.async_forward_entry_setups(entry, ["media_player"])
    entry.async_on_unload(entry.add_update_listener(update_listener))

    return True
