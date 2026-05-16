"""Services for the Stash integration."""

from __future__ import annotations

import logging

import aiohttp
from homeassistant.core import HomeAssistant, ServiceCall

from .const import CONF_API_KEY, CONF_URL, DOMAIN

_LOGGER = logging.getLogger(__name__)

# Map service name → GraphQL mutation string
_MUTATIONS: dict[str, str] = {
    "scan": "mutation { metadataScan(input: {}) }",
    "generate": "mutation { metadataGenerate(input: {}) }",
    "autotag": "mutation { metadataAutoTag(input: {}) }",
    "clean": "mutation { metadataClean(input: {dryRun: false}) }",
    "identify": "mutation { metadataIdentify(input: {}) }",
    "backup": "mutation { backupDatabase(input: {download: false}) }",
    "optimise": "mutation { optimiseDatabase }",
    "stop_all_jobs": "mutation { stopAllJobs }",
}


async def _call_mutation(url: str, api_key: str, mutation: str) -> None:
    """POST a GraphQL mutation to Stash and log any errors."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{url}/graphql",
                headers={"ApiKey": api_key, "Content-Type": "application/json"},
                json={"query": mutation},
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                if response.status != 200:
                    _LOGGER.error("Stash service call failed: HTTP %d", response.status)
                    return
                result = await response.json()
                if "errors" in result:
                    _LOGGER.error("Stash GraphQL errors: %s", result["errors"])
    except Exception as err:  # pylint: disable=broad-except
        _LOGGER.error("Error calling Stash service: %s", err)


def async_setup_services(hass: HomeAssistant) -> None:
    """Register all Stash HA services."""

    # Only register once (in case of multiple config entries)
    if hass.services.has_service(DOMAIN, "scan"):
        return

    def _make_handler(mutation_key: str):
        async def handler(call: ServiceCall) -> None:
            # Find the first loaded config entry to obtain credentials
            for entry in hass.config_entries.async_entries(DOMAIN):
                url = entry.data[CONF_URL]
                api_key = entry.data[CONF_API_KEY]
                await _call_mutation(url, api_key, _MUTATIONS[mutation_key])
                return  # use the first active entry
            _LOGGER.error("No active Stash config entry found")

        return handler

    for service_name in _MUTATIONS:
        hass.services.async_register(DOMAIN, service_name, _make_handler(service_name))
    _LOGGER.debug("Stash services registered: %s", list(_MUTATIONS))


def async_unload_services(hass: HomeAssistant) -> None:
    """Remove Stash HA services (called when last entry is removed)."""
    # Only remove when no config entries remain
    if hass.config_entries.async_entries(DOMAIN):
        return
    for service_name in _MUTATIONS:
        hass.services.async_remove(DOMAIN, service_name)
    _LOGGER.debug("Stash services unregistered")
