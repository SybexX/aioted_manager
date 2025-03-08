import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.config_entries import ConfigEntry
from homeassistant.data_entry_flow import FlowResult
import logging
from ipaddress import ip_address
from typing import Any

from .const import DOMAIN, DEFAULT_SCAN_INTERVAL, SHARED_SCHEMA, DEVICE_CLASSES, UNIT_OF_MEASUREMENTS

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
            ip_address_str = user_input.get("ip")
            if not self._is_valid_ip(ip_address_str):
                errors["ip"] = "invalid_ip"
                _LOGGER.error(f"Invalid IP address format: {ip_address_str}")

            # Validate scan_interval
            scan_interval = user_input.get("scan_interval", DEFAULT_SCAN_INTERVAL)
            if scan_interval <= 0:
                errors["scan_interval"] = "invalid_scan_interval"
                _LOGGER.error(f"Invalid scan interval: {scan_interval}")
            else:
                _LOGGER.debug(f"Valid scan interval received : {scan_interval}")

            # If no errors, create the config entry
            if not errors:
                _LOGGER.debug("Validation successful, creating config entry")
                return self.async_create_entry(
                    title=user_input["instance_name"],  # Use instance name as the title
                    data=user_input,
                    options={
                        "scan_interval": user_input.get("scan_interval", DEFAULT_SCAN_INTERVAL),
                        "log_as_csv": user_input.get("log_as_csv", True),
                        "save_images": user_input.get("save_images", True),
                        "enable_upload": user_input.get("enable_upload", False),
                        "upload_url": user_input.get("upload_url", ""),
                        "api_key": user_input.get("api_key", ""),
                    }
                )

        # Show the form with current values or errors
        _LOGGER.debug("Displaying configuration form")
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(SHARED_SCHEMA),  # use shared shema
            errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> config_entries.OptionsFlow:
        """Get the options flow for this handler."""
        _LOGGER.debug("Initializing options flow")
        return MeterCollectorOptionsFlow()

    def _is_valid_ip(self, ip: str) -> bool:
        """Validate IP address format."""
        _LOGGER.debug(f"Validating IP address: {ip}")
        try:
            ip_address(ip)
            _LOGGER.debug(f"IP address is valid: {ip}")
            return True
        except ValueError:
            _LOGGER.warning(f"IP address is invalid: {ip}")
            return False


class MeterCollectorOptionsFlow(config_entries.OptionsFlow):
    """Handle an options flow for Meter Collector."""

    # Removed: __init__ method. No need to assign self.config_entry manually

    async def async_step_init(self, user_input=None) -> FlowResult:
        """Manage the options."""
        _LOGGER.debug("Starting options configuration step")
        errors = {}

        if user_input is not None:
            _LOGGER.debug(f"User input received for options: {user_input}")
            # Validate IP address format
            ip_address_str = user_input.get("ip")
            if not self._is_valid_ip(ip_address_str):
                errors["ip"] = "invalid_ip"
                _LOGGER.error(f"Invalid IP address format: {ip_address_str}")

            # Validate scan_interval
            scan_interval = user_input.get("scan_interval", DEFAULT_SCAN_INTERVAL)
            if scan_interval <= 0:
                errors["scan_interval"] = "invalid_scan_interval"
                _LOGGER.error(f"Invalid scan interval: {scan_interval}")
            else:
                _LOGGER.debug(f"Valid scan interval received : {scan_interval}")

            if not errors:
                _LOGGER.debug("Validation successful, creating option config entry")
                # Merge data and options before updating the config entry
                new_options = {**self.config_entry.options, **user_input}
                self.hass.config_entries.async_update_entry(
                    self.config_entry, options=new_options
                )
                _LOGGER.debug(f"update entry with new options : {new_options}")
                await self.hass.config_entries.async_reload(self.config_entry.entry_id)
                return self.async_create_entry(title="", data={})
            else:
                _LOGGER.error(f"validation fail")
        # Show the form with current values
        _LOGGER.debug("Displaying options form")
        data_schema = {
            vol.Required("instance_name", default=self.config_entry.data.get("instance_name")): str,
            vol.Required("ip", default=self.config_entry.data.get("ip")): str,
            vol.Required("device_class", default=self.config_entry.data.get("device_class")): vol.In(
                DEVICE_CLASSES),
            vol.Required("unit_of_measurement", default=self.config_entry.data.get("unit_of_measurement")): vol.In(
                UNIT_OF_MEASUREMENTS),
            vol.Optional("scan_interval",
                         default=self.config_entry.options.get("scan_interval", DEFAULT_SCAN_INTERVAL)): int,
            vol.Optional("log_as_csv", default=self.config_entry.options.get("log_as_csv", True)): bool,
            vol.Optional("save_images", default=self.config_entry.options.get("save_images", True)): bool,
            vol.Optional("enable_upload", default=self.config_entry.options.get("enable_upload", False)): bool,
            vol.Optional("upload_url", default=self.config_entry.options.get("upload_url", "")): str,
            vol.Optional("api_key", default=self.config_entry.options.get("api_key", "")): str,
        }
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(data_schema),
            errors=errors,
        )

    def _is_valid_ip(self, ip_str: str) -> bool:
        """Check if the provided string is a valid IPv4 or IPv6 address."""
        _LOGGER.debug(f"Validating IP address: {ip_str}")
        try:
            ip_address(ip_str)
            _LOGGER.debug(f"IP address is valid: {ip_str}")
            return True
        except ValueError:
            _LOGGER.warning(f"IP address is invalid: {ip_str}")
            return False
