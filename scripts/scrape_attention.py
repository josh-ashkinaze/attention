"""
Author: Joshua Ashkinaze
Date: 03/16/2023

Description: This script scrapes Google Trends data for keywords
"""

import logging
import os
import pandas as pd
import time
import random
import subprocess
import argparse
import json
import csv


def get_google_trends_data(kw, start_date, end_date, search_type, sleep_multiplier=1, sleep_time=(1, 2)):
    """
    This function fetches Google Trends data for a given keyword and date range

    Params:
        kw: Keyword to search for
        start_date: Start date of the search
        end_date: End date of the search
        search_type: Type of search to perform (e.g. 'web', 'news', 'images')
        sleep_multiplier: Multiplier for the sleep time
        sleep_time: Tuple of the minimum and maximum time to sleep between requests
    Returns:
        Pandas DataFrame of the Google Trends data if successful, otherwise
        a DataFrame with a single row with the value -1.
    """
    sleep_time = random.uniform(sleep_time[0] * sleep_multiplier, sleep_time[1] * sleep_multiplier)
    logging.info("Sleeping for {}".format(sleep_time))
    time.sleep(sleep_time)
    script_path = "get_google_trends.js"
    # General exception catcher
    try:
        # If on any machine with node js installed normally
        try:
            result = subprocess.run(["node", script_path, kw, start_date, end_date, search_type], capture_output=True,
                                    text=True)
        # If on Great Lakes
        except:
            result = subprocess.run(
                ["../../../node-v18.15.0-linux-x64/bin/node", script_path, kw, start_date, end_date, search_type],
                capture_output=True,
                text=True)

        # Try to parse response
        try:
            if result.returncode == 0:
                json_data = json.loads(result.stdout)
                df = pd.DataFrame(json_data)
                df['search_type'] = search_type
                logging.info(df.head(1))
                return df
            else:
                print("Error fetching data:", result.stderr)
                return  pd.DataFrame({'kw':str(kw), 'date': start_date, 'value': -1, 'search_type': search_type})
        except Exception as e:
            logging.info("Error fetching data (parsing response) for keyword {}: {}".format(kw, e))
            return  pd.DataFrame({'kw':str(kw), 'date': start_date, 'value': -1, 'search_type': search_type})
    except Exception as e:
        logging.info("Error fetching data for keyword {}: {}".format(kw, e))
        return pd.DataFrame({'kw':str(kw), 'date': start_date, 'value': -1, 'search_type': search_type})


def main(debug=False, sleep_multiplier=1):
    log_file = os.path.splitext(os.path.basename(__file__))[0] + '.log'
    logging.basicConfig(filename=log_file, level=logging.INFO, filemode='w', format='%(asctime)s %(message)s')
    random.seed(416)
    json_df = pd.read_json("../data/2023-03-16_15:44:46_rumors.json").T.reset_index()

    # Convert the 'Rumor day' and 'Announcement day' columns to datetime objects
    json_df['rumor_day'] = pd.to_datetime(json_df['rumor_day'])
    json_df['announce_day'] = pd.to_datetime(json_df['announce_day'])
    json_df['start_date'] = (json_df['rumor_day'] - pd.Timedelta(days=30)).dt.strftime('%Y-%m-%d')
    json_df['end_date'] = (json_df['announce_day'] + pd.Timedelta(days=30)).dt.strftime('%Y-%m-%d')

    # Calculate the days between 'Rumor day' and 'Announcement day'
    json_df['days_between'] = (json_df['announce_day'] - json_df['rumor_day']).dt.days
    logging.info("Number of events: {}".format(len(json_df)))

    # Filter for gap between 7 and 60 days
    json_df_filter = json_df.query("days_between>=7&days_between<=60")
    logging.info("Number of events after filtering: {}".format(len(json_df_filter)))
    if debug:
        json_df_filter = json_df_filter.head(1)

    # Set the output file path
    fn = "../data/trend_data.csv"
    if debug:
        fn = "../data/trend_data_debug.csv"

    # Write header
    fieldnames = ["date", "value", "search_type", "event", "kw"]
    with open(fn, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

    # Loop through each event, and get web, search, and youtube data for each keyword in
    # the associated event
    counter = 0
    for index, row in json_df_filter.iterrows():
        logging.info("Processing event {} of {}: {}".format(counter, len(json_df_filter), row['event']))
        kws = row['keywords']
        search_types = ['web', 'news', 'youtube']
        for kw in kws:
            for search_type in search_types:
                trend_data = get_google_trends_data(kw=kw,
                                                    start_date=row['start_date'],
                                                    end_date=row['end_date'],
                                                    search_type=search_type,
                                                    sleep_multiplier=sleep_multiplier)
                trend_data['event'] = row['index']

                # Append the trend data to the CSV file
                with open(fn, 'a', newline='') as f:
                    trend_data_dict = trend_data.to_dict(orient='records')
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writerows(trend_data_dict)
        counter += 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape Google Trends data for keywords")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--sleep", type=float, default=1, help="Sleep time multiplier")
    args = parser.parse_args()
    main(debug=args.debug, sleep_multiplier=args.sleep)
