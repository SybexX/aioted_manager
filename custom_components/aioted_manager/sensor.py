# c:\Users\nl\Dropbox\home_automation\meter_reader\homeassistant\custom_components\aioted_manager\custom_components\aioted_manager\sensor.py
import logging
import os
import csv
from datetime import datetime, timedelta
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util import Throttle
from .const import *

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the Meter Collector sensor from a config entry."""
    _LOGGER.debug("Setting up sensor entry")
    ip_address = config_entry.data["ip"]
    json_url = f"http://{ip_address}/{API_json}"
    image_url = f"http://{ip_address}/{API_img_alg}"
    instance_name = config_entry.data["instance_name"]
    scan_interval = config_entry.options.get("scan_interval", DEFAULT_SCAN_INTERVAL)
    log_as_csv = config_entry.options.get("log_as_csv", True)
    save_images = config_entry.options.get("save_images", True)
    www_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), f"../../www/{DOMAIN}", instance_name))
    device_class = config_entry.data["device_class"]
    unit_of_measurement = config_entry.data["unit_of_measurement"]
    enable_upload = config_entry.options.get("enable_upload", False)
    upload_url = config_entry.options.get("upload_url", "")
    api_key = config_entry.options.get("api_key", "")

    # Create the www directory if it doesn't exist
    os.makedirs(www_dir, exist_ok=True)
    _LOGGER.debug(f"Created www directory: {www_dir}")

    sensor = MeterCollectorSensor(
        hass=hass,
        ip_address=ip_address,
        json_url=json_url,
        image_url=image_url,
        www_dir=www_dir,
        scan_interval=scan_interval,
        instance_name=instance_name,
        log_as_csv=log_as_csv,
        save_images=save_images,
        device_class=device_class,
        unit_of_measurement=unit_of_measurement,
        enable_upload=enable_upload,
        upload_url=upload_url,
        api_key=api_key,
        config_entry=config_entry
    )
    async_add_entities([sensor])
    _LOGGER.debug(f"Added sensor entity for instance: {instance_name}")

    # Store the sensor in hass.data for service access
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}
        _LOGGER.debug(f"Initialized hass.data[{DOMAIN}]")
    hass.data[DOMAIN][instance_name] = sensor
    _LOGGER.debug(f"Stored sensor in hass.data[{DOMAIN}][{instance_name}]")

    # Set up the time-based update (cron-like)
    async def async_update_wrapper(now):
        """Wrapper to update the sensor data."""
        # await sensor.async_update() ## if call by throttle
        await sensor._async_update() # # Call the internal update method directly

    async_track_time_interval(hass, async_update_wrapper, timedelta(seconds=scan_interval))
    _LOGGER.debug(f"Scheduled time-based updates every {scan_interval} seconds for sensor: {instance_name}")


class MeterCollectorSensor(Entity):
    """Representation of a Meter Collector sensor."""

    def __init__(self, hass, ip_address, json_url, image_url, www_dir, scan_interval, instance_name, log_as_csv, save_images, device_class, unit_of_measurement, enable_upload, upload_url, api_key, config_entry):
        """Initialize the sensor."""
        _LOGGER.debug(f"Initializing sensor for instance: {instance_name}")
        self._hass = hass
        self._ip_address = ip_address
        self._json_url = json_url
        self._image_url = image_url
        self._www_dir = www_dir
        self._scan_interval = timedelta(seconds=scan_interval)
        self._instance_name = instance_name
        self.log_as_csv = log_as_csv
        self.save_images = save_images
        self._state = None
        self._attributes = {}
        self._last_raw_value = None
        self._current_raw_value = None
        self._error_value = None
        self._latest_image_path = None
        self._device_class = device_class
        self._unit_of_measurement = unit_of_measurement
        self.enable_upload = enable_upload
        self.upload_url = upload_url
        self.api_key = api_key
        self._config_entry = config_entry
        self._enabled = True  # Default to enabled
        _LOGGER.debug(f"Sensor initialized for instance: {instance_name}")
        # Add Throttle
        # self.async_update = Throttle(self._scan_interval)(self._async_update) #remove throttle as duplicate with async_track_time_interval

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"Meter Collector ({self._instance_name})"

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def device_class(self):
        """Return the device class of the sensor."""
        return self._device_class

    @property
    def native_unit_of_measurement(self):
        """Return the unit of measurement of the sensor."""
        return self._unit_of_measurement

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return self._attributes

    @property
    def entity_picture(self):
        """Return the entity picture (local image path)."""
        return self._latest_image_path

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        # This property now correctly reflects the internal _enabled state
        return self._enabled
    
    # @property
    # def device_info(self):
    #     return {
    #         "identifiers": {(DOMAIN, self._instance_name)}, # Or use config_entry.entry_id
    #         "name": f"AIOTED Meter ({self._instance_name})",
    #         # "manufacturer": "AI-on-the-Edge-Device", # Or the actual manufacturer
    #         # "model": "Meter Reader", # Specify model if known
    #         # "sw_version": version_from_api, # If you can get it
    #         # "via_device": (DOMAIN, self._instance_name), # 
    #         "configuration_url": f"http://{self._ip_address}", # Link to device UI
    #     }

    async def _async_update(self):
        """Fetch new state data for the sensor."""
        if not self._enabled and self._state is not None: # Check if already disabled and has a state to avoid unnecessary logs
             _LOGGER.debug(f"Skipping update: sensor {self._instance_name} is disabled.")
             return

        # Assume available until proven otherwise in this update cycle
        # self._enabled = True # Removed this line - let's only set to False on error

        try:
            data = await self._fetch_json_data()
            if not data:
                # Fetch failed, mark as unavailable if not already
                if self._enabled:
                    _LOGGER.warning(f"Marking sensor {self._instance_name} as unavailable due to fetch failure.")
                    self._enabled = False
                return

            values = self._extract_values(data)
            if not values:
                # Extraction failed, mark as unavailable if not already
                if self._enabled:
                    _LOGGER.warning(f"Marking sensor {self._instance_name} as unavailable due to data extraction failure.")
                    self._enabled = False
                return

            # If we got this far, the connection and basic data structure are okay. Mark as available.
            if not self._enabled:
                 _LOGGER.info(f"Marking sensor {self._instance_name} as available again.")
                 self._enabled = True

            if not self._validate_raw_value(values["raw_value"]):
                # Validation failed, mark as unavailable
                # Error message already logged in _validate_raw_value
                self._enabled = False
                return

            if self._should_skip_update(values["raw_value"]):
                # Not an error, just skipping update. Availability remains unchanged.
                return

            # Handle prevalue setting on error
            if values["error_value"].lower() != "no error":
                await self._set_prevalue_on_error(values["pre"])
                # Note: We might still consider the sensor available even if there's a reading error,
                # as it's still communicating. If not desired, add self._enabled = False here.

            await self._save_data(values)

            self._update_state(values)

        except Exception as e:
            _LOGGER.error(f"Unexpected error during update for {self._instance_name}: {e}", exc_info=True) # Add exc_info for full traceback
            self._state = "Error"
            self._attributes = {"error": str(e)}
            # Mark as unavailable on unexpected error
            if self._enabled:
                _LOGGER.warning(f"Marking sensor {self._instance_name} as unavailable due to unexpected error.")
                self._enabled = False

    async def _fetch_json_data(self):
        """Fetch JSON data from the API."""
        try:
            session = async_get_clientsession(self._hass)
            async with session.get(self._json_url, timeout=10) as response:
                response.raise_for_status()
                return await response.json()
        except Exception as e:
            _LOGGER.error(f"Failed to fetch JSON data from {self._json_url} for {self._instance_name}: {e}")
            self._state = "Error"
            self._attributes = {"error": f"Failed to fetch JSON data: {e}"}
            # No need to set self._enabled here, the caller (_async_update) handles it
            return None

    def _extract_values(self, data):
        """Extract values from the JSON data."""
        if not data or not isinstance(data, dict):
            _LOGGER.error(f"Invalid JSON structure for {self._instance_name}: Expected a dictionary, got {type(data)}")
            self._state = "Error"
            self._attributes = {"error": "Invalid JSON structure"}
            # No need to set self._enabled here, the caller (_async_update) handles it
            return None

        top_level_key = next(iter(data.keys()), None)
        if not top_level_key:
            _LOGGER.error(f"No top-level key found in JSON data for {self._instance_name}")
            self._state = "Error"
            self._attributes = {"error": "No top-level key found in JSON data"}
            # No need to set self._enabled here, the caller (_async_update) handles it
            return None

        nested_data = data.get(top_level_key, {})
        return {
            "value": nested_data.get("value"),
            "raw_value": nested_data.get("raw"),
            "pre": nested_data.get("pre"),
            "error_value": nested_data.get("error"),
            "rate": nested_data.get("rate"),
            "timestamp": nested_data.get("timestamp"),
        }

    def _validate_raw_value(self, raw_value):
        """Validate the raw value."""
        try:
            # Attempt conversion to float
            float(raw_value)
            return True
        except (ValueError, TypeError) as e:
            _LOGGER.error(f"Invalid raw value received for {self._instance_name}: {raw_value} ({e})")
            self._state = "Error"
            self._attributes = {"error": f"Invalid raw value: {raw_value}"}
            # No need to set self._enabled here, the caller (_async_update) handles it
            return False

    def _should_skip_update(self, raw_value):
        """Check if the update should be skipped."""
        try:
            raw_value_float = float(raw_value)
            # Check if last_raw_value exists and the new value is not greater
            if self._last_raw_value is not None and raw_value_float <= self._last_raw_value:
                _LOGGER.debug(f"Skipping update for {self._instance_name}: New value {raw_value} is not greater than last value {self._last_raw_value}")
                return True
        except (ValueError, TypeError):
             # If raw_value is invalid, validation should have caught it, but handle defensively
             _LOGGER.warning(f"Could not compare raw value {raw_value} for {self._instance_name}")
             return False # Don't skip if comparison fails
        return False

    async def _set_prevalue_on_error(self, pre):
        """Set the prevalue when an error is detected."""
        try:
            session = async_get_clientsession(self._hass)
            # Ensure 'pre' is a valid number before formatting the URL
            prevalue = round(float(pre))
            prevalue_url = f"http://{self._ip_address}/setPreValue?numbers={self._instance_name}&value={prevalue}"
            _LOGGER.warning(f"Error detected for {self._instance_name}, setting prevalue with URL: {prevalue_url}")

            async with session.get(prevalue_url, timeout=10) as prevalue_response:
                prevalue_response.raise_for_status()
                response_text = await prevalue_response.text()
                _LOGGER.debug(f"Set prevalue response for {self._instance_name}: {response_text}")

        except (ValueError, TypeError) as e:
            _LOGGER.error(f"Invalid prevalue received for {self._instance_name}: {pre} ({e})")
            self._state = "Error"
            self._attributes = {"error": f"Invalid prevalue: {pre}"}
            # Consider if this should make the sensor unavailable: self._enabled = False
        except Exception as e:
            _LOGGER.error(f"Failed to set prevalue for {self._instance_name}: {e}")
            self._state = "Error"
            self._attributes = {"error": f"Failed to set prevalue: {e}"}
            # Consider if this should make the sensor unavailable: self._enabled = False

    async def _save_data(self, values):
        """Save data to CSV and images."""
        unix_epoch = int(datetime.now().timestamp())

        if self.log_as_csv:
            await self._save_csv(unix_epoch, values)

        if self.save_images:
            await self._save_image(unix_epoch, values)

    async def _save_csv(self, unix_epoch, values):
        """Save data to a CSV file."""
        csv_file = os.path.join(self._www_dir, "log.csv")
        try:
            await self._hass.async_add_executor_job(
                self._write_csv,
                csv_file,
                unix_epoch,
                values["value"],
                values["raw_value"],
                values["pre"],
                values["error_value"],
                values["rate"],
                values["timestamp"],
            )
            _LOGGER.debug(f"Successfully wrote to CSV file for {self._instance_name}: {csv_file}")
        except Exception as e:
            _LOGGER.error(f"Failed to write to CSV file {csv_file} for {self._instance_name}: {e}")

    async def _save_image(self, unix_epoch, values):
        """Save image data."""
        image_file_base = f"{unix_epoch}_{values['raw_value']}"
        image_file_suffix = "_err.jpg" if values["error_value"] != "no error" else ".jpg"
        image_filename = f"{image_file_base}{image_file_suffix}"
        image_file_full_path = os.path.join(self._www_dir, image_filename)
        latest_image_full_path = os.path.join(self._www_dir, "latest.jpg")
        self._latest_image_path = f"/local/{DOMAIN}/{self._instance_name}/{image_filename}" # Update local path

        try:
            session = async_get_clientsession(self._hass)
            async with session.get(self._image_url, timeout=10) as image_response:
                image_response.raise_for_status()
                image_data = await image_response.read()

            # Write specific image
            await self._hass.async_add_executor_job(self._write_image, image_file_full_path, image_data)
            # Write latest image
            await self._hass.async_add_executor_job(self._write_image, latest_image_full_path, image_data)

            _LOGGER.debug(f"Successfully saved image to: {image_file_full_path} for {self._instance_name}")
        except Exception as e:
            _LOGGER.error(f"Failed to fetch or save image for {self._instance_name}: {e}")
            # Clear the image path attribute on error?
            # self._latest_image_path = None

    def _update_state(self, values):
        """Update the sensor state and attributes."""
        try:
            # Ensure raw_value can be converted to float before updating state
            current_raw_float = float(values["raw_value"])
            self._state = values["raw_value"] # Keep state as string as received? Or float? Let's keep as received for now.
            self._current_raw_value = current_raw_float
            self._last_raw_value = self._current_raw_value # Update last known good value

            self._attributes = {
                "value": values["value"],
                "raw": values["raw_value"],
                "pre": values["pre"],
                "error": values["error_value"],
                "rate": values["rate"],
                "timestamp": values["timestamp"],
                "last_updated": datetime.now().isoformat(),
                "last_raw_value": self._last_raw_value,
                "current_raw_value": self._current_raw_value,
                "entity_picture": self._latest_image_path, # Use the updated path
            }
            # Ensure sensor is marked available if state update is successful
            if not self._enabled:
                _LOGGER.info(f"Marking sensor {self._instance_name} as available after successful state update.")
                self._enabled = True

        except (ValueError, TypeError) as e:
            _LOGGER.error(f"Failed to update state for {self._instance_name} due to invalid raw value '{values['raw_value']}': {e}")
            self._state = "Error"
            self._attributes["error"] = f"Invalid raw value during state update: {values['raw_value']}"
            if self._enabled:
                 _LOGGER.warning(f"Marking sensor {self._instance_name} as unavailable due to state update failure.")
                 self._enabled = False


    def _write_csv(self, csv_file, unix_epoch, value, raw_value, pre, error_value, rate, timestamp):
        """Helper method to write all values to a CSV file in an executor thread."""
        try:
            os.makedirs(os.path.dirname(csv_file), exist_ok=True)
            file_exists = os.path.isfile(csv_file)

            with open(csv_file, "a", newline="") as csvfile:
                csv_writer = csv.writer(csvfile)
                if not file_exists:
                    csv_writer.writerow([
                        "Timestamp",
                        "Value",
                        "Raw Value",
                        "Pre",
                        "Error",
                        "Rate",
                        "Timestamp (JSON)"
                    ])
                csv_writer.writerow([
                    unix_epoch,
                    value,
                    raw_value,
                    pre,
                    error_value,
                    rate,
                    timestamp
                ])
        except Exception as e:
            _LOGGER.error(f"Failed to write to CSV file {csv_file}: {e}")

    def _write_image(self, image_file, image_data):
        """Helper method to write image data to a file in an executor thread."""
        try:
            with open(image_file, "wb") as imgfile:
                imgfile.write(image_data)
        except Exception as e:
            _LOGGER.error(f"Failed to write image to file {image_file}: {e}")

