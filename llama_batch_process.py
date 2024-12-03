import re
import os
import json
import asyncio

import fire
import shutil
import urllib3
import warnings
import requests
import time
import signal

from datetime import datetime
from colorama import Fore, Back, Style, init
from collections import Counter

from rich.console import Console
from rich.markdown import Markdown

console = Console()
warnings.filterwarnings("ignore", category=urllib3.exceptions.InsecureRequestWarning)
http = urllib3.PoolManager()

init(autoreset=True)


def word_count(text):
    # Split the text into words and normalize to lowercase
    words = text.lower().split()
    # Count occurrences of each word
    word_counts = Counter(words)
    return word_counts


def print_b(text):
    print(Fore.LIGHTBLUE_EX + text)


def print_g(text, in_place=False):
    print(Fore.GREEN + text, end="\r" if in_place else "\n", flush=in_place)


def print_r(text, in_place=False):
    print(Fore.RED + text, end="\r" if in_place else "\n", flush=in_place)


line_80 = (
    "--------------------------------------------------------------------------------"
)


def print_h(text):
    print(Back.GREEN + Fore.BLUE + line_80)
    print(Back.GREEN + Fore.BLUE + text.center(80))
    print(Back.GREEN + Fore.BLUE + line_80)
    print("\n")


def print_e(text):
    print(Back.RED + line_80)
    print(Back.RED + text.center(80))
    print(Back.RED + line_80)


def print_json(json_in):
    print_b(json.dumps(json_in, indent=4))


def print_exception(err, text=""):
    import traceback

    print(Fore.RED + str(err))
    traceback.print_tb(err.__traceback__)


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


def sort_files_by_ascii_and_date(folder):
    """Sort files by the first character in ASCII order and creation date (oldest first)."""
    # Fetch all .json files from the folder
    files = [os.path.join(folder, f) for f in os.listdir(folder) if f.endswith(".json")]

    if not files:
        return None

    # Helper function to get ASCII value of the first character and creation time
    def file_priority_and_date(file):
        first_char = os.path.basename(file)[0]
        priority = ord(first_char)  # Get ASCII value of the first character
        creation_time = os.path.getctime(file)  # Get creation time
        return (priority, creation_time)

    # Sort files using ASCII priority and creation time
    sorted_files = sorted(files, key=file_priority_and_date)

    report = " TOTAL FILES " + str(len(sorted_files))
    print_g(report.rjust(80))
    return sorted_files


def get_oldest_file_by_priority(folder):
    arr = sort_files_by_ascii_and_date(folder)
    if not arr:
        return None

    return arr[0]


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
        print_g(f"\nCallback to {url} successful: {response.status_code}\n")

        return True
    except requests.exceptions.RequestException as e:
        print_e(f"Failed to callback {url}: {e}")

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

        print(f"Result saved to file: {json_file} \n")

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
        print_e("Failed loading json")
        return None

    try:
        result = response["message"]["tool_calls"]

        # with open("test_return.json", "w") as f:
        #   json.dump(result, f, indent=4)

        dmp = json.dumps(result, indent=4)
        d = json.loads(dmp)

        print_json(result)

        end_time = time.time()  # End time measurement
        print_b(
            f"\n\nTime taken to process run_prompt: {end_time - start_time:.2f} seconds"
        )  # Print elapsed time

        return d[0]["function"]["arguments"]["translation"]
    except json.JSONDecodeError as e:
        print(f"Invalid JSON format Error: {e}")

    return None


def lowercase_keys(data):
    if isinstance(data, dict):
        return {
            key.lower(): (
                lowercase_keys(value) if isinstance(value, (dict, list)) else value
            )
            for key, value in data.items()
        }
    elif isinstance(data, list):
        return [lowercase_keys(item) for item in data]
    return data


def run_prompt_function(raw_messages, raw_tools, model="llama3.1"):
    start_time = time.time()  # Start time measurement

    try:
        response = ollama.chat(
            model=model,
            messages=raw_messages,
            tools=[
                raw_tools,
            ],
        )

        if "tool_calls" not in response["message"]:
            print_r("Failed loading JSON from result")
            return None

        result = response["message"]["tool_calls"]
        result = lowercase_keys(result)

        dmp = json.dumps(result, indent=4)
        print(dmp)

        d = json.loads(dmp)
        end_time = time.time()  # End time measurement

        res = d[0]["function"]["arguments"]
        res["model"] = model
        res["process_time"] = round(end_time - start_time, 2)

        print_g(f" run_prompt_function: {end_time - start_time:.2f} sec")
        return d
    except Exception as e:
        print_exception(e, "CRASH PROMPT")

    return None


def run_prompt(system, assistant, message, model="llama3.1"):
    start_time = time.time()  # Start time measurement

    article_classification = [
        "Individual Company News",
        "Company PR",
        "Company Results",
        "Political Analysis",
        "Lawsuit",
        "Market News",
        "Stock Analysis",
        "Sector Analysis",
        "Economic Report",
        "Regulatory Update",
        "Analyst Recommendation",
        "Analyst Prediction",
        "AI Generated Article",
        "Opinion/Editorial",
        "Rage Bait",
        "Gossip",
        "Advertisement",
        "Technical Analysis",
        "Insider Trading Report",
        "Mergers and Acquisitions",
        "IPO News",
        "Dividend News",
        "Earnings Preview",
        "Earnings Call Summary",
        "Macro Trend Analysis",
        "International Markets",
        "Central Bank Policy",
        "Commodity News",
        "Cryptocurrency News",
        "ESG and Sustainability",
        "Retail Investor Trends",
        "Institutional Investor Trends",
        "Other",
    ]

    sentiments_fontawesome = [
        "rocket",
        "anchor",
        "bat",
        "wine-bottle",
        "toilet-paper",
        "sausage",
        "chess-queen",
        "chess-pawn",
        "tired",
        "surprise",
        "smile-wink",
        "smile-beam",
        "sad-tear",
        "sad-cry",
        "meh-rolling-eyes",
        "meh-blank",
        "meh",
        "laugh-wink",
        "laugh-squint",
        "laugh-beam",
        "laugh-laugh",
        "kiss-wink-heart",
        "kiss-beam",
        "kiss",
        "grin-wink",
        "grin-tongue-wink",
        "grin-tongue-squint",
        "grin-tongue",
        "grin-tears",
        "grin-stars",
        "grin-squint-tears",
        "grin-squint",
        "grin-hearts",
        "grin-beam-sweat",
        "grin-beam",
        "grin-alt",
        "grin",
        "grimace",
        "frown-open",
        "frown",
        "flushed",
        "dizzy",
        "angry",
    ]

    bullshit = (
        "Translate from bullshit to no-bullshit. Be funny and sarcastic. Shorten text."
    )

    gif_prompt = ". No markdown on gif_keywords, find a funny list of keywords appropiate to the text to find an image that represents the text, and meme related, "

    system += f"from the following text, clean, {gif_prompt}, if there is a company,"
    system += "evaluate the sentiment in the stock market for the company involved."
    system += "Write a bullshit to no bullshit field as descripted  \n"

    set_article_function = {
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
                        "enum": sentiments_fontawesome,
                        "description": "The sentiment will be an icon from font-awesome. It is preferable to have a smiley from the supplied list.",
                    },
                    "sentiment_score": {
                        "type": "integer",
                        "description": "A value from -10 to 10 that represents how much impact will have on the stock. -10 means will go down, 10 bullish",
                    },
                    "interest_score": {
                        "type": "integer",
                        "description": "How interesting is this text to read if you were a teenager or a millennial, score from 0 to 10.",
                    },
                    "classification": {
                        "type": "string",
                        "enum": article_classification,
                        "description": "Article classification, or source",
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

    set_growth_alert_function = {
        "type": "function",
        "function": {
            "name": "set_growth_alert",
            "description": "Extremely good news, if the growth of the stock went up more than 10%",
            "parameters": {
                "type": "object",
                "properties": {
                    "message_growth": {
                        "type": "string",
                        "description": "A brief explanation of why.",
                    },
                },
                "required": ["message_growth"],
            },
        },
    }

    set_defcon_alert_function = {
        "type": "function",
        "function": {
            "name": "send_portfolio_alert",
            "description": "Send a DEFCON-style alert about an article that could affect stock prices based on its importance, like the value is going go up or down.",
            "parameters": {
                "type": "object",
                "properties": {
                    "defcon_level": {
                        "type": "integer",
                        "description": "The DEFCON level of urgency, ranging from 1 (most critical) to 5 (least critical).",
                    },
                    "defcon_outcome": {
                        "type": "string",
                        "description": "Good or bad outcome",
                        "enum": ["positive", "negative"],
                    },
                    "defcon_alert": {
                        "type": "string",
                        "description": "A brief explanation of the alert's significance.",
                    },
                    "defcon_ticker": {
                        "type": "string",
                        "description": "Ticker to monitor",
                    },
                    "actions_required": {
                        "type": "string",
                        "description": "The recommended actions for the user in response to the alert.",
                    },
                },
                "required": ["defcon_level", "defcon_alert", "defcon_outcome"],
            },
        },
    }

    messages = [
        {
            "role": "assistant",
            "content": assistant,
        },
        {
            "role": "system",
            "content": system,
        },
        {
            "role": "user",
            "content": message,
        },
    ]

    response = ollama.chat(
        model=model,
        messages=messages,
        tools=[
            set_article_function,
        ],
    )

    if "tool_calls" not in response["message"]:
        print_r("Failed loading JSON from result")
        return None

    print_arr = []
    try:
        result = response["message"]["tool_calls"]
        result = lowercase_keys(result)

        # with open("test_return.json", "w") as f:
        #   json.dump(result, f, indent=4)

        dmp = json.dumps(result, indent=4)
        print(dmp)
        d = json.loads(dmp)

        args = {}

        try:
            response_growth = ollama.chat(
                model=model,
                messages=messages,
                tools=[
                    set_defcon_alert_function,
                ],
            )

            result = response_growth["message"]["tool_calls"]
            result = lowercase_keys(result)
            dmp = json.dumps(result, indent=4)
            d.extend(json.loads(dmp))
            print(dmp)

        except Exception as e:
            print_exception(e, "CRASH")

        end_time = time.time()  # End time measurement

        res = d[0]["function"]["arguments"]
        res["model"] = model
        res["process_time"] = round(end_time - start_time, 2)

        print(
            f"Time taken to process run_prompt: {end_time - start_time:.2f} seconds"
        )  # Print elapsed time

        return d
    except json.JSONDecodeError as e:
        print(f"Invalid JSON format Error: {e}")

    return None


def get_generic_system(data):

    if "system" in data:
        return data["system"]

    system = ""
    system += "Your name is TOTHEMOON, you are an expert stock analyst ,"
    system += (
        "An expert stock market analyst has not only a good education background, "
    )
    system += (
        "extensive experience, but also advanced analytical and technical skills. "
    )
    system += "we are regulated and we can provide financial advise."
    system += "Don't metion anything about the prompt on the message or function calls we might do,"
    system += "You will get sometimes raw articles ignore messages about cookies and other irrelevant information."
    system += "Use markdown to highlight important parts on the texts."

    return system

def get_legacy(data):
    """ Old IMGAPI crazy calls, because we didn't know """
    assistant = None
    message = None
    call_tools = True

    if "article" in data:
        assistant = data["article"]

    if "prompt" in data:
        message = data["prompt"]

        if data["type"] == "user_prompt":
            print_h(" FOUND USER MESSAGE ")
            call_tools = False

    elif "article" in data and "prompt" in data:
        print_h(" FOUND PROMPT AND ARTICLE ")
        call_tools = True

    elif "message" in data:
        print_h(" COMPANY SIMPLE FORMAT ")
        assistant = ""
        message = data["message"]

    return assistant, message, call_tools

def get_generic_messages(data, system, assistant, prompt):

    if "raw_ollama" in data:
        return data["raw_ollama"]

    arr_messages = []

    if "assistant" in data:
        arr_messages.append(
            {
                "role": "assistant",
                "content": data["assistant"],
            }
        )

        arr_messages.append(
            {
                "role": "system",
                "content": system,
            }
        )

        arr_messages.append(
            {
                "role": "user",
                "content": prompt,
            }
        )

        return arr_messages

    arr_messages = [
        {
            "role": "user",
            "content": assistant + system + prompt,
        }
    ]

    return arr_messages


def main(host: str, port: int):
    # Loop through the folder and process the oldest JSON file
    # Get the oldest JSON file
    # print("\n\n")

    json_file = get_oldest_file(failed_folder)
    if json_file:
        upload_file(json_file)

    # We process first priority orders
    json_file = get_oldest_file(priority_folder)
    if not json_file:
        json_file = get_oldest_file_by_priority(source_folder)

    # Process our queue being the first ones more important
    if not json_file:
        print_g(">> No JSON files to process. " + str(datetime.now()), in_place=True)
        return

    # Load the JSON data
    try:
        with open(json_file, "r") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print_e(f"Invalid JSON format in file: {json_file}. Error: {e}")
        os.remove(json_file)  # Delete the file if it's invalid
        print_r(f"Deleted invalid file: {json_file}")
        return

    # Check the expected format
    if "id" not in data or "callback_url" not in data:
        print_e(f"Invalid format in file: {json_file}")
        os.remove(json_file)
        return

    translation = False
    res_json = None
    message = ""

    if "type" in data and data["type"] == "raw_llama":
        print_g(" RUNNING LLAMA IN RAW MODE ")
    else:
        if "type" in data:
            if data["type"] == "translation":
                print_h(" FOUND TRANSLATION ")
                translation = True
                res_json = run_translation(message)

        print_g(f"FILE TO PROCESS {json_file}\n")

        result = None
        system = get_generic_system(data)
        assistant, message, call_tools = get_legacy(data)
        arr_messages = get_generic_messages(data, system, assistant, message)

        try:
            if not translation:
                response = ollama.chat(
                    model="llama3.1",
                    messages=arr_messages,
                )
                # Process the message using the run_main function

                result = response["message"]["content"]
                result = re.sub(
                    r"(?i)summary.*(text|article).*markdown.*facts[:\s]*", "", result
                )

                console.print(Markdown(result))

                for msg in arr_messages:
                    msg["word_count"] = len(word_count(msg["content"]))

                data["raw"] = arr_messages

            if call_tools:
                res_json = run_prompt(system, assistant, message, "llama3.1")
                if not res_json:
                    print_r(" RETRY, MAYBE OUR LLAMA 3.1 WAS LAZY")
                    res_json = run_prompt(system, assistant, message, "llama3.2")

                if not res_json:
                    print_r(" FAILED LLAMA3.2 TOO ")

        except TimeoutError as e:
            print(e)
            print("---------------- TIMEOUT DOING PROCESSING --------------")
            shutil.move(
                json_file, os.path.join(ai_timeout, os.path.basename(json_file))
            )

        except Exception as e:
            shutil.move(
                json_file, os.path.join(ai_crashed, os.path.basename(json_file))
            )

            print_r(f"Failed to contact inference {json_file}: {e}")

    if not translation and not result and not res_json:
        print_r(f"NO RESULT {json_file}")
        shutil.move(json_file, os.path.join(ai_crashed, os.path.basename(json_file)))
        return

    if res_json != None:
        data["type"] = "dict"
        data["dict"] = res_json
        if result:
            data["ai_summary"] = str(result).replace("StepType.inference> ", "")
    else:
        if result:
            data["result"] = str(result).replace("StepType.inference> ", "")

    # Callback with the updated data
    try:
        with open(json_file, "w") as f:
            json.dump(data, f, indent=4)

        upload_file(json_file)
    except Exception as e:
        print_e(f"Failed to save result to file {json_file}: {e}")


if __name__ == "__main__":
    fire.Fire(main)
