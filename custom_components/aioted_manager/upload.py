import os
import zipfile
import logging
import aiohttp
from datetime import datetime
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util.dt import now
import asyncio

_LOGGER = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_DELAY = 5

def create_zip_file(image_dir, zip_dir, instance_name):
    """
    Creates a zip file containing all images from the specified directory.
    """
    # Ensure the zip directory exists
    os.makedirs(zip_dir, exist_ok=True)

    # Create a zip file with a timestamp in the name
    timestamp = now().strftime("%Y%m%d_%H%M%S")
    zip_filename = os.path.join(zip_dir, f"{instance_name}_images_{timestamp}.zip")

    # Create the zip file
    with zipfile.ZipFile(zip_filename, 'w') as zipf:
        for root, _, files in os.walk(image_dir):
            for file in files:
                file_path = os.path.join(root, file)
                zipf.write(file_path, os.path.relpath(file_path, image_dir)) # Use os.path.relpath to only include the filename

    _LOGGER.info(f"Created zip file: {zip_filename}")
    return zip_filename

async def upload_zip_file(hass, zip_file_path, upload_url, api_key, instance_name):
    """Uploads a zip file to the specified URL with retry logic."""
    retries = 0
    headers = {
        "X-API-Key": api_key,
        "instance_name": instance_name,
    }
    while retries < MAX_RETRIES:
        try:
            session = async_get_clientsession(hass)
            with open(zip_file_path, "rb") as f:
                data = aiohttp.FormData()
                data.add_field("file", f, filename=os.path.basename(zip_file_path))
                async with session.post(upload_url, data=data, headers=headers) as response:
                    if response.status == 200:
                        text = await response.text()
                        if "OK" not in text:
                            _LOGGER.error(f"Upload failed: Server responded with {text}")
                            raise ValueError(f"Server response: {text}")
                        _LOGGER.info(f"Uploaded {zip_file_path} successfully.")
                        return True
                    else:
                        response_text = await response.text()
                        _LOGGER.error(f"Upload failed with status {response.status}: {response_text}")
                        raise aiohttp.ClientResponseError(response.request_info, response.history, status=response.status)
        except (aiohttp.ClientError, ValueError, aiohttp.ClientResponseError) as e:
            _LOGGER.error(f"Attempt {retries + 1}/{MAX_RETRIES} failed to upload {zip_file_path}: {str(e)}")
            retries += 1
            if retries < MAX_RETRIES:
                _LOGGER.info(f"Retrying in {RETRY_DELAY} seconds...")
                await asyncio.sleep(RETRY_DELAY)
    _LOGGER.error(f"Failed to upload {zip_file_path} after {MAX_RETRIES} retries.")
    return False

async def daily_upload_task(hass, www_dir, upload_url, api_key, instance_name):
    """
    Performs the daily upload task: zips images and uploads the zip file.
    """
    zip_dir = os.path.join(www_dir, "zip")
    try:
        # Step 1: Create the zip file in an executor thread
        zip_file_path = await hass.async_add_executor_job(
            create_zip_file, www_dir, zip_dir, instance_name
        )

        # Step 2: Upload the zip file
        upload_success = await upload_zip_file(hass, zip_file_path, upload_url, api_key, instance_name)

        # Clean up the zip file after upload only if successful
        if upload_success:
            await hass.async_add_executor_job(os.remove, zip_file_path)
            _LOGGER.info(f"Deleted {zip_file_path} after successful upload.")
        else:
            _LOGGER.error(f"Upload failed, {zip_file_path} not deleted.")
    except Exception as e:
        _LOGGER.error(f"An error occurred during daily upload task: {e}")
