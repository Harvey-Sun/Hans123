# -*- coding:utf-8 -*-

from CloudQuant import MiniSimulator
import numpy as np
import pandas as pd

username = 'Harvey_Sun'
password = 'P948894dgmcsy'
Strategy_Name = 'Hans123'

INIT_CAP = 100000000
START_DATE = '20130101'
END_DATE = '20161231'
Fee_Rate = 0.001
k = 0.75
program_path = 'C:/cStrategy/'


def initial(sdk):
    sdk.prepareData(['LZ_GPA_INDEX_CSI500MEMBER', 'LZ_GPA_SLCIND_STOP_FLAG'])


def init_per_day(sdk):
    sdk.clearGlobal()
    today = sdk.getNowDate()
    sdk.sdklog(today, '========================================日期')
    # 获取当天中证500成分股
    in_zz500 = pd.Series(sdk.getFieldData('LZ_GPA_INDEX_CSI500MEMBER')[-1]) == 1
    stock_list = sdk.getStockList()
    zz500 = list(pd.Series(stock_list)[in_zz500])
    sdk.setGlobal('zz500', zz500)
    # 获取仓位信息
    positions = sdk.getPositions()
    stock_position = dict([[i.code, 1] for i in positions])
    sdk.setGlobal('stock_position', stock_position)
    # 找到中证500外的有仓位的股票
    out_zz500_stock = list(set(stock_position.keys()) - set(zz500))
    # 当日没有停牌的股票
    not_stop = pd.isnull(sdk.getFieldData('LZ_GPA_SLCIND_STOP_FLAG')[-1])
    zz500_available = list(pd.Series(stock_list)[np.logical_and(in_zz500, not_stop)])
    sdk.setGlobal('zz500_available', zz500_available)
    # 以下代码获取当天被移出中证500的有仓位的股票中可交易的股票
    out_zz500_available = list(set(pd.Series(stock_list)[not_stop]).intersection(set(out_zz500_stock)))
    sdk.setGlobal('out_zz500_available', out_zz500_available)
    # 订阅所有可交易的股票
    stock_available = list(set(zz500_available + out_zz500_available))
    sdk.sdklog(len(stock_available), '订阅股票数量')
    sdk.sdklog(len(stock_position), '底仓股票数量')
    sdk.subscribeQuote(stock_available)


def strategy(sdk):
    if sdk.getNowTime() == '093000':
        # 获取仓位信息及有仓位的股票
        positions = sdk.getPositions()
        position_dict = dict([[i.code, i.optPosition] for i in positions])
        # 获得中证500当日可交易的股票
        zz500_available = sdk.getGlobal('zz500_available')
        # 中证500外的股票
        out_zz500_available = sdk.getGlobal('out_zz500_available')
        # 所有考虑中的可交易的股票
        stock_available = list(set(zz500_available + out_zz500_available))
        # 获取盘口数据
        quotes = sdk.getQuotes(stock_available)
        # 有底仓的股票
        stock_position = sdk.getGlobal('stock_position')
        # 考虑被移出中证500的那些股票，卖出其底仓
        base_clear = []
        if out_zz500_available:
            for stock in out_zz500_available:
                position = position_dict[stock]
                price = quotes[stock].current
                order = [stock, price, position, -1]
                base_clear.append(order)
                del stock_position[stock]
            sdk.makeOrders(base_clear)
            sdk.sdklog(len(out_zz500_available), '清除底仓股票数量')
        # 计算仓位股票和可用资金
        number = sum(stock_position.values()) / 2  # 计算有多少个全仓股
        available_cash = sdk.getAccountInfo().availableCash / (500 - number) if number < 500 else 0
        sdk.setGlobal('available_cash', available_cash)
        # 建立底仓
        stock_to_build_base = list(set(zz500_available) - set(stock_position.keys()))
        base_hold = []
        stock_built_base = []
        for stock in stock_to_build_base:
            price = quotes[stock].current
            volume = 100 * np.floor(available_cash * 0.5 / (100 * price))
            if volume > 0:
                order = [stock, price, volume, 1]
                base_hold.append(order)
                stock_position[stock] = 1
                stock_built_base.append(stock)
        sdk.makeOrders(base_hold)
        sdk.setGlobal('stock_built_base', stock_built_base)
        sdk.sdklog(len(stock_built_base), '建立底仓股票数量')
        sdk.setGlobal('stock_position', stock_position)

        zz500_tradable = list(set(zz500_available) - set(stock_built_base))
        # 取得盘口数据
        quotes = sdk.getQuotes(zz500_tradable)
        # 获取最高价与最低价
        max_high = [quotes[stock].high for stock in zz500_tradable]
        sdk.setGlobal('max_high', max_high)
        min_low = [quotes[stock].low for stock in zz500_tradable]
        sdk.setGlobal('min_low', min_low)

    if (sdk.getNowTime() > '093000') & (sdk.getNowTime() < '100000'):
        max_high = sdk.getGlobal('max_high')
        min_low = sdk.getGlobal('min_low')
        zz500_available = sdk.getGlobal('zz500_available')
        stock_built_base = sdk.getGlobal('stock_built_base')
        zz500_tradable = list(set(zz500_available) - set(stock_built_base))
        # 取得盘口数据
        quotes = sdk.getQuotes(zz500_tradable)
        # 获取最高价与最低价
        high = [quotes[stock].high for stock in zz500_tradable]
        low = [quotes[stock].low for stock in zz500_tradable]
        max_high = np.where(high > max_high, high, max_high)
        min_low = np.where(low < min_low, low, min_low)
        sdk.setGlobal('max_high', max_high)
        sdk.setGlobal('min_low', min_low)

    if (sdk.getNowTime() >= '100000') & (sdk.getNowTime() < '145500'):
        # 获取仓位信息及有仓位的股票
        positions = sdk.getPositions()
        position_dict = dict([[i.code, i.optPosition] for i in positions])
        # 获得中证500当日可交易的股票
        zz500_available = sdk.getGlobal('zz500_available')
        stock_built_base = sdk.getGlobal('stock_built_base')
        zz500_tradable = list(set(zz500_available) - set(stock_built_base))
        # 有底仓的股票
        stock_position = sdk.getGlobal('stock_position')
        # 上下轨
        up_line = pd.Series(sdk.getGlobal('max_high'), index=zz500_tradable)
        down_line = pd.Series(sdk.getGlobal('min_low'), index=zz500_tradable)
        # 取得盘口数据
        quotes = sdk.getQuotes(zz500_tradable)
        # 可用资金
        available_cash = sdk.getGlobal('available_cash')
            
        buy_orders = []
        sell_orders = []
        for stock in zz500_tradable:
            # 如果当时买入股票超过了500-number?
            current_price = quotes[stock].current
            up = up_line[stock]
            down = down_line[stock]
            if (current_price > up) & (stock_position[stock] == 1):
                volume = 100 * np.floor(available_cash * 0.5 / (100 * current_price))
                if volume > 0:
                    order = [stock, current_price, volume, 1]
                    buy_orders.append(order)
                    stock_position[stock] = 2
            elif (current_price < down) & (stock_position[stock] == 1):
                volume = position_dict[stock]
                order = [stock, current_price, volume, -1]
                sell_orders.append(order)
                stock_position[stock] = 0
            else:
                pass
        sdk.makeOrders(sell_orders)
        sdk.makeOrders(buy_orders)
        sdk.setGlobal('stock_position', stock_position)
        # 记录下单数据
        if buy_orders or sell_orders:
            sdk.sdklog(sdk.getNowTime(), '=================时间')
            if buy_orders:
                sdk.sdklog('Buy orders')
                sdk.sdklog(np.array(buy_orders))
            if sell_orders:
                sdk.sdklog('Short orders')
                sdk.sdklog(np.array(sell_orders))

    if sdk.getNowTime() == '145500':
        # 获取仓位信息及有仓位的股票
        positions = sdk.getPositions()
        position_dict = dict([[i.code, i.optPosition] for i in positions])
        available_cash = sdk.getGlobal('available_cash')
        stock_position = sdk.getGlobal('stock_position')
        stock_to_clear = list(stock_position.keys())
        quotes = sdk.getQuotes(stock_to_clear)
        clear_orders = []
        for stock in stock_to_clear:
            if stock_position[stock] == 2:
                price = quotes[stock].current
                volume = position_dict[stock]
                order = [stock, price, volume, -1]
                clear_orders.append(order)
            elif stock_position[stock] == 0:
                price = quotes[stock].current
                volume = 100 * np.floor(available_cash * 0.5 / (price * 100))
                order = [stock, price, volume, 1]
                clear_orders.append(order)
            else:
                pass
        sdk.makeOrders(clear_orders)
        sdk.setGlobal('stock_position', stock_position)

config = {
    'username': username,
    'password': password,
    'initCapital': INIT_CAP,
    'startDate': START_DATE,
    'endDate': END_DATE,
    'strategy': strategy,
    'initial': initial,
    'preparePerDay': init_per_day,
    'feeRate': Fee_Rate,
    'strategyName': Strategy_Name,
    'logfile': '%s.log' % Strategy_Name,
    'rootpath': program_path,
    'executeMode': 'M',
    'feeLimit': 5,
    'cycle': 1,
    'dealByVolume': True,
    'allowfortodayfactor': ['LZ_GPA_INDEX_CSI500MEMBER', 'LZ_GPA_SLCIND_STOP_FLAG']
}

if __name__ == "__main__":
    # 在线运行所需代码
    import os
    config['strategyID'] = os.path.splitext(os.path.split(__file__)[1])[0]
    MiniSimulator(**config).run()
