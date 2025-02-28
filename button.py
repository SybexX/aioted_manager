import logging
from homeassistant.components.button import ButtonEntity
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from .const import *

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the Reboot Button from a config entry."""
    ip_address = config_entry.data["ip"]
    instance_name = config_entry.data["instance_name"]

    # Create the button entity
    button = RebootButton(
        hass=hass,
        ip_address=ip_address,
        instance_name=instance_name
    )
    async_add_entities([button])

class RebootButton(ButtonEntity):
    """Representation of a Reboot Button."""

    def __init__(self, hass, ip_address, instance_name):
        """Initialize the button."""
        self._hass = hass
        self._ip_address = ip_address
        self._instance_name = instance_name
        self._attr_name = f"Reboot Device ({self._instance_name})"
        self._attr_unique_id = f"reboot_button_{self._instance_name}"
        self._attr_device_class = "restart"
        self._attr_icon = "mdi:restart"
        self._is_rebooting = False  # Add a new state to check if rebooting

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
        self._is_rebooting = True
        self.async_write_ha_state()  # force update on button
        session = async_get_clientsession(self._hass)

        try:
            # Example: Use GET instead of POST if required
            async with session.get(self.url) as response:
                if response.status == 200:
                    _LOGGER.info(f"Reboot request successful for {self._instance_name}")
                else:
                    _LOGGER.error(f"Failed to reboot {self._instance_name}. Status code: {response.status}")
        except Exception as e:
            _LOGGER.error(f"An error occurred while rebooting {self._instance_name}: {e}")
        finally:
            self._is_rebooting = False
            self.async_write_ha_state()  # force update on button
