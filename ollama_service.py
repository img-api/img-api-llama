import json
import re
import time
from collections import Counter

import ollama
from rich.console import Console
from rich.markdown import Markdown

from printer import print_e, print_json, print_b, print_exception, print_g, print_r


console = Console()


def run_translation(self, prompt):
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


def translation_fallback(data, arr_messages):
    response = ollama.chat(
        model="llama3.1",
        messages=arr_messages,
        options={"num_ctx": 65536},
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


def run_prompt_function(raw_messages, raw_tools, model="llama3.1"):
    start_time = time.time()  # Start time measurement

    try:
        response = ollama.chat(
            model=model,
            messages=raw_messages,
            tools=raw_tools,
            options={"num_ctx": 65536},
            keep_alive=1,
        )

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


def json_serialize_toolcall(result):

    serialz = []
    for tool in result:
        f = tool['function']
        old_format = {
            'function': {
                'name': f['name'],
                'arguments': f['arguments'],
            }
        }
        serialz.append(old_format)

    dmp = json.dumps(serialz, indent=4)
    return dmp


def word_count(text):
    # Split the text into words and normalize to lowercase
    words = text.lower().split()
    # Count occurrences of each word
    word_counts = Counter(words)
    return word_counts
