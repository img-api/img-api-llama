import re
import os
import ast
import json
import asyncio
import threading

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

from .files import get_oldest_file, load_json_file, api_file_move, upload_file
from .paths import PATHS, source_folder, processing_folder, failed_folder, priority_folder, rejected_folder, ai_crashed, ai_timeout
from .printer import print_b, print_g, print_r, print_w, print_e, print_exception, print_json, print_h, line_80


console = Console()
warnings.filterwarnings("ignore", category=urllib3.exceptions.InsecureRequestWarning)
http = urllib3.PoolManager()

init(autoreset=True)

NUM_CTX = 55000
MODEL = "llama3.1"
VALID_HOSTNAMES = ["gputop-dev-machine-20240829-103727"]

BEXIT = False


def word_count(text):
    # Split the text into words and normalize to lowercase
    words = text.lower().split()
    # Count occurrences of each word
    word_counts = Counter(words)
    return word_counts


def timeout_handler(signum, frame):
    raise TimeoutError("Program took too long to execute!")


signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(300)  # Set the alarm for 50 seconds


def count_time():
    global BEXIT
    """Function to count time and print elapsed seconds."""
    start_time = time.time()
    while BEXIT:
        elapsed_time = int(time.time() - start_time)
        print_g(f"Elapsed time: {elapsed_time} seconds", in_place=True)
        time.sleep(1)  # Update every second


# Create and start the thread
# timer_thread = threading.Thread(target=count_time)
# timer_thread.start()


import ollama


# Ensure processed folder exists
for folder in PATHS:
    if not os.path.exists(folder):
        os.makedirs(folder)


def fix_array(company_list):
    """
    Checks if the input is a string representation of a list or an actual list.
    Converts it to a proper Python list if necessary.

    Args:
        company_list (str or list): The input to be checked and fixed.

    Returns:
        list: A properly formatted Python list.
    """
    if not company_list:
        return []

    if isinstance(company_list, str):
        try:
            # Try to safely evaluate the string as a list
            parsed_list = ast.literal_eval(company_list)
            if isinstance(parsed_list, list):
                return parsed_list
        except (ValueError, SyntaxError):
            pass
        # If parsing fails, wrap the string in a list
        return [company_list]

    elif isinstance(company_list, list):
        return company_list

    # If neither, raise an error
    raise TypeError("Input must be a string or a list.")


def fix_nested_lists(data):
    """
    Recursively traverses a dictionary and fixes any keys ending with '_list'.

    Args:
        data (dict): The dictionary to be traversed.

    Returns:
        dict: The dictionary with fixed list formats.
    """
    if isinstance(data, list):
        for obj in data:
            fix_nested_lists(obj)
        return obj

    if isinstance(data, dict):
        for key, value in data.items():
            if key.endswith("_list"):
                data[key] = fix_array(value)
                continue

            fix_nested_lists(value)
    return data


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
    print_g(report.rjust(80), in_place=True)
    return sorted_files


def get_oldest_file_by_priority(folder):
    arr = sort_files_by_ascii_and_date(folder)
    if not arr:
        return None

    return arr[0]


def update_file_timestamp(filepath):
    """Touch the file to update its timestamp, making it the 'youngest'."""
    os.utime(filepath, None)


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
        model=MODEL,
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

        dmp = json_serialize_toolcall(result)

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


def run_prompt_function(raw_messages, raw_tools, model=MODEL):
    start_time = time.time()  # Start time measurement

    try:
        response = ollama.chat(
            model=model,
            messages=raw_messages,
            tools=raw_tools,
            options={"num_ctx": NUM_CTX},
            keep_alive=1,
        )

        if "content" in response["message"]:
            result = response["message"]["content"]
            console.print(Markdown(result))

        if "tool_calls" not in response["message"]:
            print_r("Failed loading JSON from result")
            return None

        result = response["message"]["tool_calls"]

        dmp = json_serialize_toolcall(result)
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


def json_serialize_toolcall(result):

    serialz = []
    for tool in result:
        f = tool["function"]
        old_format = {
            "function": {
                "name": f["name"],
                "arguments": f["arguments"],
            }
        }
        serialz.append(old_format)

    fix_nested_lists(serialz)
    dmp = json.dumps(serialz, indent=4)

    return dmp

def run_company_tickers_extraction(message,  model):

    set_summary_info = {
        "type": "function",
        "function": {
            "name": "set_summary_info",
            "description": "Set all the information about the text provided",
            "parameters": {
                "type": "object",
                "properties": {
                    "tickers_list": {
                        "type": "array",
                        "description": "A list of the tickers found in the article",
                    },
                    "company_list": {
                        "type": "array",
                        "description": "A list of the company names found in the article, don't include tickers",
                    },
                },
                "required": [
                    "tickers_list",
                    "company_list",
                ],
            },
        },
    }

    system = f"You are an expert that knows the stock market and how tickers and companies names are structured."
    system += "You have great attention to detail and can highlight in text important and relevant information."

    message = "Text to find companies and highlight: " + message

    messages = [
        {
            "role": "system",
            "content": system,
        },
        {
            "role": "user",
            "content": message,
        },
    ]

    try:
        response_growth = ollama.chat(
            model=model,
            messages=messages,
            tools=[
                set_summary_info,
            ],
        )

        result = response_growth["message"]["tool_calls"]

        dmp = json_serialize_toolcall(result)
        print(dmp)
        return json.loads(dmp)

    except Exception as e:
        print_exception(e, "CRASH")

    return []

def run_prompt(system, assistant, message, model=MODEL):
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
        "Translate the article from bullshit to no-bullshit. Be funny and sarcastic. Short text."
    )

    gif_prompt = ". No markdown on gif_keywords, find a funny list of keywords appropiate to the text to find an image that represents the text, and meme related, "

    system += f"from the following text, clean, {gif_prompt}, if there is a company,"
    system += "evaluate the sentiment in the stock market for the company involved."

    system += "Write a bullshit to no bullshit field as descripted, you are sophisticated, "
    system += "don't use phrases like 'Let's get real, folks', 'No Bullshit:', 'Let's cut to the chase', 'TL;DR', 'Translation:' or anything that starts with let's or uses folks.\n"

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
                    "title_clickbait": {
                        "type": "string",
                        "description": "Build the most click bait title possible, to show how ridiculous they can get.",
                    },
                    "title": {
                        "type": "string",
                        "description": "a one line title describing the text",
                    },
                    "paragraph": {
                        "type": "string",
                        "description": "a one paragraph, not long text. This should be a small very short summary to display as a note",
                    },
                    "article_tickers_list": {
                        "type": "array",
                        "description": "A list of the tickers found in the article",
                    },
                    "article_company_list": {
                        "type": "array",
                        "description": "A list of the company names found in the article, don't include tickers",
                    },
                    "summary": {
                        "type": "string",
                        "description": "a two to three paragraph summary",
                    },
                    "no_bullshit": {
                        "type": "string",
                        "description": bullshit,
                    },
                    "interest_score": {
                        "type": "integer",
                        "description": "Score from 0 to 10. An interesting article captures the reader's attention and sustains their engagement. It includes the following characteristics, Relevance, Engaging Opening, Clear Purpose, Well-Researched Content.",
                    },
                    "classification": {
                        "type": "string",
                        "enum": article_classification,
                        "description": "Article classification, or source from the enumeration provided",
                    },
                },
                "required": [
                    "paragraph",
                    "article_tickers_list",
                    "article_company_list",
                    "title",
                    "summary",
                    "title_clickbait",
                    "classification",
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

    print_g(">> MODEL " + model + " NUM_CTX " + str(NUM_CTX))

    response = ollama.chat(
        model=model,
        messages=messages,
        tools=[
            set_article_function,
        ],
        options={"num_ctx": NUM_CTX},
    )

    if "tool_calls" not in response["message"]:
        print_r("Failed loading JSON from result")
        return None

    try:
        result = response["message"]["tool_calls"]

        # with open("test_return.json", "w") as f:
        #   json.dump(result, f, indent=4)

        dmp = json_serialize_toolcall(result)

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

            dmp = json_serialize_toolcall(result)

            d.extend(json.loads(dmp))
            print(dmp)

        except Exception as e:
            print_exception(e, "CRASH")

        try:
            response_growth = ollama.chat(
                model=model,
                messages=messages,
                tools=[
                    set_defcon_alert_function,
                ],
            )

            result = response_growth["message"]["tool_calls"]

            dmp = json_serialize_toolcall(result)

            d.extend(json.loads(dmp))
            print(dmp)

        except Exception as e:
            print_exception(e, "CRASH")

        try:

            set_sentiment_icon_function = {
                "type": "function",
                "function": {
                    "name": "set_sentiment_icon",
                    "description": "Sentiment calculation from the article",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "sentiment": {
                                "type": "string",
                                "description": "Just sentiment on the article ",
                            },
                            "article_icon": {
                                "type": "string",
                                "enum": sentiments_fontawesome,
                                "description": "Select from the enum an icon ",
                            },
                            "sentiment_score": {
                                "type": "integer",
                                "description": "A value from -10 to 10 that represents how much impact will have on the stock. -10 means will go down, 10 bullish",
                            },
                        },
                        "required": [
                            "sentiment",
                            "article_icon",
                            "sentiment_score",
                        ],
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
                    "content": "You are an expert web designer and you have to select icons for each article, provided is the article",
                },
                {
                    "role": "user",
                    "content": "Find the right icons to represent this article from this list: "
                    + str(sentiments_fontawesome),
                },
            ]

            # print(str(messages))
            response_growth = ollama.chat(
                model="llama3.1",
                messages=messages,
                tools=[
                    set_sentiment_icon_function,
                ],
            )

            result = response_growth["message"]["tool_calls"]

            dmp = json_serialize_toolcall(result)

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

    return """
    Your name is TOTHEMOON, you are an expert stock analyst ,
        An expert stock market analyst has not only a good education background,
        extensive experience, but also advanced analytical and technical skills.
        We are regulated and we can provide financial advise.
        Don't metion anything about the prompt on the message or function calls we might do,
        You will get sometimes raw articles ignore messages about cookies and other irrelevant information.
        Use markdown to highlight important parts on the texts.
    """


def get_legacy(data):
    """Old IMGAPI crazy calls, because we didn't know"""
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
            "content": str(assistant) + str(system) + str(prompt),
        }
    ]

    return arr_messages


def api_update_stats(total_time):
    stats_file = ".stats.json"
    try:
        if os.path.isfile(stats_file):
            with open(stats_file, "r") as f:
                data = json.load(f)

                data["files_processed"] += 1
                data["total_time"] += total_time
                data["average_time"] = round(
                    data["total_time"] / data["files_processed"], 2
                )
        else:
            data = {
                "files_processed": 1,
                "total_time": total_time,
                "average_time": total_time,
            }

        with open(stats_file, "w") as f:
            json.dump(data, f, indent=4)

    except json.JSONDecodeError as e:
        os.remove(stats_file)  # Delete the file if it's invalid
        return
    except Exception as e:
        print_exception(e, "CRASHED")
        return


def main(host: str, port: int):
    # Loop through the folder and process the oldest JSON file

    global MODEL, NUM_CTX

    # Try to process failed uploads, maybe the service is back up
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
    data = load_json_file(json_file)

    print_w(" " + data["id"])

    # Move file to processing folder
    json_file = api_file_move(json_file, processing_folder)

    translation = False
    res_json = None
    result = None
    message = ""

    start_time = time.time()

    my_type = None
    if "type" in data and data["type"]:
        my_type = data["type"]

    if "model" in data:
        MODEL = data["model"]

    if "num_ctx" in data:
        NUM_CTX = data["num_ctx"]

    if "hostname" not in data or data["hostname"] not in VALID_HOSTNAMES:
        print_r(">> REJECTED " + str(data["hostname"]))
        api_file_move(json_file, rejected_folder)
        return

    if my_type == "raw_llama":
        print_g(" RUNNING LLAMA IN RAW MODE >> " + str(data["subtype"]))

        if data.get("raw_tools"):
            print_g(" RAW TOOLS ")
            print_g(" CHAT MESSAGE >> " + MODEL + " " + str(NUM_CTX))

            res_json = run_prompt_function(
                data["raw_messages"], data["raw_tools"], MODEL
            )
            if not res_json:
                print_r(" RETRY, MAYBE OUR LLAMA 3.1 WAS LAZY")
                res_json = run_prompt_function(
                    data["raw_messages"], data["raw_tools"], "llama3.2"
                )

            if not res_json:
                print_r(" FAILED LLAMA3.2 TOO ")
        else:
            print_g(" CHAT MESSAGE >> " + MODEL + " " + str(NUM_CTX))

            response = ollama.chat(
                model=MODEL,
                messages=data["raw_messages"],
                options={"num_ctx": NUM_CTX},
            )
            # Process the message using the run_main function

            result = response["message"]["content"]
            console.print(Markdown(result))

    else:

        if my_type == "translation":
            print_h(" FOUND TRANSLATION ")
            translation = True
            res_json = run_translation(message)

        system = get_generic_system(data)

        assistant, message, call_tools = get_legacy(data)
        arr_messages = get_generic_messages(data, system, assistant, message)

        print_g(">> MODEL " + MODEL)
        print(str(message))

        try:
            if not translation:
                response = ollama.chat(
                    model=MODEL,
                    messages=arr_messages,
                    options={"num_ctx": NUM_CTX},
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

                res_json = run_prompt(system, assistant, message, MODEL)
                if not res_json:
                    print_r(" RETRY, MAYBE OUR LLAMA 3.1 WAS LAZY")
                    res_json = run_prompt(system, assistant, message, "llama3.2")

                if not res_json:
                    print_r(" FAILED LLAMA3.2 TOO ")

        except TimeoutError as e:
            print(e)
            print("---------------- TIMEOUT DOING PROCESSING --------------")
            api_file_move(json_file, ai_timeout)

        except Exception as e:
            api_file_move(json_file, ai_crashed)
            print_r(f"Failed to contact inference {json_file}: {e}")

    if not translation and not result and not res_json:
        print_r(f"NO RESULT {json_file}")
        api_file_move(json_file, ai_crashed)
        return

    if res_json != None:
        data["type"] = "dict"
        data["dict"] = res_json
        if result:
            data["ai_summary"] = str(result).replace("StepType.inference> ", "")

            try:
                res = run_company_tickers_extraction(data["ai_summary"], MODEL)
                if res:
                    data["dict"].extend(res)
            except Exception as e:
                print_exception(e, "CRASH")

    else:
        if result:
            data["result"] = str(result).replace("StepType.inference> ", "")

    # Callback with the updated data
    try:
        end_time = time.time()
        print_w(" " + data["id"])

        data["at_process_time_secs"] = round(end_time - start_time, 2)
        print_b(f" Process Time {end_time - start_time:.2f} secs ")

        with open(json_file, "w") as f:
            json.dump(data, f, indent=4)

        upload_file(json_file)

    except Exception as e:
        print_e(f"Failed to save result to file {json_file}: {e}")

    api_update_stats(time.time() - start_time)

    BEXIT = True


if __name__ == "__main__":
    fire.Fire(main)
