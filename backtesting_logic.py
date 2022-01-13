import alpaca_trade_api as tradeapi
import numpy as np
import matplotlib.pyplot as plt
from binance.client import Client, BinanceAPIException
from datetime import timedelta, date, datetime
from django.db.models import Sum
import pandas as pd
import json
import random
import requests
import sys
import time
from pytz import timezone

BASE_URL = "https://data.alpaca.markets/"
auth = (alpaca_trading_token, alpaca_trading_key)
binance_client = Client(binance_bot_key, binance_bot_secret, testnet=False, tld='us')

## NOTE: a few things. In order to use the below backtester, you'll need API keys from Alpaca (to fill in the variables in line 17) and from Binance (to fill in the variables in line 18)

## NOTE: here's a few example runs of the backtester function:

# backtester({'2021-12-15': [('UPRO', 100, False)]}, 100)
# backtester({'2021-12-15': [('solana', 50, True), 
#                                      ('bitcoin', 50, True)],
#                      '2021-12-01': [('bitcoin', 50, True), 
#                                      ('ethereum', 50, True)]}, 100)


def backtest_assets_binance(start_money, start_date, end_date, assets, **kwargs):
    user_display = kwargs.get('user_display', False)
    total_value_per_asset = {}
    for asset in assets:
        ticker = asset['asset']
        backtest_df = binance_client.get_historical_klines(ticker, Client.KLINE_INTERVAL_1DAY, start_date, end_date)
        prop = 0
        if not user_display:
            prop = asset['proportion']
        initial_price = float(backtest_df[0][1])
        ticker_prices = []
        # ticker_prices.append(initial_price * initial_quantity)
        if user_display:
            initial_quantity = float(asset['quantity'])
        else:
            initial_quantity = start_money * float(prop) / initial_price
        for i in backtest_df:
            ticker_prices.append((float(i[4]) * initial_quantity, "day"))
        total_value_per_asset[ticker] = ticker_prices
    return total_value_per_asset

def backtest_assets_alpaca(start_money, start_date, end_date, assets, **kwargs):
    user_display = kwargs.get('user_display', False)
    total_value_per_asset = {}
    for asset in assets:
        ticker = asset['asset']
        # HIST_DATA_URL = BASE_URL + f"v2/stocks/{ticker}/bars?start={start_date}&end={end_date}&timeframe=1Day&adjustment=all"
        # TODO: I got rid of the end_date param here but bring back when we get the data plan
        HIST_DATA_URL = BASE_URL + f"v2/stocks/{ticker}/bars?start={start_date}&timeframe=1Day&adjustment=all"
        prop = 0
        if not user_display:
            prop = asset['proportion']
        ticker_prices = []
        try:
            r = requests.get(HIST_DATA_URL, auth=auth).text
            backtest_df = pd.DataFrame(json.loads(r)["bars"], columns=['t', 'o', 'h', 'l', 'c'])
        except KeyError:
                print("Error:")
                print(r)
                continue
        backtest_df.rename(columns={"t": "time", "o": "open", "h": "high", "l": "low", "c": "close"}, inplace=True)
        idx = pd.date_range(start_date + str("T05:00:00Z"), end_date + str("T05:00:00Z"))
        try:
            initial_price = backtest_df['open'].iloc[0]
        except IndexError:
                if user_display:
                    raise Exception(f"User's current asset {ticker} is no longer on Alpaca")
                else:
                    print(f"Alpaca doesn't have asset {ticker}'s data. Assuming cash position.")
                    for i in idx:
                        ticker_prices.append((start_money * prop, i.strftime('%Y-%m-%d')))
                total_value_per_asset[ticker] = ticker_prices
                print(f"ticker prices for {ticker}: {ticker_prices}")
                # TODO: gotta throw an error here right
                continue
        backtest_df.time = pd.to_datetime(backtest_df.time)
        for i in list(idx):
                if(i not in list(backtest_df.time)):
                    backtest_df = backtest_df.append({'time': i}, ignore_index=True)
        backtest_df = backtest_df.sort_values(by=['time'])
        backtest_df.ffill(inplace=True)
        backtest_df.backfill(inplace=True)
        if user_display:
            initial_quantity = float(asset['quantity'])
        else:
            initial_quantity = start_money * float(prop) / initial_price
        for index, day in backtest_df.iterrows():
            ticker_prices.append((day['close'] * initial_quantity, day['time'].strftime('%Y-%m-%d')))
        total_value_per_asset[ticker] = ticker_prices
        
    return total_value_per_asset
    
def backtest_assets_coingecko(start_money, start_timestamp, end_timestamp, asset):
    ticker = asset['asset']
    prop = asset['proportion']
    res = json.loads(requests.get(f"https://api.coingecko.com/api/v3/coins/{ticker}/market_chart/range?vs_currency=USD&from={int(datetime.timestamp(start_timestamp))}&to={int(datetime.timestamp(end_timestamp))}").text)
    initial_price = 0
    initial_quantity = 0
    ticker_prices = []
    total_value_per_asset = {}
    for index, i in enumerate(res['prices']):
        try:
            # coingecko doesn't let you choose date range (granualarity is automatically hourly or daily or minutely,
            # so we have to just make it daily ourselves)
            curr_date = datetime.fromtimestamp(res['prices'][index][0] / 1000).date() # datetime.strptime(res['prices'][index][0], '%Y-%m-%d').date()
            next_date = datetime.fromtimestamp(res['prices'][index + 1][0] / 1000).date()
            if(curr_date != next_date): # aka we're on the last record for the current date
                if(not ticker_prices):
                    initial_price = res['prices'][index][1]
                    initial_quantity = start_money * float(prop) / initial_price
                ticker_prices.append([res['prices'][index][1] * initial_quantity, curr_date])
        except IndexError:
            ticker_prices.append([res['prices'][index][1] * initial_quantity, curr_date])
            total_value_per_asset[ticker] = ticker_prices
    return total_value_per_asset


def backtester(positions, initial_money):
    # TODO: known error: if you have an end time on a weekend, weird things happen (prob start time too)
    returns = []
    start_money = initial_money
    for index, i in enumerate(sorted(positions.keys())):
        allocations = positions[i]
        start_date = datetime.strptime(i, '%Y-%m-%d').date()
        total_value_per_asset = {}
        try:
            end_date = datetime.strptime(sorted(positions.keys())[index + 1], '%Y-%m-%d').date()
            # print(end_date)
        except:
            end_date = date.today() - timedelta(days = 2)
            # end_date = datetime.strptime("2021-10-13", '%Y-%m-%d').date()
        
        for asset in allocations:
            crypto = asset[2]
            prop = asset[1] / 100
            ticker = asset[0]
            if crypto:
                start_timestamp = datetime.combine(start_date, datetime.min.time())
                end_timestamp = datetime.combine(end_date, datetime.max.time())
                asset = {'asset': ticker, 'proportion': prop}
                # total_value_per_asset[ticker] = backtest_assets_coingecko(start_money, start_timestamp, end_timestamp, asset)
                total_value_per_asset = total_value_per_asset | backtest_assets_coingecko(start_money, start_timestamp, end_timestamp, asset)
                
            else:
                end_date = end_date - timedelta(days=2) # TODO: change this once we get unlimited data
                end_date = end_date.strftime('%Y-%m-%d')
                start_date = start_date.strftime('%Y-%m-%d')
                assets = [{'asset': ticker, 'proportion': prop}]
                total_value_per_asset = total_value_per_asset | backtest_assets_alpaca(start_money, start_date, end_date, assets)
                    
        total_fund_value = []

        for data in total_value_per_asset.values():
            if not total_fund_value:
                for i in data:
                    total_fund_value.append([i[0], i[1]])
            else:
                for index, i in enumerate(data):
                    total_fund_value[index][0] += i[0]
            
        for i in total_fund_value:
            returns.append(i)
        # print(returns)
        # print("\n\n")
        start_money = total_fund_value[-1][0]
        time.sleep(5)
    # print(returns)
    return returns
  
