import requests
from datetime import datetime, timedelta
import traceback
import time
import json
import sys
import os
import csv
# import alpaca_trade_api as tradeapi
# from django.conf import settings
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer as SIA
from nltk.metrics import edit_distance
import praw
import matplotlib.pyplot as plt
import math
import datetime as dt
import pandas as pd
import numpy as np
import re
# from mainpage.models import FundComposition, Transactions
from decimal import Decimal, getcontext

BASE_DIRECTORY = #TODO: this is where you put the directory (between quotes) of where this file lies


## NOTE: here's how to run the below
downloadFromUrl(BASE_DIRECTORY + "TODO: this is where you want to put the scraped file", "submission", str(start_date), str(end_date)) # TODO: manually pick a start date (can do "2021-12-31")
downloadFromUrl(BASE_DIRECTORY + "TODO: this is where you want to put the scraped file", "comment", str(start_date), str(end_date)) # TODO: manually pick an end date (can do "2022-01-13")

## NOTE: after running the above, and before running analyze(), you should combine the two files generated from the above into one file, called something like "wsb_combined.txt"

submission_statistics = []
top_tickers = analyze(submission_statistics)


def downloadFromUrl(filename, object_type, start_date, end_date):
    url = f"https://api.pushshift.io/reddit/{object_type}/search?limit=1000&{filter_string}&sort=desc&after={start_date}&selftext:not='[removed]'&before="
    print(f"Saving {object_type}s to {filename}")

    count = 0
    handle = open(filename, 'w')
    previous_epoch = int(end_date)

    ticker_count = {}
    while True:
        new_url = url.format(object_type, filter_string)+str(previous_epoch)
        # print("while")
        if(object_type == "submission"):
            new_url = new_url+"&is_self=true"
        if(object_type == "comment"):
            new_url = new_url+"&score=>10"
        json_text = requests.get(
            new_url, headers={'User-Agent': ""})
        # pushshift has a rate limit, if we send requests too fast it will start returning error messages
        time.sleep(1)
        try:
            json_data = json_text.json()
        except json.decoder.JSONDecodeError:
            time.sleep(1)
            continue
        
        if 'data' not in json_data:
            break
        objects = json_data['data']
        if len(objects) == 0:
            break

        # lots of submissions are repeats (and thus could mess with results). This attempts to decrease that bias (commented below bc doesn't seem needed)
        last_text = ""
        for object in objects:
            previous_epoch = object['created_utc'] - 1
            count += 1
            if (count % 100 == 0): print(count)
            if count == 10000: break
            # print("still going")
            if object_type == 'comment':
                bodytext = object['body'].encode(
                    encoding='ascii', errors='ignore').decode()

                # if(len(bodytext) == len(last_text)):
                #     if(bodytext == last_text):
                #         continue
                # last_text = bodytext

                if any(x in bodytext for x in stocks):
                    # print(object['permalink'])
                    
                    for ticker in stocks:
                        if ticker in bodytext:
                            if ticker not in ticker_count:
                                ticker_count[ticker] = 0
                            else:
                                ticker_count[ticker] += 1
                    
                    # print(*(ticker for ticker in stocks if ticker in bodytext))
                    try:
                        handle.write(str(object['score']))
                        handle.write(" : ")
                        handle.write(datetime.fromtimestamp(
                            object['created_utc']).strftime("%Y-%m-%d"))
                        handle.write("\n")
                        handle.write(bodytext)
                        handle.write("\n-------------------------------\n")
                    except Exception as err:
                        print(
                            f"Couldn't print comment: https://www.reddit.com{object['permalink']}")
                        print(traceback.format_exc())
            elif object_type == 'submission':
                # if 'selftext' not in object:
                #     continue
                try:
                    bodytext = object['title'].encode(
                        encoding='ascii', errors='ignore').decode()
                except KeyError:
                    continue
                try:
                    bodytext = bodytext + " " + object['selftext'].encode(
                        encoding='ascii', errors='ignore').decode()
                except KeyError:
                    pass

                # if(len(bodytext) == len(last_text)):
                #     if(bodytext == last_text):
                #         continue
                # last_text = bodytext

                if any(x in bodytext for x in stocks):
                    # print(object['permalink'])
                    for ticker in stocks:
                        if ticker in bodytext:
                            if ticker not in ticker_count:
                                ticker_count[ticker] = 0
                            else:
                                ticker_count[ticker] += 1
                    
                    # print(*(ticker for ticker in stocks if ticker in bodytext))
                    try:
                        # print(object['score'])
                        handle.write(str(object['score'])) # TODO: this isn't helpful, doesn't ever pick up score
                        handle.write(" : ")
                        handle.write(datetime.fromtimestamp(
                            object['created_utc']).strftime("%Y-%m-%d"))
                        handle.write("\n")
                        handle.write(bodytext)
                        handle.write("\n-------------------------------\n")
                    except Exception as err:
                        print(f"Couldn't print post: {object['url']}")
                        print(traceback.format_exc())

        if(count == 10000): break

        # print("Scraped {} {}s through {}".format(count, object_type, datetime.fromtimestamp(previous_epoch).strftime("%Y-%m-%d")))

    # print(f"Scraped {count} {object_type}s")
    print("Scraped {} {}s through {}".format(count, object_type, datetime.fromtimestamp(previous_epoch).strftime("%Y-%m-%d")))
    handle.close()
    
    # print(ticker_count)


    
def analyze(submission_statistics):
    d = {}
    submission_statistics = submission_statistics

    new_words = {
        "yolo": 1.0,
        "tits": 0.0,
        "jacked": 4.0,
        "ape": 4.0,
        "apes": 4.0,
        "rocket": 15.0,
        "autist": 0.0,
        "retard": 0.0,
        "bull": 5.0,
        "bullish": 5.0,
        "bear": -5.0,
        "bearish": -5.0,
        "rainbow": -2.0,
        "bagholder": -5.0,
        "buy": 5.0,
        "sell": -5.0,
        "hold": 4.0,
        "bagholder": -10.0,
        "bagholders": -10.0,
        "up": 4.0,
        "down": -4.0,
        "btdf": 7.0,
        "btfd": 7.0,
        "fud": 0.0,
        "diamond": 6.0,
        "paper": -6.0,
        "hands": 0.0,
        "guh": 0.0,
        "brr": 2.0,
        "brrr": 3.0,
        "brrrr": 4.0,
        "brrrrr": 5.0,
        "printer": 2.0,
        "jpow": 3.0,
        "jerome": 3.0,
        "powell": 3.0,
        "pump": -2.0,
        "dump": -8.0,
        "moon": 7.0,
        "stonks": 2.0,
        "tendies": 4.0,
    }

    sia = SIA()
    sia.lexicon.update(new_words)

    with open(BASE_DIRECTORY + '[TODO: this is where you put the directory to where the scraped text file is, from DownloadFromURL]') as myFile:
        for chunk in each_chunk(myFile, separator='-------------------------------'):
            firstline = chunk.partition(" : ")[2]
            datestring = firstline[0:10]
            # ticker = [x for x in stocks if(re.search(rf"\b{x}\b", chunk))]
            ticker = [x for x in stocks if x in chunk]
            try:
                ticker = str(ticker[0])
            except:
                continue
            if ticker == "":
                continue
            d = {}
            d['ticker'] = ticker
            d['comment_sentiment_average'] = commentSentiment(ticker, chunk, sia)
            if d['comment_sentiment_average'] == 0.000000:
                continue
            d['date'] = datestring
            # print(ticker + " " + str(d['comment_sentiment_average']) + " " + chunk)
            chunkscore = chunk.partition(" : ")[0].strip()
            try:
                chunkscoreint = int(chunkscore)
            except:
                chunkscoreint = 1
            d['score'] = chunkscoreint
            submission_statistics.append(d)

    df = pd.DataFrame(submission_statistics)
    if df.empty: 
        print("empty dataframe")
        return

    df["adj score"] = df["comment_sentiment_average"]*1.001**(df["score"])

    df2 = (df.groupby("ticker", as_index=False).mean()
        ).filter(["ticker", "adj score"])
    df_count = df["ticker"].value_counts().sort_index().reset_index()
    df_count.columns = ["ticker", "count"]
    df2["count"] = df_count.filter(["count"])
    df2["total adj score"] = df2["adj score"] * df2["count"]
    df2.sort_values(by=["total adj score"], inplace=True, ascending=False)
    
    result = [i.strip() for i in (df2.ticker.to_string(index=False)).splitlines()]

    return result[:15]

