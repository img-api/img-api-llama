# Processs the batch of chat texts using Vertex AI
import json
import os

from fire import Fire

from .files import get_oldest_file, load_json_file


CONFIG_FILE = os.environ.get('CONFIG_FILE', 'config.json')

# Load the configuration file
with open(CONFIG_FILE, "r") as f:
    config = json.loads(f)


SOURCE_FOLDER = config['source_folder']
DEST_FOLDER = config['dest_folder']


def main():
    source_file = get_oldest_file(SOURCE_FOLDER)
    data = load_json_file(source_file)

    # Process the data
    if data is None:
        return
    
    # send the data to Vertex AI


    




if __name__ == '__main__':
    Fire(main)