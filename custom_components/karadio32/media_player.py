"""Karadio32 integration."""

from datetime import timedelta
import logging
from typing import Callable, Optional

import voluptuous as vol

from homeassistant import config_entries, core
from homeassistant.components.media_player import (
    PLATFORM_SCHEMA as MEDIA_PLAYER_PLATFORM_SCHEMA,
    ConfigType,
    MediaPlayerDeviceClass,
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
)
from homeassistant.const import CONF_URL
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import DiscoveryInfoType

from .const import DOMAIN
from .karadio32 import Karadio32Api

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(seconds=5)

MEDIA_PLAYER_PLATFORM_SCHEMA = MEDIA_PLAYER_PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_URL): cv.string,
    }
)


class Karadio32(MediaPlayerEntity):
    _attr_device_class = MediaPlayerDeviceClass.RECEIVER

    def __init__(
        self,
        api: Karadio32Api,
        source_list: list | None = None,
        sw_version: str | None = None,
    ):
        super().__init__()
        self.api: Karadio32Api = api
        self._attr_unique_id = api.host
        self._attr_unique_id = f"KaRadio32-{api.host}"
        if source_list:
            self._attr_source_list = source_list
        self.supported_features = (
            MediaPlayerEntityFeature.PLAY
            | MediaPlayerEntityFeature.STOP
            | MediaPlayerEntityFeature.SELECT_SOURCE
            | MediaPlayerEntityFeature.VOLUME_SET
        )
        self.sw_version = sw_version
        self._attr_volume_step = 0.01

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self.unique_id)},
            name=self.name,
            sw_version=self.sw_version,
        )

    async def async_media_stop(self):
        await self.api.stop()
        self._attr_state = MediaPlayerState.PAUSED

    async def async_media_play(self):
        await self.api.play(self._attr_source_list.index(self._attr_source))
        self._attr_state = MediaPlayerState.PLAYING

    async def async_select_source(self, source):
        self._attr_source = source
        await self.api.play(self._attr_source_list.index(source))

    async def async_set_volume_level(self, volume):
        self._attr_volume_level = volume
        await self.api.set_volume(volume)

    async def async_update(self):
        info = await self.api.info()
        self._attr_volume_level = int(info["vol"]) / 255
        self._attr_media_title = info["tit"]
        self._attr_state = (
            MediaPlayerState.PAUSED if info["sts"] == "0" else MediaPlayerState.PLAYING
        )
        self._attr_source = self._attr_source_list[int(info["num"])]
        _LOGGER.info(info)


async def async_setup_entry(
    hass: core.HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_entities,
):
    config = hass.data[DOMAIN][config_entry.entry_id]
    _LOGGER.info(config)
    session = async_get_clientsession(hass)
    api = Karadio32Api(config[CONF_URL], session)
    player = Karadio32(api, config.get("source_list", []), config.get("sw_version"))
    async_add_entities([player], update_before_add=True)


async def async_setup_platform(
    hass: core.HomeAssistant,
    config: ConfigType,
    async_add_entities: Callable,
    discovery_info: Optional[DiscoveryInfoType] = None,
) -> None:
    session = async_get_clientsession(hass)
    api = Karadio32Api(config[CONF_URL], session)
    player = Karadio32(api)
    async_add_entities([player], update_before_add=True)
