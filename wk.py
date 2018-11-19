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
#import threading
import concurrent.futures
import ccxt
#from sample_market_maker.market_maker.ws import ws_thread

class Main():
    
    def __init__(self):

        #### logging ####
        self.logger = log.setup_custom_logger('root')    
        self.logger.info('Wait...')
        
        #### Constant ####
        self.REFERENCE_TIME_VALUE = 1536678000 # 2018/09/12 00:00:00
        API_KEY = 'ELeP-Wfwh7pYmkc_pmPCIZ1n'
        API_SECRET = '3RrjR_AF9wIYr4N5CkXJGJcOYyB3D99VWulWmlXhJENbss06'
        ENDPOINT = 'https://www.bitmex.com/api/v1'
        self.SYMBOL = 'XBTUSD'
        SYMBOL = self.SYMBOL        
        self.market_status = "STAY"
        
        #### Create Instance #### 
        self.motion_by_connect_cryptw = totenkun.motion_by_connect_cryptw()
        self.motion_by_connect_bitmex = websocket_connect.BitMEXWebsocket(ENDPOINT,SYMBOL,API_KEY,API_SECRET)
        self.bitmex = ccxt.bitmex({'apiKey':API_KEY,'secret': API_SECRET})

        #### Experiment or TEST ####
        #executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)
        #executor.submit(self.motion_by_connect_bitmex.loop())
        #executor.submit(self.motion_by_connect_cryptw.loop())
        
        
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
    
    def buy_sell(self,side,price,pos,lot):
        self.cancel_all_orders()
        price =  self.value_set(price)

        if side == "buy" and lot - pos != 0:
            self.logger.info('side:' + format(side)+ "," + "price:" +  format(price) + ","  + "pos:"
                +  format(pos) + ","  + "lot:" + format(lot) + "market_status:" + format(self.market_status))
            self.mex_limit('buy', price,lot- pos)
            self.logger.info('----wait(buy)----')
            for x in range(0, 99, 1):
                wk_current_value = self.motion_by_connect_bitmex.recent_trade(self.SYMBOL)['price']
                wk_pos = self.motion_by_connect_bitmex.position(self.SYMBOL)['currentQty']
                wk_current_value = self.value_set(wk_current_value)
                time.sleep(0.1)
                if pos == -wk_pos:
                    self.logger.info('----buy_terminated----')
                    self.market_status = "STOP"
                    break
                if abs(wk_current_value -price) > 1:
                    self.logger.info('----emergency_withdrawal----')
                    self.market_status = "LONG"
                    break

        if side == "sell" and lot + pos != 0:
            self.logger.info('side:' + format(side)+ "," + "price:" +  format(price) + ","  + "pos:"
            +  format(pos) + ","  + "lot:" + format(lot) + "market_status:" + format(self.market_status))
        
            self.mex_limit('sell', price,lot + pos)
            self.logger.info('----wait(sell)----')
            for x in range(0, 99, 1):
                wk_current_value = self.motion_by_connect_bitmex.recent_trade(self.SYMBOL)['price']
                wk_pos = self.motion_by_connect_bitmex.position(self.SYMBOL)['currentQty']
                wk_current_value = self.value_set(wk_current_value)
                if pos == -wk_pos:
                    self.logger.info('----sell_terminated----')
                    self.market_status = "STOP"
                    break
                if abs(wk_current_value -price) > 1:
                    self.logger.info('----emergency_withdrawal----')
                    self.market_status = "SELL"
                    break
                time.sleep(0.1)
                
    #### MAIN ####
    
    def main(self):
        lot = 1
        cnt = 0
        now = round(int(datetime.datetime.now().timestamp()))
        ohlc =self.motion_by_connect_cryptw.read_crypto()
        # ans[0]:high_line , ans[1]:low_line
        ans = self.motion_by_connect_cryptw.calculate_value(ohlc)
        current_value = self.motion_by_connect_bitmex.recent_trade(self.SYMBOL)['price']
        pos = self.motion_by_connect_bitmex.position(self.SYMBOL)['currentQty']

        while True:
            now = round(int(datetime.datetime.now().timestamp()))
            if 0 <= ((now - self.REFERENCE_TIME_VALUE ) % 300) <= 5: 
                ohlc = self.motion_by_connect_cryptw.read_crypto()
                ans = self.motion_by_connect_cryptw.calculate_value(ohlc)
                self.market_status = "STAY"

            if cnt % 10 == 9:
                self.logger.info('current_value:' + format(current_value)+ "," + "high_line:" +  format(ans[0]) + ","  + "low_line:"
                +  format(ans[1]) + ","  + "pos:" + format(pos)+ ","  + "market_status:" + format(self.market_status))
                cnt = 0
            cnt = cnt + 1    
            #### MAIN LOGIC (start) ####
    
            if self.market_status != "STOP":
                if (current_value < ans[1]) or (self.market_status == "SELL"):
                    self.buy_sell("sell",current_value,pos,lot)
                elif (current_value > ans[0]) or (self.market_status == "LONG"):
                    self.buy_sell("buy",current_value,pos,lot)
            
            #### MAIN LOGIC (end) ####
            
            current_value = self.motion_by_connect_bitmex.recent_trade(self.SYMBOL)['price']
            pos = self.motion_by_connect_bitmex.position(self.SYMBOL)['currentQty']
            
            time.sleep(0.5)
            
            #time.sleep(1)で見逃したものもあるので将来的にはtime.sleep(0.5)を試してみる予定
            
if __name__ == '__main__':
    main = Main()
    main.main()
    
# 2018/10/18    
    def main(self):
        #self.cancel_all_orders() # 再起動時に備え、cancel_all_ordersはしない
        ohlc =self.motion_by_connect_cryptw.read_crypto()
        high_line = self.motion_by_connect_cryptw.calculate_value(ohlc)[0]
        low_line = self.motion_by_connect_cryptw.calculate_value(ohlc)[1]
        pos = self.motion_by_connect_bitmex.position(self.SYMBOL)['currentQty']
        current_value = self.motion_by_connect_bitmex.recent_trade(self.SYMBOL)['price']
        cnt = 0
        while True:
            try:
                now = datetime.datetime.now()
                #m = now.minute
                s = now.second
                #if m % 10 == 0 or m % 10 == 5: # 5minute
                if s % 60 == 0 : # 1minute
                    self.cancel_all_orders()
                    ohlc =self.motion_by_connect_cryptw.read_crypto()
                    high_line = self.motion_by_connect_cryptw.calculate_value(ohlc)[0]
                    low_line = self.motion_by_connect_cryptw.calculate_value(ohlc)[1]
                    pos = self.motion_by_connect_bitmex.position(self.SYMBOL)['currentQty']
                    current_value = self.motion_by_connect_bitmex.recent_trade(self.SYMBOL)['price']
                    if pos < 0:
                        self.logger.info("buy:" + "high_line:" +  format(self.value_set(high_line)) + ","  + "lot - pos:" +  format(self.lot - pos))
                        self.mex_limit('buy',self.value_set(high_line),self.lot - pos)
                    elif pos > 0:
                        self.logger.info("sell:" + "low_line:" +  format(self.value_set(low_line)) + ","  + "lot + pos:" +  format(self.lot + pos))
                        self.mex_limit('sell',self.value_set(low_line),self.lot + pos)
                    elif pos == 0:
                        self.mex_limit('buy',self.value_set(high_line),self.lot - pos)
                        self.mex_limit('sell',self.value_set(low_line),self.lot + pos)
                        self.logger.info("sell:" + "low_line:" +  format(self.value_set(low_line)) + ","  + "lot + pos:" +  format(self.lot + pos))
                        self.logger.info("buy:" + "high_line:" +  format(self.value_set(high_line)) + ","  + "lot - pos:" +  format(self.lot - pos))
                    
                    #time.sleep(60) # 5minute
                    time.sleep(10) # 1minute
                    
                if cnt % 100 == 99:
                    self.logger.info('current_value:' + format(current_value)+ "," + "high_line:" +  format(high_line) + ","  + "low_line:"
                        +  format(low_line) + ","  + "pos:" + format(pos))
                    cnt = 0
                cnt = cnt + 1
                
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


            '''
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
                '''
    def main(self):

        # init
        self.status = "STAY"
        self.request = "NOTHING"
        _high_line = 0
        _low_line = 0

        # for log
        self.cnt = 0 

        while True:
            try:
                # high_line_small,low_line_smallを取得
                #now = datetime.datetime.now()
                ohlc =self.motion_by_connect_cryptw.read_crypto()
                high_line = self.motion_by_connect_cryptw.calculate_value(ohlc)[0]
                low_line = self.motion_by_connect_cryptw.calculate_value(ohlc)[1]
                pos = self.motion_by_connect_bitmex.position(self.SYMBOL)['currentQty']
                current_value = self.motion_by_connect_bitmex.recent_trade(self.SYMBOL)['price']
                
                # self.request posと価格の状況に合わせて"NOTHING","SELL","BUY"を設定
                if pos < 0 and current_value > high_line:
                    self.request ="BUY"
                elif pos > 0 and current_value > high_line:
                    self.request ="NOTHING"
                elif pos > 0 and current_value < low_line:
                    self.request ="SELL"
                elif pos < 0 and current_value < low_line:
                    self.request ="NOTHING"
                elif pos == 0:
                    self.request ="BUY"
    
                # 売買処理の状況に合わせて"STAY","WAIT","READY","EMERGE"を設定
                if self.request != "NOTHING":
                    self.status = "WAIT"
                
                # 基本は指値
                if self.request == "BUY" and self.status == "WAIT" and current_value > high_line + 0.5:
                    self.status ="READY"
                    _high_line = high_line # high_lineは可変である為、_high_lineを使用する
                elif self.request == "SELL" and self.status == "WAIT" and current_value < low_line - 0.5:
                    self.status ="READY"
                    _low_line  = low_line # low_lineは可変である為、_low_lineを使用する
                elif self.request == "BUY" and self.status == "WAIT" and pos == 0:
                    self.status ="READY"
                    _high_line = high_line # high_lineは可変である為、_high_lineを使用する
                
                # 指値で準備中に逆値で伸びた時に成行で売買する
                if self.status == "READY" and current_value > _high_line + 5: # EMERGEの+-5の妥当性については検証中
                    self.status ="EMERGE"
                
                if self.status == "READY" and current_value < _low_line - 5:
                    self.status ="EMERGE"
                
                if self.status =="EMERGE" and self.request == "BUY":
                    pos = self.motion_by_connect_bitmex.position(self.SYMBOL)['currentQty']
                    self.cancel_all_orders() 
                    self.logger.info("buy:" + "high_line:" +  format(self.value_set(high_line)) + ","  + "lot - pos:" 
                    +  format(self.lot - pos) + ","  + "status:" + format(self.status) + ","  + "request:" + format(self.request))
                    self.mex_market('buy',self.lot - pos)
                    self.status ="WAIT" 
                if self.status =="EMERGE" and self.request == "SELL":
                    pos = self.motion_by_connect_bitmex.position(self.SYMBOL)['currentQty']
                    self.cancel_all_orders() 
                    self.logger.info("sell:" + "low_line:" +  format(self.value_set(low_line)) + ","  + "lot + pos:" 
                    +  format(self.lot + pos) + ","  +"status:" + format(self.status) + ","  + "request:" + format(self.request))
                    self.mex_limit('buy',self.value_set(high_line),self.lot - pos)
                    self.status ="WAIT"
    
                # ステータスが"READY"の時指値
                if self.status =="READY" and self.request == "BUY":
                    self.logger.info("buy:" + "high_line:" +  format(self.value_set(_high_line)) + ","  + "lot - pos:" 
                    +  format(self.lot - pos) + ","  + "status:" + format(self.status) + ","  + "request:" + format(self.request))
                    self.mex_limit('buy',self.value_set(_high_line),self.lot - pos)
                    self.status ="WAIT"
                if self.status =="READY" and self.request == "SELL":
                    self.logger.info("sell:" + "low_line:" +  format(self.value_set(_low_line)) + ","  + "lot + pos:" 
                    +  format(self.lot + pos) + ","  + "status:" + format(self.status) + ","  + "request:" + format(self.request))
                    self.mex_limit('sell',self.value_set(_low_line),self.lot + pos)
                    self.status ="WAIT"
                    
                # self.status == "WAIT"がないと-403エラーを吐き出します
                if self.request == "NOTHING" and self.status == "WAIT" and abs(pos) == self.lot: 
                    self.cancel_all_orders() # bitmexに接続しすぎると-403エラーを吐き出します
                    self.status ="STAY"
                    
                # 通常時
                if self.cnt % 10 == 9:
                    self.logger.info('current_value:' + format(current_value)+ "," + "high_line:" +  format(high_line) + ","  + "low_line:"
                        +  format(low_line) + ","  + "pos:" + format(pos) + "," + "status:" + format(self.status) + "," + "request:" + format(self.request))
                    self.cnt = 0
                self.cnt = self.cnt + 1
    
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
#!/usr/bin/python3
#coding: utf-8
#execute_totenkun.py

import json
#import logging
#import logging.handlers 
import log
import wk
#import websocket_connect
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
        API_KEY = '2jGLTxlqDt0ajmVjzf4DGw_T'
        API_SECRET = 's6PotvlvsVMPHWZP71bvfRB5t3um22P3HWgw1mM-PcPxvajK'
        ENDPOINT = 'https://www.bitmex.com/api/v1'
        self.SYMBOL = 'XBTUSD'
        SYMBOL = self.SYMBOL
        self.lot = 1
        #### Create Instance #### 
        self.motion_by_connect_cryptw = wk.motion_by_connect_cryptw()
        #self.motion_by_connect_bitmex = websocket_connect.BitMEXWebsocket(ENDPOINT,SYMBOL,API_KEY,API_SECRET)
        #self.bitmex = ccxt.bitmex({'apiKey':API_KEY,'secret': API_SECRET})
        #### Experiment or TEST ####

    #### Define ####
    #def cancel_all_orders(self,**options):
    #    try:
    #        orders = self.bitmex.privateDeleteOrderAll(options)
    #        return orders
    #    except Exception as e:
    #        print(e)
    #        return[]
            
    #def mex_limit(self,side, price, size): # 指値発注用の関数
        #o = self.bitmex.create_order('BTC/USD', type='limit', side=side, amount=size, price=price)
        #self.logger.info(o['info']['ordType'] + ' ' + o['info']['side'] + ' ' + str(o['info']['orderQty']) + ' @ ' + str(o['info']['price']) + ' ' + o['id'])

    #def mex_market(self,side, size): # 成行発注用の関数
    #    o = self.bitmex.create_order('BTC/USD', type='market', side=side, amount=size)
    #    self.logger.info(o['info']['ordType'] + ' ' + o['info']['side'] + ' ' + str(o['info']['orderQty']) + ' ' + o['id'])

    def value_set(self,price):
        return (round(price*2,0))/2      

    #### MAIN ####

    def main(self):
        #self.cancel_all_orders() # 再起動時に備え、cancel_all_ordersはしない
        ohlc =self.motion_by_connect_cryptw.read_crypto()
        high_line = self.motion_by_connect_cryptw.calculate_value(ohlc)[0]
        low_line = self.motion_by_connect_cryptw.calculate_value(ohlc)[1]
        #pos = self.motion_by_connect_bitmex.position(self.SYMBOL)['currentQty']
        #current_value = self.motion_by_connect_bitmex.recent_trade(self.SYMBOL)['price']

        while True:
            now = datetime.datetime.now()
            #m = now.minute
            s = now.second
            #if m % 10 == 0 or m % 10 == 5: # 5minute
            if s % 60 == 0 : # 1minute
                #self.cancel_all_orders()
                ohlc =self.motion_by_connect_cryptw.read_crypto()
                high_line = self.motion_by_connect_cryptw.calculate_value(ohlc)[0]
                low_line = self.motion_by_connect_cryptw.calculate_value(ohlc)[1]
                #pos = self.motion_by_connect_bitmex.position(self.SYMBOL)['currentQty']
                #current_value = self.motion_by_connect_bitmex.recent_trade(self.SYMBOL)['price']
                #if pos < 0:
                #    self.logger.info("buy:" + "high_line:" +  format(self.value_set(high_line)) + ","  + "lot - pos:" +  format(self.lot - pos))
                #    self.mex_limit('buy',self.value_set(high_line),self.lot - pos)
                #elif pos > 0:
                #    self.logger.info("sell:" + "low_line:" +  format(self.value_set(low_line)) + ","  + "lot + pos:" +  format(self.lot + pos))
                #    self.mex_limit('sell',self.value_set(low_line),self.lot + pos)
                #elif pos == 0:
                #    self.mex_limit('buy',self.value_set(high_line),self.lot - pos)
                #    self.mex_limit('sell',self.value_set(low_line),self.lot + pos)
                #    self.logger.info("sell:" + "low_line:" +  format(self.value_set(low_line)) + ","  + "lot + pos:" +  format(self.lot + pos))
                #    self.logger.info("buy:" + "high_line:" +  format(self.value_set(high_line)) + ","  + "lot - pos:" +  format(self.lot - pos))
                
                #time.sleep(60) # 5minute
                time.sleep(10) # 1minute
                
            self.logger.info("high_line:" +  format(high_line) + ","  + "low_line:"
                +  format(low_line))

            #time.sleep(1) # 5minute
            time.sleep(0.1) # 1minute
                
if __name__ == '__main__':
    main = Main()
    main.main()
