import os
import json
from flask import Flask, request, jsonify

app = Flask(__name__)

SAVE_FOLDER = './DATA/JSON_TO_PROCESS'
if not os.path.exists(SAVE_FOLDER):
    os.makedirs(SAVE_FOLDER)



@app.route('/')
def hello():
    return 'Hello, World!'

# Route to handle file upload
@app.route('/upload-json', methods=['POST'])
def upload_json():
    # Check if the request has JSON data
    if request.is_json:
        try:
            # Parse the JSON data
            data = request.get_json()

            if 'id' not in data:
                return jsonify({"error": "Invalid JSON format"}), 400

            # Define the filename
            filename = os.path.join(SAVE_FOLDER, data['id'] + '_data.json')

            # Save the JSON data to a file
            with open(filename, 'w') as json_file:
                json.dump(data, json_file, indent=4)

            return jsonify({"message": "JSON file saved successfully"}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 400
    else:
        return jsonify({"error": "Invalid JSON format"}), 400