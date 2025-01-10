""" Description: This file contains functions to work with files.
"""

import json
import os
import shutil

from colorama import Fore, Back, Style, init


def get_oldest_file(folder):
    """Get the oldest file in the folder."""
    files = [os.path.join(folder, f) for f in os.listdir(folder) if f.endswith(".json")]
    if not files:
        return None
    oldest_file = min(files, key=os.path.getctime)
    return oldest_file


def load_json_file(json_file):
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


def upload_file(json_file):
    try:
        with open(json_file, "r") as f:
            data = json.load(f)

            result_ok = callback_url(data["callback_url"], data)

            if "dev" in data:
                if result_ok:
                    api_file_move(json_file, development_folder)
                else:
                    api_file_move(json_file + ".FAILED", development_folder)

            else:
                if result_ok:
                    api_file_move(json_file, processed_folder)
                else:
                    api_file_move(json_file, failed_folder)

            print("\n")

    except Exception as e:
        print(f"Failed to save result to file {json_file}: {e}")

        os.remove(json_file)  # Delete the file if it can't be saved
        print(f"Deleted file due to save error: {json_file}")


def api_file_move(json_file, new_folder):
    print_b(" " + os.path.basename(json_file) + " >> " + new_folder)
    ret = os.path.join(new_folder, os.path.basename(json_file))
    shutil.move(json_file, ret)
    return ret


# TODO: move to a common library
def print_e(text):
    print(Back.RED + line_80)
    print(Back.RED + text.center(80))
    print(Back.RED + line_80)


def print_r(text, in_place=False):
    print(Fore.RED + text, end="\r" if in_place else "\n", flush=in_place)


def print_b(text):
    print(Fore.LIGHTBLUE_EX + text)


line_80 = (
    "--------------------------------------------------------------------------------"
)