from copy import deepcopy
from datetime import datetime
import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries, core
from homeassistant.const import CONF_URL
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN
from .karadio32 import Karadio32Api

_LOGGER = logging.getLogger(__name__)
MAIN_SCHEMA = vol.Schema({vol.Required(CONF_URL): cv.string})


class Karadio32ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Karadio32 custom flow."""

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        description_placeholders: dict[str, str] = {}
        if user_input is not None:
            session = async_get_clientsession(self.hass)
            radio = Karadio32Api(user_input[CONF_URL], session)
            try:
                user_input["sw_version"] = await radio.version()
                user_input["source_list"] = await radio.source_list()
                return self.async_create_entry(
                    title="KaRadio32",
                    data=user_input,
                )
            except TimeoutError:
                description_placeholders["reason"] = "TimeoutError"
            except Exception as e:
                description_placeholders["reason"] = str(e)

            errors["base"] = "unreachable"

        return self.async_show_form(
            step_id="user",
            data_schema=MAIN_SCHEMA,
            errors=errors,
            description_placeholders=description_placeholders,
        )

    @staticmethod
    @core.callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return OptionsFlowHandler()


class OptionsFlowHandler(config_entries.OptionsFlow):
    async def async_step_init(
        self, user_input: dict[str, Any] = None
    ) -> dict[str, Any]:
        errors: dict[str, str] = {}
        description_placeholders: dict[str, str] = {}

        if user_input is not None:
            if user_input.pop("update_info", False):
                session = async_get_clientsession(self.hass)
                radio = Karadio32Api(self.config_entry.data[CONF_URL], session)
                try:
                    user_input[CONF_URL] = self.config_entry.data[CONF_URL]
                    user_input["sw_version"] = await radio.version()
                    user_input["source_list"] = await radio.source_list()
                except TimeoutError:
                    description_placeholders["reason"] = "TimeoutError"
                    errors["base"] = "unreachable"
                except Exception as e:
                    description_placeholders["reason"] = str(e)
                    errors["base"] = "unreachable"
            if not errors:
                self.hass.config_entries.async_update_entry(
                    self.config_entry, data=user_input
                )
                return self.async_create_entry(title=None, data=None)

        option_schema = vol.Schema(
            {
                vol.Required(
                    CONF_URL, default=self.config_entry.data[CONF_URL]
                ): cv.string,
                vol.Optional("update_info"): cv.boolean,
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=option_schema,
            description_placeholders=description_placeholders,
        )
