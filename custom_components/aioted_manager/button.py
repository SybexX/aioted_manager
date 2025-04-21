import logging
import asyncio # Import asyncio for type hinting if needed, though not strictly required here

from homeassistant.components.button import ButtonEntity
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_call_later # Import async_call_later
from homeassistant.core import HomeAssistant, CALLBACK_TYPE # Import CALLBACK_TYPE for type hinting

# Import necessary constants from const.py
from .const import DOMAIN, API_reboot, API_flow_start, DEFAULT_FLOW_ROUND_TIME_WAIT

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the Buttons from a config entry."""
    instance_name = config_entry.data["instance_name"]
    ip_address = config_entry.data["ip"]
    _LOGGER.debug(f"Setting up buttons for instance: {instance_name}")

    # Create the Reboot button entity
    reboot_button = RebootButton(
        hass=hass,
        ip_address=ip_address,
        instance_name=instance_name
    )

    # Create the Start Flow button entity
    start_flow_button = StartFlowButton(
        hass=hass,
        ip_address=ip_address,
        instance_name=instance_name
    )

    # Add both entities
    async_add_entities([reboot_button, start_flow_button])
    _LOGGER.debug(f"Added reboot and start_flow button entities for instance: {instance_name}")

##########################
### RebootButton Class ###
##########################
class RebootButton(ButtonEntity):
    """Representation of a Reboot Button."""

    def __init__(self, hass, ip_address, instance_name):
        """Initialize the button."""
        _LOGGER.debug(f"Initializing reboot button for instance: {instance_name}")
        self._hass = hass
        self._ip_address = ip_address
        self._instance_name = instance_name
        self._attr_name = f"Reboot Device ({self._instance_name})"
        self._attr_unique_id = f"reboot_button_{self._instance_name}"
        self._attr_device_class = "restart"
        self._attr_icon = "mdi:restart"
        self._is_rebooting = False
        _LOGGER.debug(f"Reboot button initialized for instance: {instance_name}")

    @property
    def url(self):
        """Return the reboot URL."""
        return f"http://{self._ip_address}/{API_reboot}"

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return {"is_rebooting": self._is_rebooting}

    async def async_press(self):
        """Handle the button press."""
        _LOGGER.debug(f"Reboot button pressed for instance: {self._instance_name}")
        self._is_rebooting = True
        self.async_write_ha_state()
        session = async_get_clientsession(self._hass)

        try:
            _LOGGER.debug(f"Sending reboot request to {self.url}")
            async with session.get(self.url, timeout=10) as response:
                response.raise_for_status()
                _LOGGER.info(f"Reboot request successful for {self._instance_name}. Status code: {response.status}")
        except Exception as e:
            _LOGGER.error(f"An error occurred while rebooting {self._instance_name}: {e}")
        finally:
            self._is_rebooting = False
            self.async_write_ha_state()
            _LOGGER.debug(f"Reboot process finished for instance: {self._instance_name}")

    @property
    def device_info(self):
        """Return device information to link this entity to the main device."""
        return {
            "identifiers": {(DOMAIN, self._instance_name)},
            "via_device": (DOMAIN, self._instance_name),
        }


###################################
### StartFlowButton Class ###
###################################

# The StartFlowButton class is similar to the RebootButton class but handles starting a flow instead of rebooting.
# It uses the API_flow_start endpoint and has a different icon and name.
# The async_press method sends a GET request to the flow start URL, updates the state attributes,
# and schedules a delayed update of the corresponding sensor.
# The device_info method is the same as in the RebootButton class to ensure both buttons are linked to the same device.
class StartFlowButton(ButtonEntity):
    """Representation of a Start Flow Button."""

    def __init__(self, hass: HomeAssistant, ip_address: str, instance_name: str):
        """Initialize the button."""
        _LOGGER.debug(f"Initializing start flow button for instance: {instance_name}")
        self._hass = hass
        self._ip_address = ip_address
        self._instance_name = instance_name
        self._attr_name = f"Start Flow ({self._instance_name})"
        self._attr_unique_id = f"start_flow_button_{self._instance_name}"
        self._attr_icon = "mdi:play-circle-outline"
        self._is_starting_flow = False
        self._cancel_delayed_update: CALLBACK_TYPE | None = None # To store the cancel callback for the delayed update
        _LOGGER.debug(f"Start flow button initialized for instance: {instance_name}")

    @property
    def url(self):
        """Return the start flow URL."""
        return f"http://{self._ip_address}/{API_flow_start}"

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return {"is_starting_flow": self._is_starting_flow}

    async def async_press(self):
        """Handle the button press."""
        _LOGGER.debug(f"Start flow button pressed for instance: {self._instance_name}")

        # --- Cancel any previously scheduled delayed update ---
        if self._cancel_delayed_update:
            _LOGGER.debug(f"Cancelling previous delayed update for {self._instance_name}")
            self._cancel_delayed_update()
            self._cancel_delayed_update = None

        self._is_starting_flow = True
        self.async_write_ha_state()
        session = async_get_clientsession(self._hass)

        try:
            _LOGGER.debug(f"Sending start flow request to {self.url}")
            async with session.get(self.url, timeout=10) as response:
                response.raise_for_status()
                _LOGGER.info(f"Start flow request successful for {self._instance_name}. Status code: {response.status}")

                # --- Schedule the delayed sensor update ---
                _LOGGER.debug(f"Scheduling sensor update for {self._instance_name} in {DEFAULT_FLOW_ROUND_TIME_WAIT} seconds.")

                async def _delayed_sensor_update(_now): # The callback receives the timestamp it was called at
                    """Retrieve sensor and trigger its update method."""
                    _LOGGER.info(f"Executing delayed sensor update for {self._instance_name}")
                    sensor = self._hass.data.get(DOMAIN, {}).get(self._instance_name)
                    if sensor and hasattr(sensor, "_async_update"):
                        try:
                            await sensor._async_update()
                            _LOGGER.debug(f"Delayed sensor update successful for {self._instance_name}")
                        except Exception as update_err:
                            _LOGGER.error(f"Error during delayed sensor update for {self._instance_name}: {update_err}", exc_info=True)
                    else:
                        _LOGGER.error(f"Could not find sensor instance '{self._instance_name}' for delayed update.")
                    # Clear the cancel callback reference after execution
                    self._cancel_delayed_update = None

                # Schedule the coroutine to run after the delay
                self._cancel_delayed_update = async_call_later(
                    self._hass,
                    DEFAULT_FLOW_ROUND_TIME_WAIT,
                    _delayed_sensor_update
                )

        except Exception as e:
            _LOGGER.error(f"An error occurred while starting flow for {self._instance_name}: {e}")
            # If the request failed, we might not want to schedule the update,
            # or maybe we do? Current logic schedules only on success.
            # If scheduling failed, ensure cancel callback is None
            self._cancel_delayed_update = None
        finally:
            self._is_starting_flow = False
            self.async_write_ha_state()
            _LOGGER.debug(f"Start flow process finished for instance: {self._instance_name}")
            # Note: _cancel_delayed_update is NOT reset here, only if the task runs or fails to schedule.

    @property
    def device_info(self):
        """Return device information to link this entity to the main device."""
        return {
            "identifiers": {(DOMAIN, self._instance_name)},
            "via_device": (DOMAIN, self._instance_name),
        }

    # --- Add method to cancel timer on unload ---
    async def async_will_remove_from_hass(self) -> None:
        """Run when entity will be removed from hass."""
        if self._cancel_delayed_update:
            _LOGGER.debug(f"Cancelling delayed update for {self._instance_name} during removal.")
            self._cancel_delayed_update()
            self._cancel_delayed_update = None
        await super().async_will_remove_from_hass()

