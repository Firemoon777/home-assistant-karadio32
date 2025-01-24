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
    {vol.Required(CONF_URL): cv.string, vol.Optional("source_list"): cv.ensure_list}
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
        self._attr_unique_id = f"KaRadio32-{api.host}"
        if source_list:
            self._attr_source_list = source_list
        else:
            self._attr_source_list = []
        self.supported_features = (
            MediaPlayerEntityFeature.PLAY
            | MediaPlayerEntityFeature.STOP
            | MediaPlayerEntityFeature.PAUSE
            | MediaPlayerEntityFeature.TURN_OFF
            | MediaPlayerEntityFeature.TURN_ON
            | MediaPlayerEntityFeature.SELECT_SOURCE
            | MediaPlayerEntityFeature.VOLUME_SET
            | MediaPlayerEntityFeature.VOLUME_STEP
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
        if self._attr_source_list:
            await self.api.play(self._attr_source_list.index(self._attr_source))
        else:
            await self.api.start()

        self._attr_state = MediaPlayerState.PLAYING

    async def async_media_pause(self):
        return await self.async_media_stop()

    async def async_turn_on(self) -> None:
        await self.async_media_play()

    async def async_turn_off(self) -> None:
        await self.async_media_stop()

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
        source_id = int(info.get("num", 0))
        if source_id < len(self._attr_source_list):
            self._attr_source = self._attr_source_list[source_id]


async def async_setup_entry(
    hass: core.HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_entities,
):
    config = hass.data[DOMAIN][config_entry.entry_id]
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
    player = Karadio32(api, config.get("source_list", []))
    async_add_entities([player], update_before_add=True)
