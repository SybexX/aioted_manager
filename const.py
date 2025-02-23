DOMAIN = "aioted_manager"
DEFAULT_SCAN_INTERVAL = 300  # Default scan interval in seconds
DEFAULT_FLOW_ROUND_TIME_WAIT = 30  # Default time in seconds to run a complete round

### api doc : https://jomjol.github.io/AI-on-the-edge-device-docs/REST-API/
API_flow_start = "flow_start"
API_setPreValue = "setPreValue?numbers" #/setPreValue?numbers={instance_name}&value{last_raw_value}
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