"""
Author: Joshua Ashkinaze
Date: 03/16/2023

Description: This script scrapes Google Trends data for keywords
"""

import logging
import os
import pandas as pd
import time
from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential,
    before_sleep_log,
    retry_if_exception_type
)
import random
import subprocess
import numpy as np
import argparse
import json
import csv
import requests
import datetime
import multiprocessing
import wikipedia
import pageviewapi
from pmaw import PushshiftAPI
from waybacknews.searchapi import SearchApiClient
import datetime as dt

class TooManyRequestsError(Exception):
    pass

def date_to_unix_timestamp(date_string):
    dt = datetime.datetime.strptime(date_string, '%Y-%m-%d')
    return int(time.mktime(dt.timetuple()))

def get_news_data(kw, start_date, end_date):
    """Get news counts from mediacloud"""
    start = dt.datetime.strptime(start_date, "%Y-%m-%d")
    end = dt.datetime.strptime(end_date, "%Y-%m-%d")

    try:
        api = SearchApiClient("mediacloud")
        cts = api.count_over_time(kw, start, end)
        result = []
        for entry in cts:
            result.append({
                'kw': kw,
                'date': entry['date'].strftime("%Y-%m-%d"),
                'value': entry['count']
            })

        return pd.DataFrame(result)
    except Exception as e:
        logging.error(f"Error getting news attention for {kw}: {e}")
        return pd.DataFrame(
            {'kw': [str(kw)], 'date': [start_date], 'value': [-1]}, index=[0])

@retry(wait=wait_random_exponential(multiplier=0.05, min=1, max=60),
       stop=stop_after_attempt(30),
       retry=retry_if_exception_type(TooManyRequestsError),
       before_sleep=before_sleep_log(logging, logging.INFO),
       reraise=False)
def get_reddit_data(kw, start_date, end_date):
    def date_to_unix_timestamp(date_string):
        dt = datetime.datetime.strptime(date_string, '%Y-%m-%d')
        return int(time.mktime(dt.timetuple()))

    try:
        start_timestamp = date_to_unix_timestamp(start_date)
        end_timestamp = date_to_unix_timestamp(end_date)
        date_range = pd.date_range(start_date, end_date, freq='D')
        data_list = []
        for date in date_range:
            current_start = date_to_unix_timestamp(date.strftime('%Y-%m-%d'))
            current_end = date_to_unix_timestamp((date + pd.Timedelta(days=1)).strftime('%Y-%m-%d'))
            url = f'https://api.pushshift.io/reddit/comment/search?title={kw}&since={current_start}&until={current_end}&limit=0&track_total_hits=true'
            response = requests.get(url)
            if response.status_code == 429:
                raise TooManyRequestsError("Too many requests")
            data = response.json()
            total_hits = data['metadata']['es']['hits']['total']['value']
            data_list.append({'date': date, 'kw': kw, 'value': total_hits})
        df = pd.DataFrame(data_list)
        return df
    except TooManyRequestsError as e:
        logging.info(f"Too many requests for {kw}: {e}")
        return pd.DataFrame(
            {'kw': [str(kw)], 'date': [start_date], 'value': [np.NaN]}, index=[0])
    except Exception as e:
        logging.info(f"Error getting Reddit data for {kw}: {e}")
        return pd.DataFrame(
            {'kw': [str(kw)], 'date': [start_date], 'value': [np.NaN]}, index=[0])


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
                try:
                    json_data = json.loads(result.stdout)
                    df = pd.DataFrame(json_data)
                    df['search_type'] = search_type
                    logging.info(df.head(1))
                    return df
                except Exception as e:
                    return pd.DataFrame({'kw': [str(kw)], 'date': [start_date], 'value': [np.NaN], 'search_type': [search_type]}, index=[0])

            else:
                print("Error fetching data:", result.stderr)
                return pd.DataFrame(
                    {'kw': [str(kw)], 'date': [start_date], 'value': [np.NaN], 'search_type': [search_type]}, index=[0])
        except Exception as e:
            logging.info("Error fetching data (parsing response) for keyword {}: {}".format(kw, e))
            return pd.DataFrame({'kw': [str(kw)], 'date': [start_date], 'value': [np.NaN], 'search_type': [search_type]},
                                index=[0])
    except Exception as e:
        logging.info("Error fetching data for keyword {}: {}".format(kw, e))
        return pd.DataFrame({'kw': [str(kw)], 'date': [start_date], 'value': [np.NaN], 'search_type': [search_type]}, index=[0])


def main(debug=False, sleep_multiplier=1):
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    log_file = os.path.splitext(os.path.basename(__file__))[0] + '.log'
    logging.basicConfig(filename=log_file, level=logging.INFO, filemode='w', format='%(asctime)s %(message)s')
    random.seed(416)
    json_df = pd.read_json("../../data/2023-03-16_15_44_46_rumors.json").T.reset_index()

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
        json_df_filter = json_df_filter.head(2)

    # Set the output file path
    fn = "../../data/trend_data_new10.csv"
    if debug:
        fn = "../../data/trend_data_debug10.csv"

    # Write header
    fieldnames = ["date", "value", "search_type", "event", "kw"]
    with open(fn, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

    # Loop through each event, and get web, search, and youtube data for each keyword in
    # the associated event
    counter = 0
    wiki_article_matches = []
    for index, row in json_df_filter.iterrows():
        logging.info("Processing event {} of {}: {}".format(counter, len(json_df_filter), row['event']))
        kws = row['keywords']

        search_types = ['web', 'search', 'youtube', 'news', 'reddit']

        for kw in kws:
            for search_type in search_types:
                logging.info("Processing keyword: {} for search type {}".format(kw, search_type))
                if search_type == 'reddit':
                    trend_data = get_reddit_data(kw, row['start_date'], row['end_date'])
                elif search_type == 'news':
                    trend_data = get_news_data(kw, row['start_date'], row['end_date'])
                else:
                    trend_data = get_google_trends_data(kw=kw,
                                                        start_date=row['start_date'],
                                                        end_date=row['end_date'],
                                                        search_type=search_type,
                                                        sleep_multiplier=sleep_multiplier)
                trend_data['event'] = row['index']
                trend_data['search_type'] = search_type

                # Append the trend data to the CSV file
                with open(fn, 'a', newline='') as f:
                    trend_data_dict = trend_data.to_dict(orient='records')
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writerows(trend_data_dict)
        counter += 1
    wiki_df = pd.DataFrame(wiki_article_matches)
    wiki_df.to_csv("../../data/wiki_article_matches.csv", index=False)
    logging.info("Done")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape data for keywords")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--sleep", type=float, default=1, help="Sleep time multiplier")
    args = parser.parse_args()
    main(debug=args.debug, sleep_multiplier=args.sleep)
