#!/usr/bin/python3
#coding: utf-8
#totenkun

import requests
import math
import numpy as np
import pandas as pd
import time
import datetime
import logging 
import websocket
import json
import urllib
import ssl
#from util.api_key import generate_nonce, generate_signature

#定数
TESTNET = False
TIME_TERM = 5
CRYPTO_TERM = 1

REFERENCE_TIME_VALUE = 1536678000 # 2018/09/12 00:00:00
#motion_by_connect_cryptw():

class motion_by_connect_cryptw():

    def loop(self):

        while True:
            now = round(int(datetime.datetime.now().timestamp())) #小数点を除外
            mod = (now - REFERENCE_TIME_VALUE) % 300
            if mod <= 5 or mod >= 295:
                exit    
            print(str(mod))
            time.sleep(TIME_TERM)
        while True:
            if mod <= 5 or mod >= 295:
                ohlc =self.read_crypto()
                self.calculate_value(ohlc)
                now = round(int(datetime.datetime.now().timestamp())) #小数点を除外
                mod = (now - REFERENCE_TIME_VALUE) % 300
                ans =self.calculate_value(ohlc)
                self.calculate_value(ohlc)
                print(str(mod))
                time.sleep(CRYPTO_TERM)
        return ans
            
    def read_crypto(self):
        now = str(round(int(datetime.datetime.now().timestamp()))) #小数点を除外して文字列に変更
        ohlc = 0
        if TESTNET == True:
        # https://api.cryptowat.ch/markets/bitmex/btcusd-perpetual-futures/ohlc?periods=300
            r = requests.get('https://testnet.bitmex.com/api/udf/history?symbol=XBTUSD&resolution=5&from=' + str(int(now)-(300*15)) + '&to=' + now) # テストネット用
        else:
            r = requests.get('https://www.bitmex.com/api/udf/history?symbol=XBTUSD&resolution=5&from=' + str(int(now)-(300*15)) + '&to=' + now) # 実弾稼働用
        ohlc = r.json()                # JSONデータをリストに変換
        return ohlc

    def calculate_value(self,ohlc):
        high_array = np.array(ohlc['h'])[::-1]
        low_array = np.array(ohlc['l'])[::-1]
        close_array = np.array(ohlc['c'])[::-1] 
        open_array = np.array(ohlc['o'])[::-1] #tradingviewは最新が0、bitmexapiは最新が最後のため[::-1]でreverseする
        atr_length = 1
        sma_length = 1
        atr = self.return_atr(atr_length,high_array,low_array,close_array)
        sma = self.return_sma(sma_length,close_array)
        hl_line = self.calc_hl_line(atr,sma,close_array) 
        print(str(hl_line))
        
    def return_atr(self,length,high_array,low_array,close_array):
        close = close_array[2:]
        high = high_array[1:]
        low = low_array[1:]
        result = 0
        
        for i in range(length):
            tr = max(abs(high[i]- low[i]),abs(high[i]-close[i]),abs(low[i]-close[i]))
            result += tr
        result = round(result / length,1)
        return result

    def return_sma(self,length,close_array):
        if length == 1:
            ans = close_array[1]
        else:
            ans = np.convolve(close_array[0:length], np.ones((length,))/length, mode='valid') #注！未テスト
        return ans
    
    def calc_hl_line(self,atr,sma,close_array):
        close = close_array[1]
        UPRATIO = 0.6
        DOWNRATIO = 0.4
        high_line = sma + (atr * UPRATIO)
        low_line = sma - (atr * DOWNRATIO)
        return high_line,low_line

    