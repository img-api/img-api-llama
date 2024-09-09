import os
import json
import asyncio

import fire
import shutil
import requests
import time

from datetime import datetime
from llama_models.llama3_1.api.datatypes import Attachment, URL, UserMessage
from multi_turn import prompt_to_message, run_main

# Configurable paths
source_folder = "./DATA/JSON_TO_PROCESS"
processed_folder = "./DATA/PROCESSED"
failed_folder = "./DATA/FAILED"

# Ensure processed folder exists
if not os.path.exists(source_folder):
    os.makedirs(source_folder)

if not os.path.exists(processed_folder):
    os.makedirs(processed_folder)

if not os.path.exists(failed_folder):
    os.makedirs(failed_folder)


def get_oldest_file(folder):
    """Get the oldest file in the folder."""
    files = [
        os.path.join(folder, f) for f in os.listdir(folder)
        if f.endswith(".json")
    ]
    if not files:
        return None
    oldest_file = min(files, key=os.path.getctime)
    return oldest_file


def update_file_timestamp(filepath):
    """Touch the file to update its timestamp, making it the 'youngest'."""
    os.utime(filepath, None)


def callback_url(url, data):
    """Send a callback to the URL with the processed data."""
    try:
        response = requests.post(url, json=data)
        response.raise_for_status()
        print(f"Callback to {url} successful: {response.status_code}")

        return True
    except requests.exceptions.RequestException as e:
        print(f"Failed to callback {url}: {e}")

    return False


def main(host: str, port: int):
    # Loop through the folder and process the oldest JSON file
    # Get the oldest JSON file

    json_file = get_oldest_file(source_folder)
    if not json_file:
        print("No JSON files to process.")
        return

    # Load the JSON data
    try:
        with open(json_file, 'r') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Invalid JSON format in file: {json_file}. Error: {e}")
        os.remove(json_file)  # Delete the file if it's invalid
        print(f"Deleted invalid file: {json_file}")
        return

    # Check the expected format
    if "id" not in data or "message" not in data or "callback_url" not in data:
        print(f"Invalid format in file: {json_file}")
        os.remove(json_file)
        return

    message = data["message"]

    # Process the message using the run_main function
    result = asyncio.run(
        run_main(
            [
                prompt_to_message(message),
            ],
            host=host,
            port=port,
            disable_safety=True,
        ))

    # Add the result to the JSON data
    data["result"] = str(result).replace("StepType.inference> ", "")

    # Callback with the updated data
    result_ok = callback_url(data["callback_url"], data)

    # Save the updated JSON data back to the same file
    try:
        with open(json_file, 'w') as f:
            json.dump(data, f, indent=4)

        if result_ok:
            shutil.move(
                json_file,
                os.path.join(processed_folder, os.path.basename(json_file)))
        else:
            shutil.move(
                json_file,
                os.path.join(failed_folder, os.path.basename(json_file)))

        print(f"Result saved to file: {json_file}")
    except Exception as e:
        print(f"Failed to save result to file {json_file}: {e}")
        os.remove(json_file)  # Delete the file if it can't be saved
        print(f"Deleted file due to save error: {json_file}")


if __name__ == "__main__":
    fire.Fire(main)
