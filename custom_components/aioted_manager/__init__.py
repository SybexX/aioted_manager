from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.config_entries import ConfigEntry
import voluptuous as vol
import logging
from homeassistant.helpers.event import async_track_time_change
from .upload import daily_upload_task
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Meter Collector integration."""
    _LOGGER.debug(f"Starting setup for {DOMAIN} integration")
    # Nothing to setup here, config entries are the way
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Meter Collector from a config entry."""
    _LOGGER.debug(f"Setting up config entry for {DOMAIN}")
    try:
        # Ensure hass.data[DOMAIN] exists
        if DOMAIN not in hass.data:
            hass.data[DOMAIN] = {}
            _LOGGER.debug(f"Initialized hass.data[{DOMAIN}]")

        # Register the services
        if not await _register_services(hass):
            return False
        
        # Ensure instance name is available
        instance_name = entry.data.get("instance_name")
        if not instance_name:
            _LOGGER.error("Instance name not found in config entry")
            return False
            
        # Store cancel_upload_task to stop it later if entry unloaded
        if "cancel_upload_task" not in hass.data[DOMAIN]:
            hass.data[DOMAIN]["cancel_upload_task"] = {}

        # Forward the setup to the sensor and button platforms
        try:
            await hass.config_entries.async_forward_entry_setups(entry, ["sensor", "button"])
            _LOGGER.debug("Forwarded setup to sensor and button platforms")
        except Exception as e:
            _LOGGER.error(f"Failed to forward setup to platforms: {e}")
            return False

        # Schedule the daily upload task if enabled
        if entry.options.get("enable_upload", entry.data.get("enable_upload", False)):  # check in options first, after in data
            upload_url = entry.options.get("upload_url", entry.data.get("upload_url"))  # check in options first, after in data
            api_key = entry.options.get("api_key", entry.data.get("api_key"))  # check in options first, after in data

            async def daily_upload_wrapper(_):
                """Wrapper function to call the daily upload task."""
                sensor = hass.data[DOMAIN].get(instance_name)
                if sensor and sensor._enabled:
                    await daily_upload_task(
                        hass,  # Pass the hass object
                        sensor.www_dir,  # Pass the www_dir
                        upload_url,  # Pass the upload URL
                        api_key,  # Pass the API key
                        instance_name
                    )
                elif sensor and not sensor._enabled:
                    _LOGGER.debug(f"upload for {instance_name} is disable")
                else:
                    _LOGGER.error(f"No sensor found for instance: {instance_name}")

            # Schedule the task to run daily at midnight
            remove_listener = async_track_time_change(hass, daily_upload_wrapper, hour=0, minute=0, second=0)
            hass.data[DOMAIN]["cancel_upload_task"][instance_name] = remove_listener
            _LOGGER.info(f"Scheduled daily upload task at midnight for instance : {instance_name}")
        else:
            _LOGGER.debug(f"upload is disable for {instance_name}")
    except Exception as e:
        _LOGGER.error(f"Unexpected error in async_setup_entry: {e}")
        return False
    _LOGGER.debug(f"Completed setup for config entry {entry.entry_id}")
    return True

async def _register_services(hass: HomeAssistant) -> bool:
    """Register the services for the integration."""
    try:
        # Register the collect_data service
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
                if sensor._enabled:
                    try:
                        _LOGGER.debug(f"Triggering update for sensor: {instance_name}")
                        await sensor.async_update()
                        _LOGGER.info(f"Successfully updated sensor for instance: {instance_name}")
                    except Exception as e:
                        _LOGGER.error(f"Failed to update sensor for instance {instance_name}: {e}")
                else:
                    _LOGGER.debug(f"sensor {instance_name} is disabled")
            else:
                _LOGGER.error(f"No valid sensor found for instance: {instance_name}")

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
                        sensor.api_key,  # Pass the API key
                        sensor._instance_name
                    )
                    _LOGGER.info(f"Successfully uploaded data for instance: {instance_name}")
                except Exception as e:
                    _LOGGER.error(f"Failed to upload data for instance {instance_name}: {e}")
            else:
                _LOGGER.error(f"No valid sensor found for instance: {instance_name}")

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
    except Exception as e:
        _LOGGER.error(f"Unexpected error in _register_services : {e}")
        return False
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug(f"Unloading config entry for {DOMAIN}")
    instance_name = entry.data.get("instance_name")

    # Forward the unload to the sensor and button platforms
    try:
        await hass.config_entries.async_unload_platforms(entry, ["sensor", "button"])
        _LOGGER.debug("Unloaded sensor and button platforms")
    except Exception as e:
        _LOGGER.error(f"Failed to unload platforms: {e}")
        return False

    # Remove time-tracked task
    if instance_name in hass.data[DOMAIN]["cancel_upload_task"]:
        hass.data[DOMAIN]["cancel_upload_task"][instance_name]()
        del hass.data[DOMAIN]["cancel_upload_task"][instance_name]
        _LOGGER.info(f"Stopped daily upload task for instance : {instance_name}")

    _LOGGER.debug(f"Completed unloading for config entry {entry.entry_id}")
    return True
