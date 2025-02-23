# AI on the Edge Device  Meter Collector Integration for Home Assistant

This guide will walk you through the steps to install and configure the **"AI on the Edge device manager"** custom integration in Home Assistant.

## Installation

1. **Copy the Integration Folder:**
   - Download or clone the `AIOTED-hassio` custom component.
   - Copy the `AIOTED-hassio` folder into your Home Assistant `custom_components` directory.

2. **OPTIONAL : Set Permissions:**
   - Ensure the folder and files have the correct permissions (755).
     ```bash
     chmod -R 755 /homeassistant/custom_components/AIOTED-hassio
     ```

3. **Reboot Home Assistant:**
   - Restart Home Assistant (Hassio) to load the new integration.
     - You can do this via the **Settings > System > Restart** option in the Home Assistant UI.

4. **Add the Integration:**
   - Go to **Settings > Devices & Services > Integrations**.
   - Click **Add Integration** and search for **"AI on the Edge device manager"**.
   - Follow the prompts to configure the integration.

---

## Configuration

Once the integration is added, you will need to configure it with the following options:

### Required Configuration:
- **Instance**: A unique name for your sensor that must correspond to your "Number Sequence" name (e.g., `cold`).
- **IP**: The URL to fetch the meter value.
- Optional Configuration: </br>
    **Scan Interval**: The time interval (in seconds) at which the integration will poll the meter for updates. Default is 300 seconds (5min).
  
    **log_as_csv**: log events in homeassistant\www\AIOTED-hassio\{instance}
  
    **save_images**: save all changed images in homeassistant\homeassistant\www\AIOTED-hassio\{instance}
  
