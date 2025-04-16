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
        await sensor.async_update()

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
        self.async_update = Throttle(self._scan_interval)(self._async_update)

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
        return self._enabled

    async def _async_update(self):
        """Fetch new state data for the sensor."""
        if not self._enabled:
            _LOGGER.debug(f"Skipping update: sensor {self._instance_name} is disabled.")
            return

        try:
            data = await self._fetch_json_data()
            if not data:
                self.available = False
                return

            values = self._extract_values(data)
            if not values or values.get("error"):
                self.available = False
                return

            if not self._validate_raw_value(values["raw_value"]):
                return

            if self._should_skip_update(values["raw_value"]):
                return

            # Handle prevalue setting on error
            if values["error_value"].lower() != "no error":
                await self._set_prevalue_on_error(values["pre"])

            await self._save_data(values)
            self._update_state(values)

        except Exception as e:
            _LOGGER.error(f"Unexpected error during update: {e}")
            self._state = "Error"
            self._attributes = {"error": str(e)}
            self.available = False

    async def _fetch_json_data(self):
        """Fetch JSON data from the API."""
        try:
            session = async_get_clientsession(self._hass)
            async with session.get(self._json_url) as response:
                response.raise_for_status()
                return await response.json()
        except Exception as e:
            _LOGGER.error(f"Failed to fetch JSON data from {self._json_url}: {e}")
            self._state = "Error"
            self._attributes = {"error": f"Failed to fetch JSON data: {e}"}
            return None

    def _extract_values(self, data):
        """Extract values from the JSON data."""
        if not data or not isinstance(data, dict):
            _LOGGER.error(f"Invalid JSON structure: Expected a dictionary, got {type(data)}")
            self._state = "Error"
            self._attributes = {"error": "Invalid JSON structure"}
            return None

        top_level_key = next(iter(data.keys()), None)
        if not top_level_key:
            _LOGGER.error("No top-level key found in JSON data")
            self._state = "Error"
            self._attributes = {"error": "No top-level key found in JSON data"}
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
            raw_value_float = float(raw_value)
            return True
        except (ValueError, TypeError) as e:
            _LOGGER.error(f"Invalid raw value received: {raw_value} ({e})")
            self._state = "Error"
            self._attributes = {"error": f"Invalid raw value: {raw_value}"}
            return False

    def _should_skip_update(self, raw_value):
        """Check if the update should be skipped."""
        raw_value_float = float(raw_value)
        if self._last_raw_value is not None and raw_value_float <= self._last_raw_value:
            _LOGGER.debug(f"Skipping update: New value {raw_value} is not greater than last value {self._last_raw_value}")
            return True
        return False

    async def _set_prevalue_on_error(self, pre):
        """Set the prevalue when an error is detected."""
        try:
            session = async_get_clientsession(self._hass)
            prevalue = round(float(pre))
            prevalue_url = f"http://{self._ip_address}/setPreValue?numbers={self._instance_name}&value={prevalue}"
            _LOGGER.warning(f"Error detected, setting prevalue with URL: {prevalue_url}")

            async with session.get(prevalue_url) as prevalue_response:
                prevalue_response.raise_for_status()
                response_text = await prevalue_response.text()
                _LOGGER.debug(f"Set prevalue response: {response_text}")

        except (ValueError, TypeError) as e:
            _LOGGER.error(f"Invalid prevalue received: {pre} ({e})")
            self._state = "Error"
            self._attributes = {"error": f"Invalid prevalue: {pre}"}
        except Exception as e:
            _LOGGER.error(f"Failed to set prevalue: {e}")
            self._state = "Error"
            self._attributes = {"error": f"Failed to set prevalue: {e}"}

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
            _LOGGER.debug(f"Successfully wrote to CSV file: {csv_file}")
        except Exception as e:
            _LOGGER.error(f"Failed to write to CSV file {csv_file}: {e}")

    async def _save_image(self, unix_epoch, values):
        """Save image data."""
        try:
            session = async_get_clientsession(self._hass)
            async with session.get(self._image_url) as image_response:
                image_response.raise_for_status()
                image_data = await image_response.read()

            if values["error_value"] == "no error":
                self._latest_image_path = f"/local/{DOMAIN}/{self._instance_name}/{unix_epoch}_{values['raw_value']}.jpg"
                image_file = os.path.join(self._www_dir, f"{unix_epoch}_{values['raw_value']}.jpg")
            else:
                self._latest_image_path = f"/local/{DOMAIN}/{self._instance_name}/{unix_epoch}_{values['raw_value']}_err.jpg"
                image_file = os.path.join(self._www_dir, f"{unix_epoch}_{values['raw_value']}_err.jpg")

            await self._hass.async_add_executor_job(self._write_image, image_file, image_data)
            await self._hass.async_add_executor_job(
                self._write_image, os.path.join(self._www_dir, "latest.jpg"), image_data
            )
            _LOGGER.debug(f"Successfully saved image to: {image_file}")
        except Exception as e:
            _LOGGER.error(f"Failed to fetch or save image: {e}")

    def _update_state(self, values):
        """Update the sensor state and attributes."""
        self._state = values["raw_value"]
        self._current_raw_value = float(values["raw_value"])
        self._last_raw_value = self._current_raw_value

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
            "entity_picture": self._latest_image_path,
        }

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