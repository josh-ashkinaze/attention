import re
import csv
from datetime import datetime
import pandas as pd

def read_file(file_name):
    with open(file_name, "r") as file:
        return file.read()

def extract_events(file_content):
    event_pattern = re.compile(r"RUMOR[-\s](\d+):(.*?)\n\nANNOUNCEMENT[-\s](\d+):(.*?)(?:\n\n|$)", re.DOTALL)
    matches = event_pattern.findall(file_content)

    events = []
    for match in matches:
        rumor_number = match[0]
        key = f"rumor_{rumor_number}"
        rumor = match[1].strip()
        announcement = match[3].strip()
        event = [key, rumor, announcement]
        events.append(event)
    return events

def main():
    now_str = datetime.now().strftime("%Y-%m-%d__%H.%M.%S")
    file_name = "../../prompts/fake_rumor_prompt.md"
    file_content = read_file(file_name)
    events = extract_events(file_content)

    output_file = f"../../data/{now_str}_fake_rumors.csv"
    with open(output_file, "w", newline='', encoding='utf-8') as outfile:
        csv_writer = csv.writer(outfile)
        csv_writer.writerow(['key', 'rumor', 'announcement'])
        csv_writer.writerows(events)
    wide_df = pd.read_csv(output_file)
    long_output_file = f"../../data/{now_str}_fake_rumors_long.csv"
    df_long = pd.melt(wide_df, id_vars=['key'], var_name='rumor_or_announcement', value_name='text')
    df_long['u_key'] = df_long['key'] + '_' + df_long['rumor_or_announcement']
    df_long[['u_key', 'key', 'rumor_or_announcement', 'text']].to_csv(long_output_file, index=False)
if __name__ == "__main__":
    main()
