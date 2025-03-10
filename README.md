# AI on the Edge Device (AIOTED) Meter Collector Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge)](https://github.com/hacs/integration)
[![Validate with hassfest](https://github.com/nliaudat/aioted_manager/actions/workflows/hassfest.yaml/badge.svg)](https://github.com/nliaudat/aioted_manager/actions/workflows/hassfest.yaml)

This custom integration allows you to seamlessly integrate and manage your [AI on the Edge Device](https://jomjol.github.io/AI-on-the-edge-device-docs/) (AIOTED) water, gas, or electricity meter readers directly with Home Assistant. It eliminates the need for an MQTT gateway, offering a more streamlined and direct integration. It provides sensor data, image capture, and reboot functionality, along with advanced features like image upload and CSV logging.

![AIOTED Example](https://github.com/user-attachments/assets/30e62ae1-1644-4da6-88ca-04afc89f7647)


## Features

*   **Sensor Data:**
    *   Reads and displays the current meter value from the AIOTED device.
    *   Supports different device classes (water, gas, power) and units of measurement (liters, cubic meters, gallons, kWh, etc.).
    *   Provides additional attributes like raw value, pre-value, error status, timestamp, and rate.
*   **Image Capture:**
    *   Retrieves the latest image from the AIOTED device.
    *   Optionally saves images locally for easy access and display in the entity.
    *   Optionally save all values to a csv.
*   **Reboot Button:**
    *   Adds a button entity to reboot the AIOTED device remotely.
*   **Services:**
    *   `aioted_manager.collect_data`: Manually triggers a data update for a specific AIOTED instance.
    *   `aioted_manager.upload_data`: Manually triggers a data upload for a specific AIOTED instance.
*   **Data Logging:**
    *   Optionally logs all read values to a CSV file (`log.csv`) in the `www/aioted_manager/<instance_name>/` directory for historical analysis.
*   **Image Upload:**
    *   Optionally uploads zipped images to a remote server.
*   **Customizable Options:**
    *   **Scan Interval:** The interval in seconds between each data reading (default: 300 seconds).
    *   **Save Images:** Enable/disable image saving (default: Enabled).
    *   **Log as CSV:** Enable/disable CSV logging (default: Enabled).
    *   **Enable Upload:** Enable/disable image upload (default: Disabled).
    *   **Upload URL:** The URL of the server where images will be uploaded (if enabled).
    *   **API Key:** The API key required for the upload server (if needed).

## Installation

### HACS (Recommended)

1.  Ensure that you have the Home Assistant Community Store (HACS) installed.
2.  Go to **HACS > Integrations**.
3.  Click **"Explore & Download Repositories"**.
4.  Search for "AIOTED Manager" and select it.
5.  Click **"Download"**.
6.  Restart Home Assistant.

### Manual Installation

1.  Download the latest release from the [GitHub repository](https://github.com/nliaudat/aioted_manager).
2.  Unzip the release and copy the `aioted_manager` folder into your Home Assistant's custom components directory (`<your_config_dir>/custom_components/`).
3.  **(Optional) Set Permissions:**
    *   If needed, ensure the folder and files have the correct permissions (755):
        ```bash
        chmod -R 755 <your_config_dir>/custom_components/aioted_manager
        ```
4.  Restart Home Assistant.

## Configuration

1.  **Add the Integration:**
    *   Go to **Settings > Devices & Services > Integrations** in your Home Assistant instance.
    *   Click **"+ Add Integration"**.
    *   Search for "AIOTED Manager" and select it.
2.  **Configure a New Instance:**
    *   Enter the following information:
        *   **Instance Name:** A unique name for this AIOTED device. This name **must** correspond to your "Number Sequence" name configured on the AIOTED device (e.g., "cold", "water_meter").
        *   **IP Address:** The IP address of your AIOTED device.
        *   **Device Class:** Select the device class (e.g., "water", "gas", or "power").
        *   **Unit of Measurement:** Select the unit of measurement (e.g., "L", "m³", "ft³", "gal", "kW", etc.).
    *   Click **"Submit"**.
3.  **Set Options:**
    *   After the integration is installed, find the "AIOTED Manager" integration in the list and click **"Configure"** on the integration card.
    *   You can then customize the following options:
        *   **Instance Name:** The unique name for this AIOTED device.
        *   **IP Address:** The IP address of your AIOTED device.
        *   **Device Class:** The device class (e.g., "water", "gas", or "power").
        *   **Unit of Measurement:** The unit of measurement (e.g., "L", "m³", "ft³", "gal", "kW", etc.).
        *   **Scan Interval:** The interval in seconds between each data reading (default: 300 seconds).
        *   **Log as CSV:** Enable/disable CSV logging (default: Enabled).
        *   **Save Images:** Enable/disable image saving (default: Enabled).
        *   **Enable Upload:** Enable/disable image upload (default: Disabled).
        *   **Upload URL:** The URL of the server where images will be uploaded (if enabled).
        *   **API Key:** The API key required for the upload server (if needed).

## Entities

After successful configuration, the following entities will be created for each instance:

*   **Sensor:**
    *   `sensor.meter_collector_<instance_name>` (or similar): Displays the current meter reading.
    *   Attributes:
        *   `value`: The processed meter value.
        *   `raw`: The raw value directly from the AIOTED device.
        *   `pre`: The pre-value (used in some error recovery scenarios).
        *   `error`: Any error message from the AIOTED device.
        *   `rate`: The current rate of flow (if available).
        *   `timestamp`: The timestamp of the last reading.
        *   `last_updated`: The last time the sensor was updated in Home Assistant.
        *   `last_raw_value`: The last raw value.
        *   `current_raw_value`: The current raw value.
        *   `entity_picture`: The path to the actual image.
*   **Button:**
    *   `button.reboot_device_<instance_name>` (or similar): A button to reboot the AIOTED device.

## Services

The integration exposes the following services:

*   **`aioted_manager.collect_data`**
    *   **Description:** Manually triggers a data collection for the specified AIOTED instance.
    *   **Data:**
        *   `instance_name` (Required): The instance name of the AIOTED device.
*   **`aioted_manager.upload_data`**
    *   **Description:** Manually triggers an image upload for the specified AIOTED instance.
    *   **Data:**
        *   `instance_name` (Required): The instance name of the AIOTED device.

## Displaying the Latest Image in Lovelace

You can use the [Local File integration](https://www.home-assistant.io/integrations/local_file/) to display the latest image in your Lovelace dashboards:

1.  **Configure `local_file` Integration:**
    *   Add the `local_file` integration to your Home Assistant instance if you haven't already.
2.  **Add a Local File Camera:**
    *   In your `configuration.yaml` add a camera with path to the latest image:

      ```yaml
      camera:
        - platform: local_file
          file_path: www/aioted_manager/<instance_name>/latest.jpg
          name: "AIOTED <instance_name>"
      ```
    * Replace <instance_name> by you instance name (cold, water_meter...)
3.  **Add Camera to Dashboard:**
    *   Now you can add the camera to your dashboard as a card

## Usage

1.  **View Sensor Data:** The sensor entity will update automatically based on the configured scan interval. You can add it to your dashboards or use it in automations.
2.  **Use the Reboot Button:** Click the button to reboot the AIOTED device.
3.  **Trigger Services:**
    *   Go to **Developer Tools > Services**.
    *   Select the `aioted_manager.collect_data` or `aioted_manager.upload_data` service.
    *   Enter the `instance_name` in the data section.
    *   Click "Call Service."
4.  **Advanced Usage:**
    *   You can use the image in your dashboard.
    *   The integration saves all values in the `log.csv` file in the `www/aioted_manager/<instance_name>/` folder.

## Troubleshooting

*   **Cannot connect to AIOTED device:**
    *   Double-check the IP address.
    *   Ensure that the AIOTED device is powered on and connected to the network.
    *   Verify that the AIOTED device is running the correct software version.
*   **No data in Home Assistant:**
    *   Check the Home Assistant logs for errors related to `aioted_manager`.
    *   Ensure that the scan interval is not too high.
    *   Check the AIOTED device's log.
*   **Image upload fails:**
    *   Check the URL.
    *   Check the API key.
    *   Check the upload server log.

## Contributing

If you'd like to contribute to this project, feel free to:

*   Report issues or suggest features by opening an issue on the [GitHub repository](https://github.com/nliaudat/aioted_manager/issues).
*   Submit pull requests with bug fixes or improvements.

## License

This project is licensed under the [MIT License].

## Credits

*   This code was built using the AI-on-the-edge-device documentation: [https://jomjol.github.io/AI-on-the-edge-device-docs/REST-API/](https://jomjol.github.io/AI-on-the-edge-device-docs/REST-API/)
*   Thank you to all contributors!
