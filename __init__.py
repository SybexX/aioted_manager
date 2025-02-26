from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import config_validation as cv
import voluptuous as vol
import logging
import asyncio
from homeassistant.helpers.event import async_track_time_change
from .upload import daily_upload_task  # Import the upload logic
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

    # Register the upload_data service
    try:
        _LOGGER.debug("Registering upload_data service")
        hass.services.async_register(
            DOMAIN,
            "upload_data",
            async_handle_upload_data,
            schema=vol.Schema({
                vol.Required("instance_name"): str,
            }),
        )
        _LOGGER.info("upload_data service registered successfully")
    except Exception as e:
        _LOGGER.error(f"Failed to register upload_data service: {e}")
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

    # Schedule the daily upload task if enabled
    if entry.data.get("enable_upload", False):
        upload_url = entry.data.get("upload_url")
        api_key = entry.data.get("api_key")

        async def daily_upload_wrapper(_):
            """Wrapper function to call the daily upload task."""
            sensor = hass.data[DOMAIN].get(entry.data["instance_name"])
            if sensor:
                await daily_upload_task(
                    hass,  # Pass the hass object
                    sensor.www_dir,  # Pass the www_dir
                    upload_url,  # Pass the upload URL
                    api_key  # Pass the API key
                )
            else:
                _LOGGER.error(f"No sensor found for instance: {entry.data['instance_name']}")

        # Schedule the task to run daily at midnight
        async_track_time_change(hass, daily_upload_wrapper, hour=0, minute=0, second=0)
        _LOGGER.info("Scheduled daily upload task at midnight")

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

async def async_handle_upload_data(call: ServiceCall) -> None:
    """Handle the upload_data service call."""
    instance_name = call.data.get("instance_name")
    _LOGGER.debug(f"Handling upload_data service call for instance: {instance_name}")

    if not instance_name:
        _LOGGER.error("No instance_name provided in service call")
        return

    # Ensure DOMAIN is in hass.data
    if DOMAIN not in hass.data:
        _LOGGER.error(f"{DOMAIN} not found in hass.data")
        return

    # Get the sensor entity
    sensor = hass.data[DOMAIN].get(instance_name)

    if sensor and hasattr(sensor, "www_dir"):
        try:
            _LOGGER.debug(f"Triggering upload for instance: {instance_name}")
            await daily_upload_task(
                hass,  # Pass the hass object
                sensor.www_dir,  # Pass the www_dir
                sensor.upload_url,  # Pass the upload URL
                sensor.api_key  # Pass the API key
            )
            _LOGGER.info(f"Successfully uploaded data for instance: {instance_name}")
        except Exception as e:
            _LOGGER.error(f"Failed to upload data for instance {instance_name}: {e}")
    else:
        _LOGGER.error(f"No valid sensor found for instance: {instance_name}")