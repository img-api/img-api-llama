import re
import os
import json
import asyncio

import fire
import shutil
import requests
import time
import signal

from datetime import datetime

def timeout_handler(signum, frame):
    raise TimeoutError("Program took too long to execute!")

signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(50)  # Set the alarm for 50 seconds

import ollama

# Configurable paths
source_folder = "./DATA/JSON_TO_PROCESS"
priority_folder = "./DATA/JSON_TO_PROCESS_PRIORITY"

processed_folder = "./DATA/PROCESSED"
ai_crashed = "./DATA/AI_FAILED"
ai_timeout = "./DATA/AI_TIMEOUT"
failed_folder = "./DATA/FAILED"

# Ensure processed folder exists
if not os.path.exists(priority_folder):
    os.makedirs(priority_folder)

if not os.path.exists(ai_timeout):
    os.makedirs(ai_timeout)

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


def run_translation(prompt):
    start_time = time.time()  # Start time measurement
    response = ollama.chat(
        model="llama3.1",
        messages=[{"role": "user", "content": prompt}],
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "set_translation",
                    "description": "As an expert native and professional translator, transcribe the text adjusted to the locale required.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "translation": {
                                "type": "string",
                                "description": "result of the translation",
                            },
                            "editor_comments": {
                                "type": "string",
                                "description": "Any comments on the transcript",
                            },
                        },
                        "required": [
                            "translation",
                            "editor_comments",
                        ],
                    },
                },
            }
        ],
    )

    if "tool_calls" not in response["message"]:
        print("Failed loading json")
        return None

    try:
        result = response["message"]["tool_calls"]

        # with open("test_return.json", "w") as f:
        #   json.dump(result, f, indent=4)

        dmp = json.dumps(result, indent=4)
        print(dmp)

        d = json.loads(dmp)

        end_time = time.time()  # End time measurement
        print(
            f"Time taken to process run_prompt: {end_time - start_time:.2f} seconds"
        )  # Print elapsed time

        return d[0]['function']['arguments']['translation']
    except json.JSONDecodeError as e:
        print(f"Invalid JSON format Error: {e}")

    return None

def lowercase_keys(d):
    if isinstance(d, dict):
        return {key.lower(): lowercase_keys(value) if isinstance(value, dict) else value for key, value in d.items()}
    return d

def run_prompt(system, assistant, message, model="llama3.1"):
    start_time = time.time()  # Start time measurement

    bullshit = (
        "Translate from bullshit to no-bullshit. Be funny and sarcastic. Shorten text."
    )

    gif_prompt = ". No markdown on gif_keywords, find a funny list of keywords appropiate to the text to find an image that represents the text, and meme related, "

    system += f"from the following text, clean, {gif_prompt}, if there is a company,"
    system += "evaluate the sentiment in the stock market for the company involved."
    system += "Write a bullshit to no bullshit field as descripted  \n"

    response = ollama.chat(
        model=model,
        messages=[
            {
                "role": "system",
                "content": system,
            },
            {
                "role": "user",
                "content": assistant + " " + message,
            },
        ],
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "set_article_information",
                    "description": "Set all the information about the text provided",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "gif_keywords": {
                                "type": "string",
                                "description": "use the sentiment to create a list of human emotions, no markdown, only comma separated list",
                            },
                            "title": {
                                "type": "string",
                                "description": "a one line title describing the text",
                            },
                            "paragraph": {
                                "type": "string",
                                "description": "a one paragraph, not long text. This should be a small very short summary to display as a note",
                            },
                            "summary": {
                                "type": "string",
                                "description": "a two to three paragraph summary",
                            },
                            "no_bullshit": {
                                "type": "string",
                                "description": bullshit,
                            },
                            "sentiment": {
                                "type": "string",
                                "enum": ["positive", "negative", "neutral"],
                                "description": "The sentiment positive, negative, neutral",
                            },
                            "sentiment_score": {
                                "type": "integer",
                                "description": "A value from -10 to 10 that represents how much impact will have on the stock. -10 means will go down, 10 bullish",
                            },
                            "interest_score": {
                                "type": "integer",
                                "description": "How interesting is this text to read, score from 0 to 10.",
                            },
                        },
                        "required": [
                            "paragraph",
                            "sentiment",
                            "title",
                            "summary",
                            "no_bullshit",
                            "gif_keywords",
                            "interest_score",
                        ],
                    },
                },
            }
        ],
    )

    if "tool_calls" not in response["message"]:
        print("Failed loading json")
        return None

    try:
        result = response["message"]["tool_calls"]
        result = lowercase_keys(result)

        # with open("test_return.json", "w") as f:
        #   json.dump(result, f, indent=4)

        dmp = json.dumps(result, indent=4)
        print(dmp)

        d = json.loads(dmp)

        args = d[0]['function']['arguments']
        end_time = time.time()  # End time measurement

        args['model'] = model
        args['process_time'] = round(end_time - start_time, 2)

        print(
            f"Time taken to process run_prompt: {end_time - start_time:.2f} seconds"
        )  # Print elapsed time

        return d
    except json.JSONDecodeError as e:
        print(f"Invalid JSON format Error: {e}")

    return None


def main(host: str, port: int):
    # Loop through the folder and process the oldest JSON file
    # Get the oldest JSON file

    json_file = get_oldest_file(failed_folder)
    if json_file:
        upload_file(json_file)

    # We process first priority orders
    json_file = get_oldest_file(priority_folder)
    if not json_file:
        json_file = get_youngest_file(source_folder)

    # Process our queue being the first ones more important
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
    if "id" not in data or "callback_url" not in data:
        print(f"Invalid format in file: {json_file}")
        os.remove(json_file)
        return

    print(f" FILE TO PROCESS {json_file}")

    translation = False
    call_tools = False

    if "article" in data:
        assistant = data["article"]

    if "prompt" in data:
        message = data["prompt"]

    if "type" in data and data["type"] == "translation":
        print("--------------------------------------------------------------------")
        print(" FOUND TRANSLATION ")
        print("--------------------------------------------------------------------")
        translation = True

    elif "type" in data and data["type"] == "user_prompt":
        print("--------------------------------------------------------------------")
        print(" FOUND USER MESSAGE ")
        print("--------------------------------------------------------------------")
        call_tools = False

    elif "article" in data and "prompt" in data:
        print("--------------------------------------------------------------------")
        print(" FOUND PROMPT AND ARTICLE ")
        print("--------------------------------------------------------------------")
        call_tools = True

    elif "message" in data:
        print("--------------------------------------------------------------------")
        print(" COMPANY SIMPLE FORMAT ")
        print("--------------------------------------------------------------------")
        assistant = ""
        message = data["message"]

    result = None
    res_json = None

    system = ""
    system += "You are an expert stock analyst ,"
    #system += "An expert stock market analyst has not only a good education background, "
    #system += "extensive experience, but also advanced analytical and technical skills. "
    system += "can provide financial advise as far as you specify at the end that this is not financial advice."
    system += "Don't metion anything about the prompt on the message or function calls we might do,"
    system += "ignore messages about cookies and don't mention them."
    system += "Use markdown to highlight important parts on the texts."

    try:
        if translation:
            res_json = run_translation(message)
        else:
            response = ollama.chat(
                model="llama3.1",
                messages=[
                    {
                        "role": "system",
                        "content": system,
                    },
                    {
                        "role": "user",
                        "content": assistant,
                    },
                    {
                        "role": "user",
                        "content": assistant + message,
                    },
                ],
            )
            # Process the message using the run_main function

            result = response["message"]["content"]
            result = re.sub(
                r"(?i)summary.*(text|article).*markdown.*facts[:\s]*", "", result
            )

            print(f" *** {result}")

        if call_tools:
            res_json = run_prompt(system, assistant, message, "llama3.1")
            if not res_json:
                print(message)
                print(" RETRY, MAYBE OUR LLAMA 3.1 WAS LAZY")
                res_json = run_prompt(system, assistant, message, "llama3.2")

            if not res_json:
                print(" FAILED LLAMA3.2 TOO ")

    except TimeoutError as e:
        print(e)
        print("---------------- TIMEOUT DOING PROCESSING --------------")
        shutil.move(json_file, os.path.join(ai_timeout, os.path.basename(json_file)))

    except Exception as e:
        shutil.move(json_file, os.path.join(ai_crashed, os.path.basename(json_file)))

        print(f"Failed to contact inference {json_file}: {e}")
        # kill_llama()

    if not translation and not result:
        print(f"NO RESULT {json_file}")
        shutil.move(json_file, os.path.join(ai_crashed, os.path.basename(json_file)))
        return

    # Add the result to the JSON data

    if res_json != None:
        if result:
            data["ai_summary"] = str(result).replace("StepType.inference> ", "")

        data["dict"] = res_json
        data["type"] = "dict"
    else:
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
