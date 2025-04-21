import logging
from homeassistant.components.button import ButtonEntity
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from .const import DOMAIN, API_reboot # Import DOMAIN and API_reboot

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the Reboot Button from a config entry."""
    _LOGGER.debug(f"Setting up button for instance: {config_entry.data['instance_name']}")
    ip_address = config_entry.data["ip"]
    instance_name = config_entry.data["instance_name"]

    # Create the button entity
    button = RebootButton(
        hass=hass,
        ip_address=ip_address,
        instance_name=instance_name
        # Pass config_entry if needed for device_info identifier, but instance_name is sufficient here
    )
    async_add_entities([button])
    _LOGGER.debug(f"Added button entity for instance: {instance_name}")

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
        self._is_rebooting = False  # Add a new state to check if rebooting
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
        self.async_write_ha_state()  # force update on button
        session = async_get_clientsession(self._hass)

        try:
            _LOGGER.debug(f"Sending reboot request to {self.url}")
            # Example: Use GET instead of POST if required
            async with session.get(self.url, timeout=10) as response: # Added timeout
                response.raise_for_status()  # Raise an exception for bad status codes
                _LOGGER.info(f"Reboot request successful for {self._instance_name}. Status code: {response.status}")
        except Exception as e:
            _LOGGER.error(f"An error occurred while rebooting {self._instance_name}: {e}")
        finally:
            self._is_rebooting = False
            self.async_write_ha_state()  # force update on button
            _LOGGER.debug(f"Reboot process finished for instance: {self._instance_name}")


    @property
    def device_info(self):
        """Return device information to link this entity to the main device."""
        # This button entity belongs to the device defined by the sensor.
        # We link it using 'via_device' with the *same identifier* used in the sensor's 'identifiers'.
        # Even with via_device, HA requires 'identifiers' or 'connections' to be present.
        return {
            # Add identifiers, using the same tuple as the main device defined in sensor.py
            # This satisfies the HA schema validation requirement.
            "identifiers": {(DOMAIN, self._instance_name)},

            # IMPORTANT: Use 'via_device' to link to the sensor's device entry.
            # The value MUST be the *exact same tuple* used in the sensor's 'identifiers'.
            "via_device": (DOMAIN, self._instance_name),

            # You generally DON'T need to repeat name, manufacturer, etc. here
            # as HA will get them from the device linked via 'via_device'.
        }

