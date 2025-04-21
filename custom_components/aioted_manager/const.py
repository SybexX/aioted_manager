# Default values
DOMAIN = "aioted_manager"
DEFAULT_SCAN_INTERVAL = 300  # Default scan interval in seconds
DEFAULT_FLOW_ROUND_TIME_WAIT = 30  # Default time in seconds to run a complete round after a flow is started

### api doc : https://jomjol.github.io/AI-on-the-edge-device-docs/REST-API/
API_flow_start = "flow_start"
# API_setPreValue = "setPreValue?numbers" #/setPreValue?numbers={instance_name}&value{last_raw_value}
API_reboot = "reboot"
# API_mqtt_publish_discovery = "mqtt_publish_discovery"
API_json = "json"
# API_value = "value"
# API_img_raw = "img_tmp/raw.jpg" #Capture and show a new raw image
API_img_alg= "img_tmp/alg.jpg" #Show last aligned image
# API_img_alg_roi= "img_tmp/alg_roi.jpg" #Show last aligned image including ROI overlay
# API_statusflow = "statusflow" #Show the actual step of the flow incl. timestamp - Example: Take Image (15:56:34)
# API_rssi = "rssi" #Show the WIFI signal strength (Unit: dBm) - Example: -51
# API_cpu_temperature = "cpu_temperature" #Show the CPU temperature (Unit: °C) - Example: 38
# API_sysinfo = "sysinfo"
# API_starttime = "starttime" #Show starttime - Example: 20230113-154634
# API_uptime = "uptime" #Show uptime - Example: 0d 00h 15m 50s
# API_lighton = "lighton" #Switch the camera flashlight on 
# API_lightoff = "lightoff" #Switch the camera flashlight off
# API_capture = "capture" #Capture a new image (without flashlight)
# API_capture_with_flashlight = "capture_with_flashlight" #Capture a new image with flashlight
# API_stream = "stream"
# API_save = "save"
# API_log = "log"
# API_log_html = "log.html"
# API_heap= "heap"
# API_metrics= "metrics"

import voluptuous as vol

# Define the valid options for device class and unit of measurement
DEVICE_CLASSES = {
    "power",
    "water",
    "gas",
}

UNIT_OF_MEASUREMENTS = {
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
}

# Define the shared schema
# not used as setup is done in config_flow.py
# but kept for reference and future use
""" SHARED_SCHEMA = {
    vol.Required("instance_name"): str,
    vol.Required("ip"): str,
    vol.Optional("scan_interval", default=DEFAULT_SCAN_INTERVAL): int,
    vol.Optional("log_as_csv", default=True): bool,
    vol.Optional("save_images", default=True): bool,
    vol.Required("device_class"): vol.In(DEVICE_CLASSES),
    vol.Required("unit_of_measurement"): vol.In(UNIT_OF_MEASUREMENTS),
    vol.Optional("enable_upload", default=False): bool,
    vol.Optional("upload_url"): str,
    vol.Optional("api_key"): str,
} """

