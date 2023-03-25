"""
Author: Joshua Ashkinaze
Date: 03/16/2023

Description: This script parses the events given by GPT4 and outputs a json file
"""

import re
import json
from datetime import datetime

def convert_date(date_str):
    date_obj = datetime.strptime(date_str, "%B %d, %Y").strftime("%Y-%m-%d")
    return date_obj.strftime("%Y-%m-%d")


def main():
    now_str = datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
    prompt_file_path = "../../prompts/event_prompt.md"
    with open(prompt_file_path, "r") as file:
        data = file.read()
    pattern = r"Event: (.*?)\nRumor day: (.*?)\nAnnouncement day: (.*?)\nDescription: (.*?)\n\n\n"
    matches = re.findall(pattern, data, re.MULTILINE | re.DOTALL)

    rumors = {}
    for match in matches:
        event, rumor_day, announcement_day, description = match
        event_first_word, event_last_word = event.split()[0], event.split()[-1]
        rumor_year = rumor_day.split()[-1]

        key = f"{event_first_word}_{event_last_word}_{rumor_year}"

        rumors[key] = {
            "event": event,
            "rumor_day": datetime.strptime(rumor_day, "%B %d, %Y").strftime("%Y-%m-%d"),
            "announce_day": datetime.strptime(announcement_day, "%B %d, %Y").strftime("%Y-%m-%d"),
            "description": description,
            "keywords": []
        }

    with open("../data/{}_rumors.json".format(now_str), "w") as outfile:
        json.dump(rumors, outfile, indent=4)


if __name__ == "__main__":
    main()