# Processs the batch of chat texts using Vertex AI
import json
import os

from fire import Fire
import vertexai
from vertexai.generative_models import GenerativeModel
from google.oauth2 import service_account

from files import get_oldest_file, load_json_file


os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/home/dev/vertexai-credentials.json"


CONFIG_FILE = os.environ.get('CONFIG_FILE', 'config.json')

# Load the configuration file
with open(CONFIG_FILE, "r") as f:
    config = json.loads(f)


SOURCE_FOLDER = config['source_folder']
DEST_FOLDER = config['dest_folder']


def main():
    model = init_vertexai()

    source_file = get_oldest_file(SOURCE_FOLDER)
    data = load_json_file(source_file)

    # Process the data
    if data is None:
        return
    
    NUM_CTX = data["num_ctx"] if "num_ctx" in data else 1

    # send the data to Vertex AI
    messages = data['raw_messages']

    # Process the messages
    response = model.generate([messages], num_ctx=NUM_CTX)
    print(response)


def init_vertexai():
    # reading and saving credentials
    with open(os.environ['GOOGLE_APPLICATION_CREDENTIALS'], 'r') as source:
        info = json.load(source)

    # Auth using service account with json credentials
    service_account.Credentials.from_service_account_info(info)

    model = GenerativeModel(model_name="gemini-1.5-flash-001")
    # model = GenerativeModel(model_name="meta/llama-3.2-90b-vision-instruct-maas")
    # model = GenerativeModel(model_name="publishers/google/models/gemini-1.5-pro-002")

    return model


if __name__ == '__main__':
    Fire(main)