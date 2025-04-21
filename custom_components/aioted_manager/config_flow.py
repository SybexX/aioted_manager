import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback, HomeAssistant # Added HomeAssistant import
from homeassistant.config_entries import ConfigEntry
from homeassistant.data_entry_flow import FlowResult
import logging
from ipaddress import ip_address
from typing import Any, Dict # Added Dict import

# Import constants correctly using CONF_SCAN_INTERVAL if defined, otherwise use string
try:
    from homeassistant.const import CONF_SCAN_INTERVAL
except ImportError:
    CONF_SCAN_INTERVAL = "scan_interval" # Fallback if not in const

from .const import (
    DOMAIN,
    DEFAULT_SCAN_INTERVAL,
    # SHARED_SCHEMA, # Keep if used, but ideally define schemas locally
    DEVICE_CLASSES,
    UNIT_OF_MEASUREMENTS
)

from homeassistant.helpers import config_validation as cv

CONFIG_SCHEMA = cv.config_entry_only_config_schema(vol.Schema({}))

_LOGGER = logging.getLogger(__name__)


# --- Helper function to validate IP ---
def _is_valid_ip(ip: str) -> bool:
    """Validate IP address format."""
    if not ip: return False # Handle empty string case
    try:
        ip_address(ip)
        return True
    except ValueError:
        return False

# --- Helper function to build the options schema ---
def _build_options_schema(config_entry: ConfigEntry) -> vol.Schema:
    """Build the options schema, pre-filling defaults from existing options."""
    # --- Recommended Options Schema (Only fields meant to be changed after setup) ---
    options_schema = {
        vol.Optional(
            CONF_SCAN_INTERVAL,
            default=config_entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        ): cv.positive_int, # Use cv.positive_int for better validation
        vol.Optional(
            "log_as_csv",
            default=config_entry.options.get("log_as_csv", True)
        ): bool,
        vol.Optional(
            "save_images",
            default=config_entry.options.get("save_images", True)
        ): bool,
        vol.Optional(
            "enable_upload",
            default=config_entry.options.get("enable_upload", False)
        ): bool,
        # Only require upload_url and api_key if enable_upload is true (more advanced schema needed)
        # For simplicity now, keep them optional strings
        vol.Optional(
            "upload_url",
            default=config_entry.options.get("upload_url", "")
        ): str,
        vol.Optional(
            "api_key",
            default=config_entry.options.get("api_key", "")
        ): str,
        # --- Fields below are usually part of config_entry.data and NOT options ---
        # --- Consider removing them from the options flow unless you specifically ---
        # --- want users to change them here post-setup. ---
        # vol.Required(
        #     "instance_name",
        #     default=config_entry.data.get("instance_name") # From data
        # ): str,
        # vol.Required(
        #     "ip",
        #     default=config_entry.data.get("ip") # From data
        # ): str,
        # vol.Required(
        #     "device_class",
        #     default=config_entry.data.get("device_class") # From data
        # ): vol.In(DEVICE_CLASSES),
        # vol.Required(
        #     "unit_of_measurement",
        #     default=config_entry.data.get("unit_of_measurement") # From data
        # ): vol.In(UNIT_OF_MEASUREMENTS),
    }
    return vol.Schema(options_schema)


class MeterCollectorConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Meter Collector."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    async def async_step_user(self, user_input: Dict[str, Any] | None = None) -> FlowResult:
        """Handle the initial step."""
        errors: Dict[str, str] = {}
        _LOGGER.debug("Starting user configuration step")

        if user_input is not None:
            _LOGGER.debug(f"User input received: {user_input}")

            # --- Simplified Validation ---
            # Validate IP address format
            if not _is_valid_ip(user_input.get("ip", "")):
                errors["ip"] = "invalid_ip"
                _LOGGER.error(f"Invalid IP address format: {user_input.get('ip')}")

            # Validate scan_interval (using CONF_SCAN_INTERVAL)
            scan_interval = user_input.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
            try:
                scan_int = int(scan_interval)
                if scan_int <= 0:
                    errors[CONF_SCAN_INTERVAL] = "invalid_scan_interval"
                    _LOGGER.error(f"Invalid scan interval: {scan_interval}")
                else:
                    _LOGGER.debug(f"Valid scan interval received : {scan_int}")
                    user_input[CONF_SCAN_INTERVAL] = scan_int # Ensure it's stored as int
            except (ValueError, TypeError):
                 errors[CONF_SCAN_INTERVAL] = "invalid_scan_interval"
                 _LOGGER.error(f"Invalid scan interval format: {scan_interval}")

            # Add validation for other required fields if necessary (e.g., instance_name)
            if not user_input.get("instance_name"):
                 errors["instance_name"] = "name_required" # Example error key

            # If no errors, create the config entry
            if not errors:
                _LOGGER.debug("Validation successful, creating config entry")

                # Separate data (usually connection/static info) from options (changeable settings)
                config_data = {
                    "instance_name": user_input["instance_name"],
                    "ip": user_input["ip"],
                    "device_class": user_input["device_class"],
                    "unit_of_measurement": user_input["unit_of_measurement"],
                    # Add other essential setup data here if needed
                }
                config_options = {
                    CONF_SCAN_INTERVAL: user_input.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                    "log_as_csv": user_input.get("log_as_csv", True),
                    "save_images": user_input.get("save_images", True),
                    "enable_upload": user_input.get("enable_upload", False),
                    "upload_url": user_input.get("upload_url", ""),
                    "api_key": user_input.get("api_key", ""),
                }

                # Optional: Set unique ID to prevent duplicate entries for the same device/instance
                # await self.async_set_unique_id(user_input["instance_name"]) # Or based on IP/MAC
                await self.async_set_unique_id(user_input["ip"])
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=user_input["instance_name"],
                    data=config_data,
                    options=config_options # Store changeable settings in options
                )

        # --- Define Schema for User Step ---
        # Use SHARED_SCHEMA if it defines exactly what you need for the *initial* setup form
        # Otherwise, define it explicitly here.
        user_schema = vol.Schema({
            vol.Required("instance_name"): str,
            vol.Required("ip"): str,
            vol.Required("device_class"): vol.In(DEVICE_CLASSES),
            vol.Required("unit_of_measurement"): vol.In(UNIT_OF_MEASUREMENTS),
            vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): int, # Use constant
            vol.Optional("log_as_csv", default=True): bool,
            vol.Optional("save_images", default=True): bool,
            vol.Optional("enable_upload", default=False): bool,
            vol.Optional("upload_url", default=""): str, # Default to empty string
            vol.Optional("api_key", default=""): str,     # Default to empty string
        })

        # Show the form with current values or errors
        _LOGGER.debug("Displaying configuration form")
        return self.async_show_form(
            step_id="user",
            data_schema=user_schema,
            errors=errors,
            description_placeholders=None, # Add placeholders if needed
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> config_entries.OptionsFlow:
        """Get the options flow for this handler."""
        _LOGGER.debug(f"Initializing options flow for entry: {config_entry.entry_id}")
        # Pass the config_entry to the OptionsFlow constructor
        return MeterCollectorOptionsFlow(config_entry)


class MeterCollectorOptionsFlow(config_entries.OptionsFlow):
    """Handle an options flow for Meter Collector."""

    # Store the config entry passed from async_get_options_flow
    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        # self.config_entry = config_entry
        # You can also pre-load options here if needed for multiple steps
        # self.options = dict(config_entry.options)
        _LOGGER.debug("OptionsFlow initialized") # Add logging for debugging

    async def async_step_init(self, user_input: Dict[str, Any] | None = None) -> FlowResult:
        """Manage the options."""
        _LOGGER.debug("Starting options configuration step (init)")
        errors: Dict[str, str] = {}

        if user_input is not None:
            _LOGGER.debug(f"User input received for options: {user_input}")

            # --- Validation for Options ---
            # Validate scan_interval (using CONF_SCAN_INTERVAL)
            scan_interval = user_input.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL) # Get submitted value
            try:
                scan_int = int(scan_interval)
                if scan_int <= 0:
                    errors[CONF_SCAN_INTERVAL] = "invalid_scan_interval"
                    _LOGGER.error(f"Invalid scan interval: {scan_interval}")
                else:
                    _LOGGER.debug(f"Valid scan interval received : {scan_int}")
                    # No need to update user_input here if validation passes
            except (ValueError, TypeError):
                 errors[CONF_SCAN_INTERVAL] = "invalid_scan_interval"
                 _LOGGER.error(f"Invalid scan interval format: {scan_interval}")

            # Add validation for other options if needed (e.g., upload_url format)

            # --- Save Options if No Errors ---
            if not errors:
                _LOGGER.debug("Validation successful, creating/updating options entry")
                # The data passed here becomes the new config_entry.options
                # It completely replaces the old options unless you merge them,
                # but typically you just save the validated input from this form.
                return self.async_create_entry(title="", data=user_input)
            else:
                _LOGGER.error(f"Validation failed for options: {errors}")

        # --- Show Form ---
        # Build the schema using the helper, pre-filling with *current* options
        options_schema = _build_options_schema(self.config_entry)

        _LOGGER.debug("Displaying options form")
        return self.async_show_form(
            step_id="init",
            data_schema=options_schema,
            errors=errors,
            description_placeholders=None, # Add placeholders if needed
        )

    # Removed _is_valid_ip as it's not typically needed/recommended in options flow
    # If IP needs changing, it's usually better to re-add the integration.
    # If you MUST allow changing IP via options, add the validation back here
    # and ensure the integration handles the IP change correctly via the update listener.

