import re
import os
import json
import asyncio

import fire
import shutil
import requests
import time

from datetime import datetime


import ollama

# Configurable paths
source_folder = "./DATA/JSON_TO_PROCESS"
processed_folder = "./DATA/PROCESSED"
ai_crashed = "./DATA/AI_FAILED"
failed_folder = "./DATA/FAILED"

# Ensure processed folder exists
if not os.path.exists(source_folder):
    os.makedirs(source_folder)

if not os.path.exists(processed_folder):
    os.makedirs(processed_folder)

if not os.path.exists(failed_folder):
    os.makedirs(failed_folder)

if not os.path.exists(ai_crashed):
    os.makedirs(ai_crashed)


def get_youngest_file(folder):
    """Get the oldest file in the folder."""
    files = [os.path.join(folder, f) for f in os.listdir(folder) if f.endswith(".json")]
    if not files:
        return None
    youngest_file = max(files, key=os.path.getctime)
    return youngest_file


def get_oldest_file(folder):
    """Get the oldest file in the folder."""
    files = [os.path.join(folder, f) for f in os.listdir(folder) if f.endswith(".json")]
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
        response = requests.post(url, json=data, verify=False)
        response.raise_for_status()
        print(f"Callback to {url} successful: {response.status_code}")

        return True
    except requests.exceptions.RequestException as e:
        print(f"Failed to callback {url}: {e}")

    return False


def upload_file(json_file):
    try:
        with open(json_file, "r") as f:
            data = json.load(f)

            result_ok = callback_url(data["callback_url"], data)
            if result_ok:
                shutil.move(
                    json_file,
                    os.path.join(processed_folder, os.path.basename(json_file)),
                )
            else:
                shutil.move(
                    json_file, os.path.join(failed_folder, os.path.basename(json_file))
                )

        print(f"Result saved to file: {json_file}")

    except Exception as e:

        print(f"Failed to save result to file {json_file}: {e}")

        os.remove(json_file)  # Delete the file if it can't be saved
        print(f"Deleted file due to save error: {json_file}")


def kill_llama():
    import time
    import psutil
    import signal

    cmdline_pattern = [
        "/home/jupyter/LLAMA/venv/bin/python3",
        "/home/jupyter/LLAMA/venv/bin/llama",
        "inference",
        "start",
    ]
    for process in psutil.process_iter(["pid", "cmdline"]):
        cmdline = process.info["cmdline"]
        if cmdline == cmdline_pattern:
            print(
                f"Found llama process: PID = {process.info['pid']}, Command Line: {' '.join(cmdline)}"
            )
            os.kill(process.info["pid"], signal.SIGKILL)
            # process.terminate()  # Gracefully terminate
            # process.wait()       # Wait for process to be terminated

    count = 5
    while count > 0:
        print("..WAIT.. " + str(count))
        count -= 1
        time.sleep(10)


def main(host: str, port: int):
    # Loop through the folder and process the oldest JSON file
    # Get the oldest JSON file

    json_file = get_oldest_file(failed_folder)
    if json_file:
        upload_file(json_file)

    json_file = get_youngest_file(source_folder)
    if not json_file:
        print("No JSON files to process.")
        return

    # Load the JSON data
    try:
        with open(json_file, "r") as f:
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

    print(f" FILE TO PROCESS {json_file}")

    message = "Ignore any text about cookies or website errors " + data["message"]

    result = None
    try:

        response = ollama.chat(
            model="llama3.1",
            messages=[
                {
                    "role": "user",
                    "content": message,
                },
            ],
        )
        # Process the message using the run_main function

        result = response["message"]["content"]
        result = re.sub(r"(?i)summary.*(text|article).*markdown.*facts[:\s]*", "", result)

        print(f" *** {result}")

    except Exception as e:
        shutil.move(json_file, os.path.join(ai_crashed, os.path.basename(json_file)))

        print(f"Failed to contact inference {json_file}: {e}")
        # kill_llama()

    if not result:
        print(f"NO RESULT {json_file}")
        shutil.move(json_file, os.path.join(ai_crashed, os.path.basename(json_file)))
        return

    # Add the result to the JSON data
    data["result"] = str(result).replace("StepType.inference> ", "")

    # Callback with the updated data
    try:
        with open(json_file, "w") as f:
            json.dump(data, f, indent=4)

        upload_file(json_file)

    except Exception as e:
        print(f"Failed to save result to file {json_file}: {e}")


if __name__ == "__main__":
    fire.Fire(main)
