from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import config_validation as cv
import voluptuous as vol
import logging

from .sensor import MeterCollectorSensor

_LOGGER = logging.getLogger(__name__)

DOMAIN = "aioted_manager"

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Meter Collector integration."""
    _LOGGER.debug(f"Starting setup for {DOMAIN} integration")

    # Ensure hass.data[DOMAIN] exists
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}
        _LOGGER.debug(f"Initialized hass.data[{DOMAIN}]")

    # Register the collect_data service
    try:
        _LOGGER.debug("Registering collect_data service")
        hass.services.async_register(
            DOMAIN,
            "collect_data",
            async_handle_collect_data,
            schema=vol.Schema({
                vol.Required("instance_name"): str,
            }),
        )
        _LOGGER.info("collect_data service registered successfully")
    except Exception as e:
        _LOGGER.error(f"Failed to register collect_data service: {e}")
        return False

    _LOGGER.debug(f"Completed setup for {DOMAIN} integration")
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Meter Collector from a config entry."""
    _LOGGER.debug(f"Setting up config entry for {DOMAIN}")

    # Ensure hass.data[DOMAIN] is initialized
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}
        _LOGGER.debug(f"Initialized hass.data[{DOMAIN}]")

    # Forward the setup to the sensor and button platforms
    try:
        await hass.config_entries.async_forward_entry_setups(entry, ["sensor", "button"])
        _LOGGER.debug("Forwarded setup to sensor and button platforms")
    except Exception as e:
        _LOGGER.error(f"Failed to forward setup to platforms: {e}")
        return False

    # Register the collect_data service (avoid duplicate registration)
    if not hass.services.has_service(DOMAIN, "collect_data"):
        try:
            _LOGGER.debug("Registering collect_data service in setup_entry")
            hass.services.async_register(
                DOMAIN,
                "collect_data",
                async_handle_collect_data,
                schema=vol.Schema({
                    vol.Required("instance_name"): str,
                }),
            )
            _LOGGER.info("collect_data service registered successfully in setup_entry")
        except Exception as e:
            _LOGGER.error(f"Failed to register collect_data service in setup_entry: {e}")
            return False

    _LOGGER.debug(f"Completed setup for config entry {entry.entry_id}")
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug(f"Unloading config entry for {DOMAIN}")

    # Forward the unload to the sensor and button platforms
    try:
        await hass.config_entries.async_unload_platforms(entry, ["sensor", "button"])
        _LOGGER.debug("Unloaded sensor and button platforms")
    except Exception as e:
        _LOGGER.error(f"Failed to unload platforms: {e}")
        return False

    _LOGGER.debug(f"Completed unloading for config entry {entry.entry_id}")
    return True

async def async_handle_collect_data(call: ServiceCall) -> None:
    """Handle the collect_data service call."""
    instance_name = call.data.get("instance_name")
    _LOGGER.debug(f"Handling collect_data service call for instance: {instance_name}")

    if not instance_name:
        _LOGGER.error("No instance_name provided in service call")
        return

    # Ensure DOMAIN is in hass.data
    if DOMAIN not in hass.data:
        _LOGGER.error(f"{DOMAIN} not found in hass.data")
        return

    # Get the sensor entity
    sensor = hass.data[DOMAIN].get(instance_name)

    if sensor and hasattr(sensor, "async_update"):
        try:
            _LOGGER.debug(f"Triggering update for sensor: {instance_name}")
            await sensor.async_update()
            _LOGGER.info(f"Successfully updated sensor for instance: {instance_name}")
        except Exception as e:
            _LOGGER.error(f"Failed to update sensor for instance {instance_name}: {e}")
    else:
        _LOGGER.error(f"No valid sensor found for instance: {instance_name}")