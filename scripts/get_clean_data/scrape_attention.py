"""
Author: Joshua Ashkinaze
Date: 03/16/2023

Description: This script gets attenion on various platforms for different keywords
"""
import argparse
import csv
from pytrends.request import TrendReq
import datetime
import datetime as dt
import json
import logging
import os
from json import JSONDecodeError
import random
import time

import numpy as np
import pandas as pd
import pytz
import requests
import tweepy
from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential,
    before_sleep_log,
    retry_if_exception_type
)
from waybacknews.searchapi import SearchApiClient


class TooManyRequestsError(Exception):
    logging.info("Error, too many requests")
    pass


def date_to_unix_timestamp(date_string, start_or_end):
    dt = datetime.datetime.strptime(date_string, '%Y-%m-%d')

    if start_or_end == 'start':
        dt = dt.replace(hour=0, minute=0, second=0)
    elif start_or_end == 'end':
        dt = dt.replace(hour=23, minute=59, second=59)
    else:
        raise ValueError("Invalid value for 'start_or_end'. Must be either 'start' or 'end'.")

    # Make the datetime object timezone-aware (assuming UTC)
    dt_utc = dt.replace(tzinfo=pytz.UTC)

    # Convert the datetime object to Eastern Standard Time (EST)
    est = pytz.timezone('US/Eastern')
    dt_est = dt_utc.astimezone(est)

    # Return the Unix timestamp
    return int(dt_est.timestamp())


def get_twitter_data(kw, start_date, end_date, bearer_token):
    data = []
    try:
        client = tweepy.Client(
            bearer_token=bearer_token,
            wait_on_rate_limit=True)
        counts = client.get_all_tweets_count(query=kw, start_time=f'{start_date}T00:00:00-05:00',
                                             end_time=f'{end_date}T11:59:59-05:00', granularity='day')
        for x in counts.data:
            row = {'day': x['start'].split("T")[0], 'kw': kw, 'value': x['tweet_count']}
            data.append(row)
    except Exception as e:
        return pd.DataFrame(
            {'kw': [str(kw)], 'date': [start_date], 'value': [np.NaN]}, index=[0])
    return pd.DataFrame(data)


def get_news_data(kw, start_date, end_date):
    start = dt.datetime.strptime(start_date, "%Y-%m-%d")
    end = dt.datetime.strptime(end_date, "%Y-%m-%d")

    # Make the start and end datetime objects timezone-aware (assuming UTC)
    start_utc = start.replace(tzinfo=pytz.UTC)
    end_utc = end.replace(tzinfo=pytz.UTC)

    # Convert the datetime objects to Eastern Standard Time (EST)
    est = pytz.timezone('US/Eastern')
    start_est = start_utc.astimezone(est)
    end_est = end_utc.astimezone(est)

    try:
        api = SearchApiClient("mediacloud")
        cts = api.count_over_time(kw, start_est, end_est)
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
            {'kw': [str(kw)], 'date': [start_date], 'value': [np.NaN]}, index=[0])


@retry(wait=wait_random_exponential(multiplier=0.05, min=1, max=60),
       stop=stop_after_attempt(30),
       retry=retry_if_exception_type(TooManyRequestsError, ValueError, JSONDecodeError),
       before_sleep=before_sleep_log(logging, logging.INFO),
       reraise=False)
def get_reddit_data(kw, start_date, end_date):
    try:
        start_timestamp = date_to_unix_timestamp(start_date, "start")
        end_timestamp = date_to_unix_timestamp(end_date, "end")
        date_range = pd.date_range(start_date, end_date, freq='D')
        data_list = []
        for date in date_range:
            date_str = date.strftime('%Y-%m-%d')
            current_start = date_to_unix_timestamp(date.strftime('%Y-%m-%d'), 'start')
            current_end = date_to_unix_timestamp((date + pd.Timedelta(days=1)).strftime('%Y-%m-%d'), 'end')
            url = f'https://api.pushshift.io/reddit/comment/search?title={kw}&since={current_start}&until={current_end}&limit=0&track_total_hits=true'
            response = requests.get(url)
            if response.status_code == 429:
                raise TooManyRequestsError("Too many requests")
            data = response.json()
            total_hits = data['metadata']['es']['hits']['total']['value']
            data_list.append({'date': date_str, 'kw': kw, 'value': total_hits})
        df = pd.DataFrame(data_list)
        return df
    except Exception as e:
        logging.info(f"Error getting Reddit data for {kw}: {e}")
        return pd.DataFrame(
            {'kw': [str(kw)], 'date': [start_date], 'value': [np.NaN]}, index=[0])

def get_google_trends_data(kw, start_date, end_date, search_type="", sleep_multiplier=1):
    try:
        if search_type == "web":
          search_type = ""
        time.sleep(sleep_multiplier)
        pytrends = TrendReq(hl='en-US',
                            tz=300,
                            geo = "US",
                            retries=10,
                            backoff_factor=5,
                            # Note: This is a temporary fix to changes to the Google Trends backend, working as of the
                            # time this script was run. Credit:
                            # https://github.com/GeneralMills/pytrends/issues/561#issuecomment-1462358749
                            requests_args = {'headers': {'Cookie': 'AEC=AUEFqZdI42AmiBCbajQmcjdVL6JsL0_jjuEBNgioIAifo2CdeKZjBkJz8vk; SID=VAg-9nNMB1RPS2j9KMTAU872D_QGUrXIV4GuoK2px7btIyryCkR-UnWLQGUdUuaRJp5E_g.; __Secure-1PSID=VAg-9nNMB1RPS2j9KMTAU872D_QGUrXIV4GuoK2px7btIyryyUqor8RKBlPSijO5jYTYWQ.; __Secure-3PSID=VAg-9nNMB1RPS2j9KMTAU872D_QGUrXIV4GuoK2px7btIyryEoN2Mb7Xfg_BKwEcbdmqnw.; HSID=ATj--Nr4zP6RlECcX; SSID=AyjRgRMVts1Z1v_09; APISID=_Q5UAlzMyjjCSfcb/AJ-kLsh6mkIE2BZfk; SAPISID=bM_ApyCj3JsatDpU/A1vQT7swDqYsb3ROc; __Secure-1PAPISID=bM_ApyCj3JsatDpU/A1vQT7swDqYsb3ROc; __Secure-3PAPISID=bM_ApyCj3JsatDpU/A1vQT7swDqYsb3ROc; NID=511=lq3xAB-CQT9jCytVXgT2vcO7nFM9S8tl97lJqPcbT_56hrc_V_aJCCamm-wgHwiB-PnUcrgq8awJBDFQR-iSBB_zvRzTpifdqA9OwZagmKNn5S0bmjv3-HsasR6fybPtcmSngtwitO-hU_1L3yJWZm-nvSuywU7fUge3XupAlilIbx1BTcAnykF4QQynsRQNzoMWTkr-60uyQE4K3PbKTuW9N-stfs14UMUKv3dqEX41cfZ7Amo7; 1P_JAR=2023-04-07-19; SIDCC=AFvIBn9S2jtFpiTP2L9AcdyQZlG03UFdiU-ZxeG40vb0O8EsyuojrKs-7dDHHl5LnBhV3sYBjg; __Secure-1PSIDCC=AFvIBn_1yN2rslv3gVNyJzBbMjsATlE80nlP1xv5WJ5SNo6KwaHys9_zm0TDfMigg3160pZNyw; __Secure-3PSIDCC=AFvIBn_p531rwqZwqHzxZF3EY62bU8VTtlap87jRCemhq14TJYrspbU04zaKHsAYaEgY0JO1UQ'}})
        pytrends.build_payload([kw], timeframe=f"{start_date} {end_date}", geo='US', gprop=search_type)
        data = pytrends.interest_over_time()
        d = data.reset_index()
        d = d[d.columns[:2]]
        d['kw'] = kw
        d.columns = ['date', 'value', 'kw']
        d = d[['kw', 'date', 'value']]
        return d
    except Exception as e:
        logging.info(f"Error getting Google Trends data for {kw} for search type {search_type}: {e}")
        return pd.DataFrame(
            {'kw': [str(kw)], 'date': [start_date], 'value': [np.NaN]}, index=[0])


def main(debug=False, sleep_multiplier=1):
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    log_file = os.path.splitext(os.path.basename(__file__))[0] + '.log'

    logging.basicConfig(filename=log_file, level=logging.INFO, filemode='w', format='%(asctime)s %(message)s', force=True)
    logging.info("Started")
    random.seed(416)
    print(f"Log file path: {log_file}")

    with open("../../src/creds.json", "r") as json_file:
        creds = json.load(json_file)
    bearer_token = creds["bearer_token"]

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
    for index, row in json_df_filter.iterrows():
        logging.info("Processing event {} of {}: {}".format(counter, len(json_df_filter), row['event']))
        kws = row['keywords']

        search_types = ['web', 'news', 'reddit', 'youtube', 'twitter']

        for kw in kws:
            for search_type in search_types:
                logging.info("Processing keyword: {} for search type {}".format(kw, search_type))
                if search_type == 'reddit':
                    trend_data = get_reddit_data(kw, row['start_date'], row['end_date'])
                elif search_type == 'news':
                    trend_data = get_news_data(kw, row['start_date'], row['end_date'])
                elif search_type == 'web':
                    trend_data = get_google_trends_data(kw=kw,
                                                        start_date=row['start_date'],
                                                        end_date=row['end_date'],
                                                        search_type=search_type,
                                                        sleep_multiplier=sleep_multiplier)
                elif search_type == 'youtube':
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
    logging.info("Done")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape data for keywords")
    parser.add_argument("--d", action="store_true", help="Enable debug mode")
    parser.add_argument("--s", type=float, default=10, help="Sleep time multiplier")
    args = parser.parse_args()
    main(debug=args.d, sleep_multiplier=args.s)
