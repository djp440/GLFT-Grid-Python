# 查询全部仓位

```
positions = await exchange.fetch_positions([symbolName], params={'productType': 'USDT-FUTURES'})
```

如果要使用 websocket 监听方法则将函数名替换为`watch_positions`即可，参数和返回值不变

## 注意事项

1. 就算只查询一个交易对，也必须将交易对的名称用[]括起来
2. productType 必须正确填写，有以下几种类型

- USDT-FUTURES：U 本位合约
- COIN-FUTURES：币本位合约
- USDC-FUTURES：USDC 合约
- SUSDT-FUTURES：U 本位合约模拟盘
- SCOIN-FUTURES：币本位合约模拟盘
- SUSDC-FUTURES：USDC 合约模拟盘

## 返回结构体

```
[{'info': {'marginCoin': 'SUSDT', 'symbol': 'SBTCSUSDT', 'holdSide': 'long', 'openDelegateSize': '0', 'marginSize': '227.2346', 'available': '0.01', 'locked': '0', 'total': '0.01', 'leverage': '5', 'achievedProfits': '0', 'openPriceAvg': '113617.3', 'marginMode': 'crossed', 'posMode': 'hedge_mode', 'unrealizedPL': '0.225', 'liquidationPrice': '65031742.063478260869', 'keepMarginRate': '0.004', 'markPrice': '113639.8', 'marginRatio': '0.001747451267', 'breakEvenPrice': '113753.722613568141', 'totalFee': '', 'deductedFee': '0.6817038', 'grant': '', 'assetMode': 'single', 'autoMargin': 'off', 'takeProfit': '', 'stopLoss': '', 'takeProfitId': '', 'stopLossId': '', 'cTime': '1754214011739', 'uTime': '1754214011739'}, 'id': None, 'symbol': 'SBTC/SUSDT:SUSDT', 'notional': 1136.398, 'marginMode': 'cross', 'liquidationPrice': 65031742.06347826, 'entryPrice': 113617.3, 'unrealizedPnl': 0.225, 'realizedPnl': None, 'percentage': 0.09, 'contracts': 0.01, 'contractSize': 1, 'markPrice': 113639.8, 'lastPrice': None, 'side': 'long', 'hedged': True, 'timestamp': 1754214011739, 'datetime': '2025-08-03T09:40:11.739Z', 'lastUpdateTimestamp': None, 'maintenanceMargin': 5.2274308, 'maintenanceMarginPercentage': 0.004, 'collateral': None, 'initialMargin': 227.2346, 'initialMarginPercentage': 0.19996040119746777, 'leverage': 5.0, 'marginRatio': 0.001747451267, 'stopLossPrice': None, 'takeProfitPrice': None}, {'info': {'marginCoin': 'SUSDT', 'symbol': 'SBTCSUSDT', 'holdSide': 'short', 'openDelegateSize': '0', 'marginSize': '227.2416', 'available': '0.01', 'locked': '0', 'total': '0.01', 'leverage': '5', 'achievedProfits': '0', 'openPriceAvg': '113620.8', 'marginMode': 'crossed', 'posMode': 'hedge_mode', 'unrealizedPL': '-0.19', 'liquidationPrice': '65031742.063478260869', 'keepMarginRate': '0.004', 'markPrice': '113639.8', 'marginRatio': '0.001747451267', 'breakEvenPrice': '113484.536797921247', 'totalFee': '', 'deductedFee': '0.6817248', 'grant': '', 'assetMode': 'single', 'autoMargin': 'off', 'takeProfit': '', 'stopLoss': '', 'takeProfitId': '', 'stopLossId': '', 'cTime': '1754213528153', 'uTime': '1754213528153'}, 'id': None, 'symbol': 'SBTC/SUSDT:SUSDT', 'notional': 1136.398, 'marginMode': 'cross', 'liquidationPrice': 65031742.06347826, 'entryPrice': 113620.8, 'unrealizedPnl': -0.19, 'realizedPnl': None, 'percentage': -0.08, 'contracts': 0.01, 'contractSize': 1, 'markPrice': 113639.8, 'lastPrice': None, 'side': 'short', 'hedged': True, 'timestamp': 1754213528153, 'datetime': '2025-08-03T09:32:08.153Z', 'lastUpdateTimestamp': None, 'maintenanceMargin': 5.2274308, 'maintenanceMarginPercentage': 0.004, 'collateral': None, 'initialMargin': 227.2416, 'initialMarginPercentage': 0.19996656101119503, 'leverage': 5.0, 'marginRatio': 0.001747451267, 'stopLossPrice': None, 'takeProfitPrice': None}]
```

# 下单

```
order = await exchange.createOrder(
    symbol=str,
    type=OrderType,
    side=OrderSide,
    amount=amount,
    price=price,
    params={
    "reduceOnly": reduceOnly,
    "hedged": True
    }
  )
```

## 注意事项

1. reduceOnly 代表是否只减仓，由于程序必须在双向持仓模式下运行，执行“平空”“平多”操作时，必须将 reduceOnly 设置为 True，而执行“开多”“开空”操作时，必须将 reduceOnly 设置为 False。
2. hedged 代表是否使用双向持仓模式，由于程序必须在双向持仓模式下运行，必须将 hedged 设置为 True。
3. type 可以设置为以下几种类型

- limit：限价单
- market：市价单
- stop：止损单
- stopLimit：止损限价单
- takeProfit：止盈单
- takeProfitLimit：止盈限价单
- trailingStop：跟踪止损单
- trailingStopLimit：跟踪止损限价单
  使用市价单时，price 参数可以设置为 None，程序会自动使用当前市场价格。

## 返回结构体

```
{'info': {'clientOid': '1335844108068626432', 'orderId': '1335844108056043522'}, 'id': '1335844108056043522', 'clientOrderId': '1335844108068626432', 'timestamp': None, 'datetime': None, 'lastTradeTimestamp': None, 'lastUpdateTimestamp': None, 'symbol': 'SBTC/SUSDT:SUSDT', 'type': None, 'side': None, 'price': None, 'amount': None, 'cost': None, 'average': None, 'filled': None, 'remaining': None, 'timeInForce': None, 'postOnly': None, 'reduceOnly': None, 'triggerPrice': None, 'takeProfitPrice': None, 'stopLossPrice': None, 'status': None, 'fee': None, 'trades': [], 'fees': [], 'stopPrice': None}
```

# 获取 K 线数据

```
ohlcv_data = await exchange.fetch_ohlcv(
            symbol=symbol,
            timeframe='1m',
            limit=20
        )
```

若要使用 websocket 监听方法则将函数名替换为`watch_ohlcv`即可，参数和返回值不变

## 注意事项

1. 时间框架可以设置为以下几种类型

- 1m：1 分钟
- 3m：3 分钟
- 5m：5 分钟
- 15m：15 分钟
- 30m：30 分钟
- 1h：1 小时
- 2h：2 小时
- 4h：4 小时
- 6h：6 小时
- 8h：8 小时
- 12h：12 小时
- 1d：1 天
- 3d：3 天
- 1w：1 周
- 1M：1 月

2. limit 代表获取的 K 线数据条数，最大为 100 条。

## 返回结构体

```
[[1754215200000, 113612.4, 113612.4, 113612.3, 113612.4, 2.132], [1754215260000, 113612.4, 113634.2, 113612.4, 113634.1, 5.24], [1754215320000, 113634.1, 113640.5, 113634.1, 113640.3, 0.89], [1754215380000, 113640.3, 113660.5, 113640.3, 113660.4, 1.692], [1754215440000, 113660.4, 113660.7, 113653.6, 113653.6, 3.588], [1754215500000, 113653.6, 113658.3, 113653.6, 113658.3, 5.336], [1754215560000, 113658.3, 113658.3, 113652.2, 113652.2, 3.07], [1754215620000, 113652.2, 113652.5, 113649.9, 113649.9, 3.344], [1754215680000, 113649.9, 113658.9, 113649.9, 113652.7, 6.268], [1754215740000, 113652.7, 113660.0, 113652.7, 113660.0, 2.594], [1754215800000, 113660.0, 113700.0, 113659.9, 113699.1, 3.158], [1754215860000, 113699.1, 113709.0, 113699.1, 113709.0, 1.764], [1754215920000, 113709.0, 113709.0, 113692.8, 113697.2, 1.902], [1754215980000, 113697.2, 113706.0, 113697.1, 113705.8, 1.054], [1754216040000, 113705.8, 113726.0, 113705.8, 113726.0, 0.702], [1754216100000, 113726.0, 113735.8, 113701.5, 113701.5, 22.752], [1754216160000, 113701.5, 113701.8, 113701.5, 113701.5, 0.798], [1754216220000, 113701.5, 113719.2, 113700.7, 113719.2, 4.108], [1754216280000, 113719.2, 113720.0, 113710.1, 113710.1, 2.002], [1754216340000, 113710.1, 113710.5, 113710.1, 113710.2, 3.702]]
```

- 函数会返回一个列表，这个列表里的每一个元素又是另一个列表，代表一根 K 线。

```
[timestamp, open, high, low, close, volume]
```

- timestamp: 这根 K 线开始的时间戳 (毫秒)
- open: 开盘价
- high: 最高价
- low: 最低价
- close: 收盘价
- volume: 成交量
