import logging
import os
import csv
from datetime import datetime, timedelta
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.aiohttp_client import async_get_clientsession
# from homeassistant.components.sensor import SensorDeviceClass
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
    log_as_csv = config_entry.options.get("log_as_csv", True)  # Use options for log_as_csv
    save_images = config_entry.options.get("save_images", True)  # Use options for save_images
    www_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), f"../../www/{DOMAIN}", instance_name))  # Save images in www folder
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

class MeterCollectorSensor(Entity):
    """Representation of a Meter Collector sensor."""

    def __init__(self, hass, ip_address, json_url, image_url, www_dir, scan_interval, instance_name, log_as_csv, save_images , device_class, unit_of_measurement, enable_upload, upload_url, api_key, config_entry):
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
        self._last_update = None
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

    async def async_update(self):
        """Fetch new state data for the sensor."""
        # _LOGGER.debug(f"Starting async_update for instance: {self._instance_name}")
        try:
            # Check if device is enabled
            if not self._enabled:
                _LOGGER.debug(f"Skipping update: sensor {self._instance_name} is disabled.")
                return

            # Throttle updates based on scan_interval
            if self._last_update is not None:
                time_since_last_update = datetime.now() - self._last_update
                if time_since_last_update < self._scan_interval:
                    remaining_time = self._scan_interval - time_since_last_update
                    _LOGGER.debug(
                        f"Skipping update for '{self._instance_name}' due to throttle, last update was {self._last_update.strftime('%Y-%m-%d %H:%M:%S.%f')}, "
                        f"scan_interval is {self._scan_interval}. "
                        f"Remaining: {remaining_time.total_seconds():.0f} sec"
                    )
                    self._last_update = datetime.now()
                    return
            
            _LOGGER.debug(f"Updating sensor : {self._instance_name}")

            session = async_get_clientsession(self._hass)

            # Fetch JSON data
            try:
                _LOGGER.debug(f"Fetching JSON data from {self._json_url}")
                async with session.get(self._json_url) as response:
                    response.raise_for_status()
                    data = await response.json()
                _LOGGER.debug(f"Received JSON data: {data}")
            except Exception as e:
                _LOGGER.error(f"Failed to fetch JSON data from {self._json_url}: {e}")
                self._state = "Error"
                self._attributes = {"error": f"Failed to fetch JSON data: {e}"}
                return

            # Validate JSON data
            if not data or not isinstance(data, dict):
                _LOGGER.error(f"Invalid JSON structure: Expected a dictionary, got {type(data)}")
                self._state = "Error"
                self._attributes = {"error": "Invalid JSON structure"}
                return

            # Get the first (and only) top-level key
            top_level_key = next(iter(data.keys()), None)
            if not top_level_key:
                _LOGGER.error("No top-level key found in JSON data")
                self._state = "Error"
                self._attributes = {"error": "No top-level key found in JSON data"}
                return

            # Extract values from the nested object
            nested_data = data.get(top_level_key, {})
            value = nested_data.get("value")
            raw_value = nested_data.get("raw")
            pre = nested_data.get("pre")
            error_value = nested_data.get("error") #, "no error")
            rate = nested_data.get("rate")
            timestamp = nested_data.get("timestamp")
            _LOGGER.debug(f"Extracted values: value={value}, raw_value={raw_value}, pre={pre}, error_value={error_value}, rate={rate}, timestamp={timestamp}")
            
            

                
            # Set prevalue on error 
            ## TODO : implement "Neg. Rate - Read" and "Rate too high - Read"
            if error_value.lower() != "no error": # error occured
                _LOGGER.warning(f"Error detected, setting prevalue: {error_value}")
                
                try:
                    raw_value_float = float(raw_value)
                except (ValueError, TypeError) as e:
                    _LOGGER.error(f"Invalid raw value received: {raw_value} ({e})")
                    self._state = "Error"
                    self._attributes = {"error": f"Invalid raw value: {raw_value}"}
                    # raw_value_float = 0
                    self._last_update = datetime.now()
                    #return
                try:
                    # if raw_value_float < float(pre):
                        # prevalue = round(raw_value_float)
                    # else:
                        # prevalue = round(float(pre))
                    raw_value_float = round(float(pre))
                    prevalue = round(float(pre))
                    prevalue_url = f"http://{self._ip_address}/setPreValue?numbers={self._instance_name}&value={prevalue}"
                    _LOGGER.debug(f"Setting prevalue with URL: {prevalue_url}")
                    async with session.get(prevalue_url) as prevalue_response:
                        prevalue_response.raise_for_status()
                        data = await prevalue_response.text()
                    _LOGGER.debug(f"Set prevalue response: {data}")
                except Exception as e:
                    _LOGGER.error(f"Failed to set prevalue: {e}")
                    self._state = "Error"
                    self._attributes = {"error": f"Failed to set prevalue: {e}"}
                finally:
                    self._last_update = datetime.now()
                    return
            else: # no error
            
                # Validate raw_value
                try:
                    raw_value_float = float(raw_value)
                    self._last_update = datetime.now()
                except (ValueError, TypeError) as e:
                    _LOGGER.error(f"Invalid raw value received: {raw_value} ({e})")
                    self._state = "Error"
                    self._attributes = {"error": f"Invalid raw value: {raw_value}"}
                    self._last_update = datetime.now()
                    return
            

            # Skip if the new value is not greater than the last recorded value
            if self._last_raw_value is not None and raw_value_float <= self._last_raw_value:
                _LOGGER.debug(f"Skipping update: New value {raw_value} is not greater than last value {self._last_raw_value}")
                self._last_update = datetime.now()
                return

            # Get the current Unix epoch time
            unix_epoch = int(datetime.now().timestamp())

            # Save all values to CSV (Move to executor)
            if self.log_as_csv:
                csv_file = os.path.join(self._www_dir, "log.csv")
                try:
                    _LOGGER.debug(f"Writing to CSV file: {csv_file}")
                    await self._hass.async_add_executor_job(
                        self._write_csv,
                        csv_file,
                        unix_epoch,
                        value,
                        raw_value,
                        pre,
                        error_value,
                        rate,
                        timestamp
                    )
                    _LOGGER.debug(f"Successfully wrote to CSV file: {csv_file}")
                except Exception as e:
                    _LOGGER.error(f"Failed to write to CSV file {csv_file}: {e}")

            # Save image (Move to executor)
            if self.save_images:
                try:
                    _LOGGER.debug(f"Fetching image from {self._image_url}")
                    # Fetch image from the remote URL
                    async with session.get(self._image_url) as image_response:
                        image_response.raise_for_status()
                        image_data = await image_response.read()

                    # Determine image file name
                    # image_file = os.path.join(self._www_dir, f"{unix_epoch}_{raw_value}.jpg")
                    if error_value == "no error":
                        self._latest_image_path = f"/local/{DOMAIN}/{self._instance_name}/{unix_epoch}_{raw_value}.jpg"
                        image_file = os.path.join(self._www_dir, f"{unix_epoch}_{raw_value}.jpg")
                    else: #TODO : implement "Neg. Rate - Read" and "Rate too high - Read"
                        self._latest_image_path = f"/local/{DOMAIN}/{self._instance_name}/{unix_epoch}_{raw_value}_err.jpg"
                        image_file = os.path.join(self._www_dir, f"{unix_epoch}_{raw_value}_err.jpg")
                    _LOGGER.debug(f"Saving image to: {image_file}")
                    # Save the image
                    await self._hass.async_add_executor_job(self._write_image, image_file, image_data) #current image
                    await self._hass.async_add_executor_job(self._write_image, os.path.join(self._www_dir, "latest.jpg"), image_data) #latest (to simple image entities access)
                    _LOGGER.debug(f"Successfully saved image to: {image_file}")
                except Exception as e:
                    _LOGGER.error(f"Failed to fetch or save image: {e}")

            # Update state and attributes
            self._state = raw_value
            self._current_raw_value = raw_value_float

            # Include all relevant fields in attributes
            self._attributes = {
                "value": value,
                "raw": raw_value,
                "pre": pre,
                "error": error_value,
                "rate": rate,
                "timestamp": timestamp,
                "last_updated": datetime.now().isoformat(),
                "last_raw_value": self._last_raw_value,
                "current_raw_value": self._current_raw_value,
                "entity_picture": self._latest_image_path,
            }

            # Record the last update time and last raw value
            #self._last_update = datetime.now()
            self._last_raw_value = raw_value_float

            #_LOGGER.debug(f"Finished async_update for instance: {self._instance_name}")


        except Exception as e:
            _LOGGER.error(f"Unexpected error during update: {e}")
            self._state = "Error"
            self._attributes = {"error": str(e)}        
        finally:
            self._last_update = datetime.now()
            #_LOGGER.debug(f"Finished async_update for instance: {self._instance_name}")
    def _write_csv(self, csv_file, unix_epoch, value, raw_value, pre, error_value, rate, timestamp):
        """Helper method to write all values to a CSV file in an executor thread."""
        try:
            # Ensure the directory exists
            os.makedirs(os.path.dirname(csv_file), exist_ok=True)

            # Check if the file exists
            file_exists = os.path.isfile(csv_file)

            # Open the file in append mode
            with open(csv_file, "a", newline="") as csvfile:
                csv_writer = csv.writer(csvfile)

                # Write headers if the file doesn't exist
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

                # Write the row with all values
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
