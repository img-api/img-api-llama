"""Module for using Vertex AI as a service """
import json
import os
import time

from vertexai.generative_models import GenerativeModel                                                        
from google.oauth2 import service_account                                                                                                                                                                                   

from printer import print_r, print_exception, print_g


# Load config from JSON file
config_file_path = os.environ.get("CONFIG_FILE_PATH", "/home/dev/vertex-ai-config.json")

with open(config_file_path, "r") as f:
    config = json.load(f)

# Extract config values
google_credentials = config["GOOGLE_APPLICATION_CREDENTIALS"] 
ai_model = config["AI_MODEL"]

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = google_credentials


# Load credentials
with open(google_credentials, 'r') as source:
    info = json.load(source)

# Auth using service account with json credentials
service_account.Credentials.from_service_account_info(info)
model = GenerativeModel(model_name=ai_model)


def run_translation(self, prompt):
    """
    response = model.generate_content(["Tell me the numbers from 1 to 10"])
    text = response.candidates[0].content.parts[0].text
    return text
    """
    try:
        # Create prompt for translation
        translation_prompt = [
            {
                "text": "As an expert native and professional translator, transcribe the following text adjusted to the locale required:\n\n" + prompt
            }
        ]

        # Generate response from model
        response = model.generate_content(translation_prompt)

        # Extract translated text from response
        if response.candidates and len(response.candidates) > 0:
            translation = response.candidates[0].content.parts[0].text
            return translation
        
        return None

    except Exception as e:
        print(f"Translation failed: {str(e)}")
        return None


def run_prompt_function(raw_messages, raw_tools, model="llama3.1"):
    start_time = time.time()  # Start time measurement

    try:
        # Convert raw messages to prompt text
        prompt_text = ""
        for msg in raw_messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            prompt_text += f"{role}: {content}\n"

        # Add tools context to prompt
        if raw_tools:
            prompt_text += "\nAvailable tools:\n"
            for tool in raw_tools:
                prompt_text += json.dumps(tool, indent=2) + "\n"

        # Generate response from model
        response = model.generate_content(prompt_text)

        if not response.candidates or len(response.candidates) == 0:
            print_r("No response generated from model")
            return None

        # Extract response text
        result_text = response.candidates[0].content.parts[0].text

        # Try to parse response as JSON
        try:
            # Attempt to extract JSON from response text
            json_str = result_text[result_text.find("{"):result_text.rfind("}")+1]
            result = json.loads(json_str)

            end_time = time.time()  # End time measurement

            # Format response similar to ollama format
            formatted_response = [{
                "function": {
                    "name": "set_article_information",
                    "arguments": result
                }
            }]

            # Add timing info
            result["model"] = "vertexai"
            result["process_time"] = round(end_time - start_time, 2)

            print_g(f" run_prompt_function: {end_time - start_time:.2f} sec")
            return formatted_response

        except json.JSONDecodeError as e:
            print_r(f"Failed parsing JSON from response: {e}")
            return None

    except Exception as e:
        print_exception(e, "CRASH PROMPT")

    return None


def run_prompt(raw_messages, raw_tools, model="llama3.1"):
    start_time = time.time()  # Start time measurement

    try:
        # Convert raw messages to prompt text
        prompt_text = ""
        for msg in raw_messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            prompt_text += f"{role}: {content}\n"

        # Generate response from model
        response = model.generate_content(prompt_text)

        if not response.candidates or len(response.candidates) == 0:
            print_r("No response generated from model")
            return None

        # Extract response text
        result_text = response.candidates[0].content.parts[0].text

        # Try to parse response as JSON
        try:
            # Attempt to extract JSON from response text
            json_str = result_text[result_text.find("{"):result_text.rfind("}")+1]
            result = json.loads(json_str)

            end_time = time.time()  # End time measurement

            # Format response similar to ollama format
            formatted_response = [{
                "function": {
                    "name": "set_article_information",
                    "arguments": result
                }
            }]

            # Add timing info
            result["model"] = "vertexai"
            result["process_time"] = round(end_time - start_time, 2)

            print_g(f" run_prompt_function: {end_time - start_time:.2f} sec")
            return formatted_response

        except json.JSONDecodeError as e:
            print_r(f"Failed parsing JSON from response: {e}")
            return None

    except Exception as e:
        print_exception(e, "CRASH PROMPT")

    return None
