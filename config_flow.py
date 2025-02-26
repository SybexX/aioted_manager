import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.config_entries import ConfigEntry
from homeassistant.data_entry_flow import FlowResult
import logging
import re
from .const import DOMAIN, DEFAULT_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)

class MeterCollectorConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Meter Collector."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    async def async_step_user(self, user_input=None) -> FlowResult:
        """Handle the initial step."""
        errors = {}
        _LOGGER.debug("Starting user configuration step")

        if user_input is not None:
            _LOGGER.debug(f"User input received: {user_input}")

            # Validate IP address format
            ip_address = user_input.get("ip")
            if not self._is_valid_ip(ip_address):
                errors["ip"] = "invalid_ip"
                _LOGGER.error(f"Invalid IP address format: {ip_address}")

            # Validate scan_interval
            scan_interval = user_input.get("scan_interval", DEFAULT_SCAN_INTERVAL)
            if scan_interval <= 0:
                errors["scan_interval"] = "invalid_scan_interval"
                _LOGGER.error(f"Invalid scan interval: {scan_interval}")

            # If no errors, create the config entry
            if not errors:
                _LOGGER.debug("Validation successful, creating config entry")
                return self.async_create_entry(
                    title=user_input["instance_name"],  # Use instance name as the title
                    data=user_input
                )

        # Show the form with current values or errors
        _LOGGER.debug("Displaying configuration form")
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("instance_name"): str,
                vol.Required("ip"): str,
                vol.Optional("scan_interval", default=DEFAULT_SCAN_INTERVAL): int,
                vol.Optional("log_as_csv", default=True): bool,
                vol.Optional("save_images", default=True): bool,
                vol.Required("device_class"): vol.In({
                    "power",
                    "water",
                    "gas",
                }),
                vol.Required("unit_of_measurement"): vol.In({
                    "L",
                    "m³",
                    "ft³",
                    "CCF",
                    "gal",
                    "kW",
                    "W",
                    "MW",
                    "GW",
                    "TW",
                    "BTU/h",
                }),
                vol.Optional("enable_upload", default=False): bool,
                vol.Optional("upload_url"): str,
                vol.Optional("api_key"): str,
            }),
            errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> config_entries.OptionsFlow:
        """Get the options flow for this handler."""
        _LOGGER.debug("Initializing options flow")
        return MeterCollectorOptionsFlow(config_entry)

    def _is_valid_ip(self, ip: str) -> bool:
        """Validate IP address format."""
        _LOGGER.debug(f"Validating IP address: {ip}")
        pattern = r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$"
        return bool(re.match(pattern, ip))

class MeterCollectorOptionsFlow(config_entries.OptionsFlow):
    """Handle an options flow for Meter Collector."""

    def __init__(self, config_entry: ConfigEntry):
        """Initialize options flow."""
        self.config_entry = config_entry
        _LOGGER.debug(f"Initialized options flow for config entry: {config_entry.entry_id}")

    async def async_step_init(self, user_input=None) -> FlowResult:
        """Manage the options."""
        _LOGGER.debug("Starting options configuration step")

        if user_input is not None:
            _LOGGER.debug(f"User input received for options: {user_input}")
            # Update the config entry with new options
            return self.async_create_entry(title="", data=user_input)

        # Show the form with current values
        _LOGGER.debug("Displaying options form")
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required("instance_name", default=self.config_entry.data.get("instance_name")): str,
                vol.Required("ip", default=self.config_entry.data.get("ip")): str,
                vol.Optional("scan_interval", default=self.config_entry.options.get("scan_interval", DEFAULT_SCAN_INTERVAL)): int,
                vol.Optional("log_as_csv", default=self.config_entry.options.get("log_as_csv", True)): bool,
                vol.Optional("save_images", default=self.config_entry.options.get("save_images", True)): bool,
                vol.Required("device_class", default=self.config_entry.data.get("device_class")): vol.In({
                    "power",
                    "water",
                    "gas",
                }),
                vol.Required("unit_of_measurement", default=self.config_entry.data.get("unit_of_measurement")): vol.In({
                    "L",
                    "m³",
                    "ft³",
                    "CCF",
                    "gal",
                    "kW",
                    "W",
                    "MW",
                    "GW",
                    "TW",
                    "BTU/h",
                }),
                vol.Optional("enable_upload", default=self.config_entry.data.get("enable_upload", False)): bool,
                vol.Optional("upload_url", default=self.config_entry.data.get("upload_url", "")): str,
                vol.Optional("api_key", default=self.config_entry.data.get("api_key", "")): str,
            })
        )