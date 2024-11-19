import os
import json
from flask import Flask, request, jsonify
from datetime import datetime

app = Flask(__name__)

SAVE_FOLDER = "./DATA/JSON_TO_PROCESS"
if not os.path.exists(SAVE_FOLDER):
    os.makedirs(SAVE_FOLDER)

PRIORITY_FOLDER = "./DATA/JSON_TO_PROCESS_PRIORITY"
if not os.path.exists(PRIORITY_FOLDER):
    os.makedirs(PRIORITY_FOLDER)


def get_files_and_dates_sorted(folder_path):
    files_info = []
    for dirpath, dirnames, filenames in os.walk(folder_path):
        for file in filenames:
            file_path = os.path.join(dirpath, file)
            if os.path.isfile(file_path):
                # Get the last modification date
                mod_time = os.path.getmtime(file_path)
                files_info.append(
                    (file_path, mod_time)
                )  # Store the timestamp for sorting

    # Sort by modification time
    files_info.sort(key=lambda x: x[1])  # Sort by timestamp
    # Convert the timestamp back to a readable date
    sorted_files = [
        (file, datetime.fromtimestamp(mod_time).strftime("%Y-%m-%d %H:%M:%S"))
        for file, mod_time in files_info
    ]
    return sorted_files


def count_files_in_folder(folder_path):
    file_count = 0
    for dirpath, dirnames, filenames in os.walk(folder_path):
        file_count += len(filenames)
    return file_count


@app.route("/")
@app.route("/api_v1/")
def hello():
    return (
        jsonify(
            {
                "process": get_files_and_dates_sorted(SAVE_FOLDER),
                "priority": get_files_and_dates_sorted(PRIORITY_FOLDER),
                "message": "JSON file saved successfully",
            }
        ),
        200,
    )


# Route to handle file upload
@app.route("/upload-json", methods=["POST"])
@app.route("/api_v1/upload-json", methods=["POST"])
def upload_json():
    # Check if the request has JSON data
    if request.is_json:
        try:
            # Parse the JSON data
            data = request.get_json()

            if "id" not in data:
                return jsonify({"error": "Invalid JSON format"}), 400

            folder = SAVE_FOLDER
            if "priority" in data:
                print(" FOUND PRIORITY FILE ")
                folder = PRIORITY_FOLDER

            # Define the filename
            filename = os.path.join(folder, data["id"] + "_data.json")

            # Save the JSON data to a file
            with open(filename, "w") as json_file:
                json.dump(data, json_file, indent=4)

            total_files = count_files_in_folder(folder)
            files_folder = get_files_and_dates_sorted(folder)
            return (
                jsonify(
                    {
                        "queue_size": total_files,
                        "files_folder": files_folder,
                        "message": "JSON file saved successfully",
                    }
                ),
                200,
            )
        except Exception as e:
            return jsonify({"error": str(e)}), 400
    else:
        return jsonify({"error": "Invalid JSON format"}), 400
