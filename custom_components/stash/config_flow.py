"""Config flow for Stash integration."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant import config_entries, exceptions
from homeassistant.core import HomeAssistant

from .const import CONF_API_KEY, CONF_URL, DOMAIN

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_URL): str,
        vol.Required(CONF_API_KEY): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from DATA_SCHEMA with values provided by the user.
    """
    url = data[CONF_URL]
    api_key = data[CONF_API_KEY]

    # Ensure URL has proper format
    if not url.startswith(("http://", "https://")):
        url = f"http://{url}"

    # Remove trailing slash if present
    url = url.rstrip("/")

    # Test connection with a simple query
    query = """
        query {
            stats {
                sceneCount
            }
        }
    """

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{url}/graphql",
                headers={"ApiKey": api_key, "Content-Type": "application/json"},
                json={"query": query},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                if response.status == 401:
                    raise InvalidAuth
                if response.status != 200:
                    raise CannotConnect

                result = await response.json()

                # Check for GraphQL errors
                if "errors" in result:
                    _LOGGER.error("GraphQL errors: %s", result["errors"])
                    raise CannotConnect

                if "data" not in result:
                    raise CannotConnect

    except aiohttp.ClientError as err:
        raise CannotConnect from err

    # Return info that you want to store in the config entry.
    return {"title": "Stash", "url": url}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Stash."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)

                return self.async_create_entry(title=info["title"], data=user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(exceptions.HomeAssistantError):
    """Error to indicate there is invalid auth."""
