from keys import api, secret
from binance.um_futures import UMFutures
import ta
import pandas as pd
from time import sleep
from binance.error import ClientError
from tradingview_ta import  TA_Handler, Interval

client = UMFutures(key = api, secret=secret)

# 0.012 means +1.2%, 0.009 is -0.9%
tp = 0.05
sl = 0.05
volume = 20
leverage = 5
type = 'ISOLATED'
qty = 100  # Amount of concurrent opened positions

# getting your futures balance in USDT
def get_balance_usdt():
    try:
        response = client.balance(recvWindow=6000)
        for elem in response:
            if elem['asset'] == 'USDT':
                return float(elem['balance'])

    except ClientError as error:
        print(
            "Found error. status: {}, error code: {}, error message: {}".format(
                error.status_code, error.error_code, error.error_message
            )
        )


# Getting all available symbols on the Futures ('BTCUSDT', 'ETHUSDT', ....)
def get_tickers_usdt():
    tickers = []
    resp = client.ticker_price()
    for elem in resp:
        if 'USDT' in elem['BTC']:
            tickers.append(elem['BTC'])
    return tickers


# Getting candles for the needed symbol, its a dataframe with 'Time', 'Open', 'High', 'Low', 'Close', 'Volume'
def klines(symbol):
    try:
        resp = pd.DataFrame(client.klines(symbol, '15m'))
        resp = resp.iloc[:,:6]
        resp.columns = ['Time', 'Open', 'High', 'Low', 'Close', 'Volume']
        resp = resp.set_index('Time')
        resp.index = pd.to_datetime(resp.index, unit = 'ms')
        resp = resp.astype(float)
        return resp
    except ClientError as error:
        print(
            "Found error. status: {}, error code: {}, error message: {}".format(
                error.status_code, error.error_code, error.error_message
            )
        )

# Set leverage for the needed symbol. You need this bcz different symbols can have different leverage
def set_leverage(symbol, level):
    try:
        response = client.change_leverage(
            symbol=symbol, leverage=level, recvWindow=6000
        )
        print(response)
    except ClientError as error:
        print(
            "Found error. status: {}, error code: {}, error message: {}".format(
                error.status_code, error.error_code, error.error_message
            )
        )


# The same for the margin type
def set_mode(symbol, type):
    try:
        response = client.change_margin_type(
            symbol=symbol, marginType=type, recvWindow=6000
        )
        print(response)
    except ClientError as error:
        print(
            "Found error. status: {}, error code: {}, error message: {}".format(
                error.status_code, error.error_code, error.error_message
            )
        )


# Price precision. BTC has 1, XRP has 4
def get_price_precision(symbol):
    resp = client.exchange_info()['symbols']
    for elem in resp:
        if elem['symbol'] == symbol:
            return elem['pricePrecision']


# Amount precision. BTC has 3, XRP has 1
def get_qty_precision(symbol):
    resp = client.exchange_info()['symbols']
    for elem in resp:
        if elem['symbol'] == symbol:
            return elem['quantityPrecision']


# Open new order with the last price, and set TP and SL:
def open_order(symbol, side):
    price = float(client.ticker_price(symbol)['price'])
    qty_precision = get_qty_precision(symbol)
    price_precision = get_price_precision(symbol)
    qty = round(volume/price, qty_precision)
    if side == 'buy':
        try:
            resp1 = client.new_order(symbol=symbol, side='BUY', type='LIMIT', quantity=qty, timeInForce='GTC', price=price)
            print(symbol, side, "placing order")
            print(resp1)
            sleep(2)
            sl_price = round(price - price*sl, price_precision)
            resp2 = client.new_order(symbol=symbol, side='SELL', type='STOP_MARKET', quantity=qty, timeInForce='GTC', stopPrice=sl_price)
            print(resp2)
            sleep(2)
            tp_price = round(price + price * tp, price_precision)
            resp3 = client.new_order(symbol=symbol, side='SELL', type='TAKE_PROFIT_MARKET', quantity=qty, timeInForce='GTC',
                                     stopPrice=tp_price)
            print(resp3)
        except ClientError as error:
            print(
                "Found error. status: {}, error code: {}, error message: {}".format(
                    error.status_code, error.error_code, error.error_message
                )
            )
    if side == 'sell':
        try:
            resp1 = client.new_order(symbol=symbol, side='SELL', type='LIMIT', quantity=qty, timeInForce='GTC', price=price)
            print(symbol, side, "placing order")
            print(resp1)
            sleep(2)
            sl_price = round(price + price*sl, price_precision)
            resp2 = client.new_order(symbol=symbol, side='BUY', type='STOP_MARKET', quantity=qty, timeInForce='GTC', stopPrice=sl_price)
            print(resp2)
            sleep(2)
            tp_price = round(price - price * tp, price_precision)
            resp3 = client.new_order(symbol=symbol, side='BUY', type='TAKE_PROFIT_MARKET', quantity=qty, timeInForce='GTC',
                                     stopPrice=tp_price)
            print(resp3)
        except ClientError as error:
            print(
                "Found error. status: {}, error code: {}, error message: {}".format(
                    error.status_code, error.error_code, error.error_message
                )
            )
# Your current positions (returns the symbols list):
def get_pos():
    try:
        resp = client.get_position_risk()
        pos = []
        for elem in resp:
            if float(elem['positionAmt']) != 0:
                pos.append(elem['symbol'])
        return pos
    except ClientError as error:
        print(
            "Found error. status: {}, error code: {}, error message: {}".format(
                error.status_code, error.error_code, error.error_message
            )
        )

def check_orders():
    try:
        response = client.get_orders(recvWindow=6000)
        sym = []
        for elem in response:
            sym.append(elem['BTC'])
        return sym
    except ClientError as error:
        print(
            "Found error. status: {}, error code: {}, error message: {}".format(
                error.status_code, error.error_code, error.error_message
            )
        )

# Close open orders for the needed symbol. If one stop order is executed and another one is still there
def close_open_orders(symbol):
    try:
        response = client.cancel_open_orders(symbol=symbol, recvWindow=6000)
        print(response)
    except ClientError as error:
        print(
            "Found error. status: {}, error code: {}, error message: {}".format(
                error.status_code, error.error_code, error.error_message
            )
        )

def rsi_signal(symbol):
    coin = TA_Handler(
        symbol=symbol+"USDT",
        screener="crypto",
        exchange="BINANCE",
        interval=Interval.INTERVAL_4_HOUR
    )
    kl = klines(symbol)
    data = coin.get_analysis().indicators
    data_indicator_rsi = data['RSI']
    data_indicator_rsi_1 = data['RSI[1]']
    if data_indicator_rsi > data_indicator_rsi_1:
        return 'up'
    elif data_indicator_rsi < data_indicator_rsi_1:
        return 'down'
    else:
        return 'neutral'

symbols = get_tickers_usdt()

while True:
    # we need to get balance to check if the connection is good, or you have all the needed permissions
    balance = get_balance_usdt()
    sleep(1)
    if balance == None:
        print('Cant connect to API. Check IP, restrictions or wait some time')
    if balance != None:
        print("My balance is: ", balance, " USDT")
        pos = []
        pos = get_pos()
        print(f'You have {len(pos)} opened positions:\n{pos}')
        ord = []
        ord = check_orders()
        for elem in ord:
            if not elem in pos:
                close_open_orders(elem)

        if len(pos) < qty:
            for elem in symbols:
                signal = rsi_signal(elem)
                if signal == 'up' and not elem in pos and not elem in ord and elem != symbol:
                    print('Found BUY signal for ', elem)
                    set_mode(elem, type)
                    set_leverage(elem, leverage)
                    print('Placing order for ', elem)
                    open_order(elem, 'buy')
                    symbol = elem
                    order = True
                    pos = get_pos()
                    ord = check_orders()
                    # break
                if signal == 'down' and not elem in pos and not elem in ord and elem != symbol:
                    print('Found SELL signal for ', elem)
                    set_mode(elem, type)
                    set_leverage(elem, leverage)
                    print('Placing order for ', elem)
                    open_order(elem, 'sell')
                    symbol = elem
                    order = True
                    pos = get_pos()
                    ord = check_orders()
                    # break
    print('Waiting 30 sec')
    sleep(30)