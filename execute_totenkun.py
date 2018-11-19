#!/usr/bin/python3
#coding: utf-8
#execute_totenkun.py

import json
#import logging
#import logging.handlers 
import log
import totenkun
import websocket_connect
import datetime
import time
import ccxt
#from sample_market_maker.market_maker.ws import ws_thread


class Main():
    
    def __init__(self):

        #### logging ####
        self.logger = log.setup_custom_logger('root')    
        self.logger.info('Wait...')
        
        #### Constant ####
        self.REFERENCE_TIME_VALUE = 1536678000 # 2018/09/12 00:00:00
        #API_KEY = '2jGLTxlqDt0ajmVjzf4DGw_T'
        #API_SECRET = 's6PotvlvsVMPHWZP71bvfRB5t3um22P3HWgw1mM-PcPxvajK'
        API_KEY = 'bQz_JX6S7rHTl98LcsMw8tdS'
        API_SECRET = 'wc3vCSy8CfFITO5I2gGdswxK1JuBabBpksTr1DwO6j9ZrCNl'
        ENDPOINT = 'https://www.bitmex.com/api/v1'
        self.SYMBOL = 'XBTUSD'
        SYMBOL = self.SYMBOL
        self.lot = 500 # 0.025BTX以下は禁止
        #### Create Instance #### 
        self.motion_by_connect_cryptw = totenkun.motion_by_connect_cryptw()
        self.motion_by_connect_bitmex = websocket_connect.BitMEXWebsocket(ENDPOINT,SYMBOL,API_KEY,API_SECRET)
        self.bitmex = ccxt.bitmex({'apiKey':API_KEY,'secret': API_SECRET})
        #### Experiment or TEST ####

        #### Help Error ####
        self.INTERVAL = 0.0004    # mmbot化する時に使う数値。通常は使いません。
        self.STOP_FOUND_ERR = True # 一定時間に多数エラーが検出されたときに停止するかのフラグ
        self.ERR_LIMIT_5MIN = 20   # 5分当たり許容エラー件数
        self.ERR_LIMIT_1HOUR = 150 # 1時間当たり許容エラー件数
        self.CRITICAL_ERRORS = ['Invalid orderQty','Available Balance', 'Forbidden'] # 検出したら即停止のエラー
        self.IGNORE_ERRORS = ['overloaded', '502 Server Error', 'Read timed out'] # 検出しても回数にカウントしないエラー
        #### Parameter ####
        self.err_cnt_total, self.err_cnt_hour, self.err_cnt_5minute = (0,0,0) # エラーカウンタ
        self.last_reported_time = datetime.datetime.now() # レポート通知最終時刻（時足エラーカウントクリアにも併用）
        self.last_err_cnt_5minute_clear_time = datetime.datetime.now() # 分速エラーカウントクリア最終時刻



    #### Define ####
    def cancel_all_orders(self,**options):
        try:
            orders = self.bitmex.privateDeleteOrderAll(options)
            return orders
        except Exception as e:
            print(e)
            return[]
            
    def mex_limit(self,side, price, size): # 指値発注用の関数
        o = self.bitmex.create_order('BTC/USD', type='limit', side=side, amount=size, price=price)
        self.logger.info(o['info']['ordType'] + ' ' + o['info']['side'] + ' ' + str(o['info']['orderQty']) + ' @ ' + str(o['info']['price']) + ' ' + o['id'])

    def mex_market(self,side, size): # 成行発注用の関数
        o = self.bitmex.create_order('BTC/USD', type='market', side=side, amount=size)
        self.logger.info(o['info']['ordType'] + ' ' + o['info']['side'] + ' ' + str(o['info']['orderQty']) + ' ' + o['id'])

    def value_set(self,price):
        return (round(price*2,0))/2      

    #### MAIN ####

    def main(self):
        cnt = 0
        s = 0
        _low_line = 0
        _high_line = 0
        ask = "NOTHING"
        status = "STAY"
        self.cancel_all_orders() 
        ohlc =self.motion_by_connect_cryptw.read_crypto()
        high_line = self.motion_by_connect_cryptw.calculate_value(ohlc)[0]
        low_line = self.motion_by_connect_cryptw.calculate_value(ohlc)[1]

        while True:
            try:
                pos = self.motion_by_connect_bitmex.position(self.SYMBOL)['currentQty']
                current_value = self.motion_by_connect_bitmex.recent_trade(self.SYMBOL)['price']
                
                # high_line,low_lineを取得(アクセス回数を少なくしないとapi制限に掛かる)
                # 再起動時に備え、cancel order はしない
                now = datetime.datetime.now()
                s = now.second
                if s % 60 == 0 : # 1minute
                    ohlc =self.motion_by_connect_cryptw.read_crypto()
                    high_line = self.motion_by_connect_cryptw.calculate_value(ohlc)[0]
                    low_line = self.motion_by_connect_cryptw.calculate_value(ohlc)[1]
                
                # 売買ロジック
                # ask:NOTHING,SELL,BUY
                # state:STAY,LIMIT,MARKET,WAIT
                if pos <= 0 and current_value > high_line and status == "STAY" :
                    ask = "BUY"
                    status = "LIMIT"
                elif pos >= 0 and current_value < low_line and status == "STAY":
                    ask = "SELL"
                    status = "LIMIT"

                # オーダー解除_01
                if pos == self.lot * (-1) and status == "WAIT" and ask == "SELL":
                    ask = "NOTHING"
                    status = "WAIT"
                elif pos == self.lot and status == "WAIT" and ask == "BUY":
                    ask = "NOTHING"
                    status = "WAIT"

                # オーダー解除_02 
                if current_value < low_line and status == "WAIT" and ask == "BUY":
                    ask = "NOTHING"
                    status = "WAIT"
                elif current_value > high_line and status == "WAIT" and ask == "SELL":
                    ask = "NOTHING"
                    status = "WAIT"

                # オーダー解除_03
                if abs(pos) == self.lot and status == "MARKET" and ask == "NOTHING":
                    ask = "NOTHING"
                    status = "WAIT"

                # オーダーキャンセル
                if status == "WAIT" and ask == "NOTHING": 
                    self.cancel_all_orders() 
                    _low_line = 0
                    _high_line = 0
                    status = "STAY"

                # LIMIT
                if ask == "BUY" and status == "LIMIT":
                    self.logger.info('01:' + "," +'current_value:' + format(current_value)+ "," + "high_line:" +  format(high_line) + ","  + "low_line:"
                        +  format(low_line) + ","  + "pos:" + format(pos) + ","  + "ask:" + format(ask) + ","  + "status:" + format(status)
                        + ","  + "_h_l:" + format(_high_line) + ","  + "_l_l:" + format(_low_line))
                    self.mex_limit('buy',self.value_set(high_line) - 0.5,self.lot - pos)
                    _high_line = self.value_set(high_line) - 0.5
                    status ="WAIT"
                if ask == "SELL" and status == "LIMIT":
                    self.logger.info('02:' + "," +'current_value:' + format(current_value)+ "," + "high_line:" +  format(high_line) + ","  + "low_line:"
                        +  format(low_line) + ","  + "pos:" + format(pos) + ","  + "ask:" + format(ask) + ","  + "status:" + format(status)
                        + ","  + "_h_l:" + format(_high_line) + ","  + "_l_l:" + format(_low_line))
                    self.mex_limit('sell',self.value_set(low_line) + 0.5,self.lot + pos)
                    _low_line = self.value_set(low_line) + 0.5
                    status ="WAIT"

                # MARKET
                # _low_lineが初期化されないことによる唐突な注文を避けるために_low_line != 0を追加
                if status == "WAIT" and ask == "SELL" and _low_line - current_value > 5 and _low_line != 0:
                    status = "MARKET"
                elif status == "WAIT" and ask == "BUY" and current_value - _high_line > 5 and _high_line != 0:
                    status = "MARKET"

                if status == "MARKET" and ask == "SELL":
                    self.cancel_all_orders() 
                    self.logger.info('03:' + "," +'current_value:' + format(current_value)+ "," + "high_line:" +  format(high_line) + ","  + "low_line:"
                        +  format(low_line) + ","  + "pos:" + format(pos) + ","  + "ask:" + format(ask) + ","  + "status:" + format(status)
                        + ","  + "_h_l:" + format(_high_line) + ","  + "_l_l:" + format(_low_line))
                    self.mex_market('sell',self.lot + pos)
                    ask = "NOTHING"
                    time.sleep(5)

                elif status == "MARKET" and ask == "BUY":
                    self.cancel_all_orders() 
                    self.logger.info('04:' + "," +'current_value:' + format(current_value)+ "," + "high_line:" +  format(high_line) + ","  + "low_line:"
                        +  format(low_line) + ","  + "pos:" + format(pos) + ","  + "ask:" + format(ask) + ","  + "status:" + format(status)
                        + ","  + "_h_l:" + format(_high_line) + ","  + "_l_l:" + format(_low_line))
                    self.mex_market('buy',self.lot + pos)
                    ask = "NOTHING"
                    time.sleep(5)

                # log出力タイミングを制御
                if cnt % 100 == 99:
                    self.logger.info('05:' + "," +'current_value:' + format(current_value)+ "," + "high_line:" +  format(high_line) + ","  + "low_line:"
                        +  format(low_line) + ","  + "pos:" + format(pos) + ","  + "ask:" + format(ask) + ","  + "status:" + format(status)
                        + ","  + "_h_l:" + format(_high_line) + ","  + "_l_l:" + format(_low_line))
                    self.cnt = 0
                cnt = cnt + 1
                #self.logger.info('current_value:' + format(current_value)+ "," + "high_line:" +  format(high_line) + ","  + "low_line:"
                #    +  format(low_line) + ","  + "pos:" + format(pos) + ","  + "ask:" + format(ask) + ","  + "status:" + format(status))
                
                #time.sleep(1) # 5minute
                time.sleep(0.1) # 1minute

            except Exception as x:
                for ignore_error in self.IGNORE_ERRORS:
                    if ignore_error in str(x):
                        self.logger.info('混雑中')
                        time.sleep(3)
                        break
                else:
                    continue
                self.logger.info("Error!")
                self.logger.exception(x)
                        # エラーカウントインクリメント
                self.err_cnt_total += 1
                self.err_cnt_hour += 1
                self.err_cnt_5minute += 1
                # エラー件数が5分当たりERR_LIMIT_5MIN件、時間あたりERR_LIMIT_1HOUR件のどちらかを超えると、アラートを出します
                # STOP_FOUND_ERR���Trueの場合は24時間処理を停止します
                if self.err_cnt_5minute > self.ERR_LIMIT_5MIN or self.err_cnt_hour > self.ERR_LIMIT_1HOUR :
                    message = \
                        "BOT連続エラーを検出しました！\n累積Err:{total}\n時台Err:{hour}\n5分台Err{minute}" \
                        .format(total=self.err_cnt_total, hour=self.err_cnt_hour, minute=self.err_cnt_5minute)
                    #if LINETOKEN != '':
                    #    linemsg(message)
                    #if DISCORDURL != '':
                    #    discord(message)
                    self.logger.info(message)
                    if self.STOP_FOUND_ERR :
                        message = "多数エラー検出のため、BOTを24時間停止します"
                    #    if LINETOKEN != '':
                    #        linemsg(message)
                    #    if DISCORDURL != '':
                    #        discord(message)
                        self.logger.info(message)
                        time.sleep(86400)
                else:
                    for critical_error in self.CRITICAL_ERRORS :
                        if critical_error in str(x):
                            message = "即停止対象エラー[{critical}]を検知しました".format(critical=critical_error)
                            #if LINETOKEN != '':
                            #    linemsg(message)
                            #if DISCORDURL != '':
                            #    discord(message)
                            self.logger.info(message)
                            if self.STOP_FOUND_ERR :
                                message = "即停止エラー検出のため、BOTを24時間停止します"
                                #if LINETOKEN != '':
                                #    linemsg(message)
                                #if DISCORDURL != '':
                                #    discord(message)
                                self.logger.info(message)
                                time.sleep(86400)
                time.sleep(30)

if __name__ == '__main__':
    main = Main()
    main.main()
