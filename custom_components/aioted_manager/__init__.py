# c:\Users\nl\Dropbox\home_automation\meter_reader\homeassistant\custom_components\aioted_manager\custom_components\aioted_manager\__init__.py

import logging
import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.typing import ConfigType # Use ConfigType for async_setup

from .upload import daily_upload_task
from .const import DOMAIN
# Import sensor class if needed for type checking during unload
# from .sensor import MeterCollectorSensor

_LOGGER = logging.getLogger(__name__)

# Define platforms to be loaded
PLATFORMS = ["sensor", "button"]

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Meter Collector integration."""
    # This function is usually minimal for config entry based integrations
    _LOGGER.debug(f"Starting async_setup for {DOMAIN}")
    hass.data.setdefault(DOMAIN, {}) # Ensure domain key exists early
    # Register services here if they are truly global and not entry-specific
    # It's often better to register services in async_setup_entry if they depend on entries
    # await _register_services(hass) # Moved service registration to setup_entry
    _LOGGER.debug(f"Completed async_setup for {DOMAIN}")
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Meter Collector from a config entry."""
    _LOGGER.debug(f"Setting up config entry {entry.entry_id} ({entry.title}) for {DOMAIN}")

    instance_name = entry.data.get("instance_name")
    if not instance_name:
        _LOGGER.error(f"Instance name not found in config entry data for {entry.entry_id}")
        return False

    # Ensure domain and instance-specific data structures exist
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault("cancel_upload_task", {})
    # Store entry data/options if needed globally (less common now with entry object)
    # hass.data[DOMAIN][entry.entry_id] = {"entry": entry} # Example

    # --- Register Services ---
    # Register services only once, ideally check if already registered
    # Or register them here tied to the entry lifecycle if appropriate
    if not hass.services.has_service(DOMAIN, "collect_data"):
         await _register_services(hass) # Register services if not already done

    # --- Forward Setup to Platforms ---
    try:
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
        _LOGGER.debug(f"Forwarded setup to platforms {PLATFORMS} for entry {entry.entry_id}")
    except Exception as e:
        _LOGGER.error(f"Failed to forward setup to platforms for entry {entry.entry_id}: {e}", exc_info=True)
        # Clean up anything partially set up if needed before returning False
        return False

    # --- Schedule Daily Upload Task ---
    # Read options first, fallback to data for backward compatibility or initial setup
    enable_upload = entry.options.get("enable_upload", entry.data.get("enable_upload", False))
    upload_url = entry.options.get("upload_url", entry.data.get("upload_url"))
    api_key = entry.options.get("api_key", entry.data.get("api_key"))

    if enable_upload and upload_url and api_key:
        _LOGGER.info(f"Scheduling daily upload task at midnight for instance: {instance_name}")

        async def daily_upload_wrapper(_now): # Parameter name convention is often _now
            """Wrapper function to call the daily upload task."""
            # Fetch sensor instance safely from hass.data
            sensor = hass.data.get(DOMAIN, {}).get(instance_name)

            if sensor and hasattr(sensor, "available") and sensor.available and hasattr(sensor, "www_dir"):
                _LOGGER.debug(f"Executing daily upload for instance: {instance_name}")
                try:
                    await daily_upload_task(
                        hass,
                        sensor.www_dir,
                        upload_url, # Use the value read from options/data
                        api_key,    # Use the value read from options/data
                        instance_name
                    )
                except Exception as e:
                    _LOGGER.error(f"Error during scheduled daily upload for {instance_name}: {e}", exc_info=True)
            elif sensor and hasattr(sensor, "available") and not sensor.available:
                _LOGGER.debug(f"Skipping daily upload for {instance_name}: sensor is unavailable.")
            else:
                _LOGGER.error(f"Could not execute daily upload: Sensor instance '{instance_name}' not found or invalid in hass.data.")

        # Schedule the task to run daily at midnight
        # Store the removal function using the instance_name as the key
        remove_listener = async_track_time_change(hass, daily_upload_wrapper, hour=0, minute=0, second=0)
        hass.data[DOMAIN]["cancel_upload_task"][instance_name] = remove_listener
    else:
        if enable_upload and (not upload_url or not api_key):
             _LOGGER.warning(f"Upload enabled for {instance_name}, but Upload URL or API Key is missing. Task not scheduled.")
        else:
             _LOGGER.debug(f"Daily upload is disabled for instance: {instance_name}")

    # --- Register Update Listener ---
    # This is crucial for reacting to option changes from the UI
    entry.async_on_unload(entry.add_update_listener(options_update_listener))
    _LOGGER.debug(f"Registered options update listener for entry {entry.entry_id}")

    _LOGGER.info(f"Successfully set up config entry {entry.entry_id} ({entry.title})")
    return True


async def options_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    _LOGGER.info(f"Configuration options updated for {entry.title} ({entry.entry_id}), reloading integration.")
    # Reload the integration instance. This will call async_unload_entry, then async_setup_entry
    await hass.config_entries.async_reload(entry.entry_id)


async def _register_services(hass: HomeAssistant) -> None:
    """Register the services for the integration."""
    # Note: Consider if services should be per-instance or global.
    # If per-instance, they might be better registered elsewhere or handled differently.

    # --- Collect Data Service ---
    async def async_handle_collect_data(call: ServiceCall) -> None:
        """Handle the collect_data service call."""
        instance_name = call.data.get("instance_name")
        _LOGGER.debug(f"Service call collect_data received for instance: {instance_name}")

        if not instance_name:
            _LOGGER.error("Service collect_data: Missing 'instance_name'")
            return

        sensor = hass.data.get(DOMAIN, {}).get(instance_name)

        if sensor and hasattr(sensor, "async_update") and hasattr(sensor, "available"):
            if sensor.available:
                try:
                    _LOGGER.info(f"Service collect_data: Triggering update for sensor: {instance_name}")
                    # Note: Calling async_update directly might bypass throttling.
                    # Consider if a dedicated "force_update" method is needed in the sensor.
                    await sensor.async_update() # Be aware this might ignore Throttle
                    _LOGGER.debug(f"Service collect_data: Update successful for sensor: {instance_name}")
                except Exception as e:
                    _LOGGER.error(f"Service collect_data: Failed to update sensor {instance_name}: {e}", exc_info=True)
            else:
                _LOGGER.warning(f"Service collect_data: Sensor {instance_name} is unavailable, cannot collect data.")
        else:
            _LOGGER.error(f"Service collect_data: Sensor instance '{instance_name}' not found or invalid.")

    # --- Upload Data Service ---
    async def async_handle_upload_data(call: ServiceCall) -> None:
        """Handle the upload_data service call."""
        instance_name = call.data.get("instance_name")
        _LOGGER.debug(f"Service call upload_data received for instance: {instance_name}")

        if not instance_name:
            _LOGGER.error("Service upload_data: Missing 'instance_name'")
            return

        sensor = hass.data.get(DOMAIN, {}).get(instance_name)

        # Need to get upload details from the config entry associated with the sensor/instance
        # This requires finding the correct entry or storing necessary details on the sensor itself.
        # Assuming sensor has upload_url, api_key, www_dir attributes set during its init.
        if sensor and hasattr(sensor, "www_dir") and hasattr(sensor, "upload_url") and hasattr(sensor, "api_key"):
             if sensor.available: # Check if sensor is available before trying to upload
                if sensor.upload_url and sensor.api_key: # Check if upload details are configured
                    try:
                        _LOGGER.info(f"Service upload_data: Triggering upload for instance: {instance_name}")
                        await daily_upload_task(
                            hass,
                            sensor.www_dir,
                            sensor.upload_url,
                            sensor.api_key,
                            instance_name # Use instance_name from service call
                        )
                        _LOGGER.debug(f"Service upload_data: Upload successful for instance: {instance_name}")
                    except Exception as e:
                        _LOGGER.error(f"Service upload_data: Failed to upload data for {instance_name}: {e}", exc_info=True)
                else:
                    _LOGGER.error(f"Service upload_data: Upload URL or API Key not configured for instance {instance_name}.")
             else:
                 _LOGGER.warning(f"Service upload_data: Sensor {instance_name} is unavailable, cannot upload data.")
        else:
            _LOGGER.error(f"Service upload_data: Sensor instance '{instance_name}' not found or missing required attributes (www_dir, upload_url, api_key).")

    # Register services safely, checking if they already exist
    if not hass.services.has_service(DOMAIN, "collect_data"):
        try:
            _LOGGER.debug("Registering collect_data service")
            hass.services.async_register(
                DOMAIN,
                "collect_data",
                async_handle_collect_data,
                schema=vol.Schema({vol.Required("instance_name"): str}),
            )
            _LOGGER.info("collect_data service registered successfully")
        except Exception as e:
            _LOGGER.error(f"Failed to register collect_data service: {e}", exc_info=True)

    if not hass.services.has_service(DOMAIN, "upload_data"):
        try:
            _LOGGER.debug("Registering upload_data service")
            hass.services.async_register(
                DOMAIN,
                "upload_data",
                async_handle_upload_data,
                schema=vol.Schema({vol.Required("instance_name"): str}),
            )
            _LOGGER.info("upload_data service registered successfully")
        except Exception as e:
            _LOGGER.error(f"Failed to register upload_data service: {e}", exc_info=True)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    instance_name = entry.data.get("instance_name")
    _LOGGER.info(f"Unloading config entry {entry.entry_id} ({instance_name}) for {DOMAIN}")

    # --- Cancel Scheduled Tasks ---
    # Use .get() with default {} to avoid KeyError if structure isn't fully initialized
    cancel_upload_task_dict = hass.data.get(DOMAIN, {}).get("cancel_upload_task", {})
    if instance_name in cancel_upload_task_dict:
        try:
            cancel_upload_task_dict[instance_name]() # Call the removal function
            _LOGGER.debug(f"Cancelled daily upload task listener for instance: {instance_name}")
        except Exception as e:
            _LOGGER.error(f"Error cancelling upload task listener for {instance_name}: {e}")
        # Remove the entry from the dict
        del cancel_upload_task_dict[instance_name]
    else:
         _LOGGER.debug(f"No upload task listener found to cancel for instance: {instance_name}")


    # --- Unload Platforms ---
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        _LOGGER.debug(f"Successfully unloaded platforms {PLATFORMS} for entry {entry.entry_id}")
    else:
        _LOGGER.error(f"Failed to unload platforms for entry {entry.entry_id}")
        # Depending on severity, you might want to stop here
        # return False # Or attempt further cleanup

    # --- Clean up hass.data ---
    # Remove the sensor instance associated with this entry's instance_name
    if DOMAIN in hass.data and instance_name in hass.data[DOMAIN]:
        # Check if it's the sensor object before popping if necessary
        # if isinstance(hass.data[DOMAIN][instance_name], MeterCollectorSensor): # Requires MeterCollectorSensor import
        _LOGGER.debug(f"Removing sensor instance '{instance_name}' from hass.data[{DOMAIN}]")
        hass.data[DOMAIN].pop(instance_name, None) # Use pop with None default
        # else:
        #     _LOGGER.warning(f"Found item for {instance_name} in hass.data, but it wasn't the expected sensor object.")

    # Optional: Clean up hass.data[DOMAIN] subsections if they become empty
    if DOMAIN in hass.data and not hass.data[DOMAIN].get("cancel_upload_task"):
         hass.data[DOMAIN].pop("cancel_upload_task", None)
    # Optional: Remove DOMAIN from hass.data if completely empty (careful if multiple entries exist)
    # if DOMAIN in hass.data and not hass.data[DOMAIN]:
    #     hass.data.pop(DOMAIN)
    #     _LOGGER.debug(f"Removed empty hass.data[{DOMAIN}]")

    # Note: Services are typically not unregistered here unless they were specific to this entry.
    # Global services registered in async_setup usually persist.

    _LOGGER.info(f"Successfully unloaded config entry {entry.entry_id} ({instance_name})")
    return unload_ok # Return the success status of platform unloading
