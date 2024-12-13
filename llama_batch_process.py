import os
import json

import fire
import shutil
import urllib3
import warnings
import requests
import signal

from datetime import datetime
from colorama import Fore, Back, Style, init

from rich.console import Console

from printer import print_h, print_e, print_g, print_r


class AIServices:
    OLLAMA = "ollama"
    VERTEXAI = "vertexai"


IMGDATA_AI_SERVICE = os.environ.get("IMGDATA_AI_SERVICE", "ollama")


match IMGDATA_AI_SERVICE:
    case AIServices.OLLAMA:
        import ollama_service as service
    case AIServices.VERTEXAI:
        import vertexai_service as service


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
signal.alarm(50)  # Set the alarm for 50 seconds

import ollama

# Configurable paths
source_folder = "./DATA/JSON_TO_PROCESS"
priority_folder = "./DATA/JSON_TO_PROCESS_PRIORITY"
processed_folder = "./DATA/PROCESSED"
processing_folder = "./DATA/PROCESSING"
ai_crashed = "./DATA/AI_FAILED"
ai_timeout = "./DATA/AI_TIMEOUT"
failed_folder = "./DATA/FAILED"
rejected_folder = "./DATA/REJECTED"

PATHS = [
    source_folder,
    priority_folder,
    processed_folder,
    processing_folder,
    ai_crashed,
    ai_timeout,
    failed_folder,
    rejected_folder,
]

# Ensure processed folder exists
for folder in PATHS:
    if not os.path.exists(folder):
        os.makedirs(folder)


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
        print_g(f" Callback {url} {response.status_code}")

        return True
    except requests.exceptions.RequestException as e:
        print_e(f" Failed to callback {url}: {e}")

    return False


def upload_file(json_file):
    try:
        with open(json_file, "r") as f:
            data = json.load(f)

            result_ok = callback_url(data["callback_url"], data)
            if result_ok:
                api_file_move(json_file, processed_folder)
            else:
                api_file_move(json_file, failed_folder)

            print("\n")

    except Exception as e:
        print(f"Failed to save result to file {json_file}: {e}")

        os.remove(json_file)  # Delete the file if it can't be saved
        print(f"Deleted file due to save error: {json_file}")


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

    dmp = json.dumps(serialz, indent=4)
    return dmp


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
                    "title_clickbait",
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
        options={"num_ctx": 65536},
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


def api_file_move(json_file, new_folder):
    print_b(" " + os.path.basename(json_file) + " >> " + new_folder)
    ret = os.path.join(new_folder, os.path.basename(json_file))
    shutil.move(json_file, ret)
    return ret


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

    print_w(" " + data['id'])

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

        res_json = service.run_prompt_function(
            data["raw_messages"], data["raw_tools"], "llama3.1"
        )
        if not res_json:
            print_r(" RETRY, MAYBE OUR LLAMA 3.1 WAS LAZY")
            res_json = service.run_prompt_function(
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
            res_json = service.run_translation(message)

        system = get_generic_system(data)

        assistant, message, call_tools = get_legacy(data)
        arr_messages = get_generic_messages(data, system, assistant, message)

        print_g(">> MODEL " + MODEL)
        print(str(message))

        try:
            if not translation:
                service.translation_fallback(data, arr_messages)

            if call_tools:
                res_json = service.run_prompt(system, assistant, message, "llama3.1")
                if not res_json:
                    print_r(" RETRY, MAYBE OUR LLAMA 3.1 WAS LAZY")
                    res_json = service.run_prompt(system, assistant, message, "llama3.2")

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
    else:
        if result:
            data["result"] = str(result).replace("StepType.inference> ", "")

    # Callback with the updated data
    try:
        end_time = time.time()

        data["at_process_time_secs"] = round(end_time - start_time, 2)
        print_b(f" Process Time {end_time - start_time:.2f} secs ")

        with open(json_file, "w") as f:
            json.dump(data, f, indent=4)

        upload_file(json_file)
    except Exception as e:
        print_e(f"Failed to save result to file {json_file}: {e}")

    BEXIT = True


if __name__ == "__main__":
    fire.Fire(main)
