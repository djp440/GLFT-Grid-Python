# CCXT Pro 详尽使用文档

## 目录
1. [简介](#简介)
2. [架构概述](#架构概述)
3. [安装配置](#安装配置)
4. [支持的交易所](#支持的交易所)
5. [核心功能](#核心功能)
6. [API 参考](#api-参考)
7. [代码示例](#代码示例)
8. [错误处理](#错误处理)
9. [最佳实践](#最佳实践)
10. [常见问题](#常见问题)

## 简介

CCXT Pro 是 CCXT 库的专业版扩展，专门为算法交易者和开发者设计，提供 WebSocket 实时数据流支持。自 CCXT 1.95+ 版本起，CCXT Pro 已免费合并到主 CCXT 包中，无需单独购买许可证。

### 主要特性
- **实时数据流**：通过 WebSocket 连接获取实时市场数据
- **统一 API**：与 CCXT REST API 保持一致的接口设计
- **多语言支持**：JavaScript、Python、PHP 等
- **增量状态管理**：高效的数据缓存和更新机制
- **自动重连**：内置连接管理和错误恢复
- **65+ 交易所支持**：覆盖主流加密货币交易所

## 架构概述

CCXT Pro 基于 CCXT 核心库构建，通过以下技术扩展功能：
- **JavaScript**：原型级混入 (Prototype-level mixins)
- **Python**：多重继承 (Multiple inheritance)
- **PHP**：特性 (Traits)

```
                                 User
    +-------------------------------------------------------------+
    |                          CCXT Pro                           |
    +------------------------------+------------------------------+
    |            Public            .           Private            |
    +=============================================================+
    │                              .                              |
    │                  The Unified CCXT Pro API                   |
    |                              .                              |
    |     loadMarkets              .         watchBalance         |
    |     watchTicker              .         watchOrders          |
    |     watchTickers             .         watchMyTrades        |
    |     watchOrderBook           .         watchPositions       |
    |     watchOHLCV               .         createOrderWs        |
    |     watchStatus              .         editOrderWs          |
    |     watchTrades              .         cancelOrderWs        |
    │     watchOHLCVForSymbols     .         cancelOrdersWs       |
    │     watchTradesForSymbols    .         cancelAllOrdersWs    |
    │     watchOrderBookForSymbols .                              |
    │                              .                              |
    +=============================================================+
    │                          unWatch                            |
    │                   (to stop **watch** method)                |
    +=============================================================+
    │                              .                              |
    |            The Underlying Exchange-Specific APIs            |
    |         (Derived Classes And Their Implementations)         |
    │                              .                              |
    +=============================================================+
    │                              .                              |
    |                 CCXT Pro Base Exchange Class                |
    │                              .                              |
    +=============================================================+

    +-------------------------------------------------------------+
    |                                                             |
    |                            CCXT                             |
    |                                                             |
    +=============================================================+
```

## 安装配置

### JavaScript/Node.js

#### 通过 NPM 安装
```bash
npm install ccxt
```

#### 使用方式
```javascript
// ESM 导入
import { pro as ccxt } from 'ccxt';

// CommonJS 导入
const ccxt = require('ccxt').pro;

// 创建交易所实例
const exchange = new ccxt.binance({
    apiKey: 'YOUR_API_KEY',
    secret: 'YOUR_SECRET_KEY',
    // verbose: true, // 调试模式
});
```

#### 浏览器使用
```html
<script src="https://cdn.jsdelivr.net/npm/ccxt@latest/dist/ccxt.browser.min.js"></script>
<script>
    const exchange = new ccxt.pro.binance();
</script>
```

### Python

#### 通过 pip 安装
```bash
pip install ccxt
```

#### 使用方式
```python
import ccxt.pro as ccxtpro

# 创建交易所实例
exchange = ccxtpro.binance({
    'apiKey': 'YOUR_API_KEY',
    'secret': 'YOUR_SECRET_KEY',
    # 'verbose': True,  # 调试模式
})
```

### PHP

#### 通过 Composer 安装
```bash
composer require ccxt/ccxt
```

#### 使用方式
```php
<?php
require_once 'vendor/autoload.php';

$exchange = new \ccxtpro\binance([
    'apiKey' => 'YOUR_API_KEY',
    'secret' => 'YOUR_SECRET_KEY',
]);
?>
```

## 支持的交易所

CCXT Pro 目前支持 65+ 个加密货币交易所的 WebSocket API：

### 主要交易所
- **Binance** (binance)
- **Binance COIN-M** (binancecoinm)
- **Binance USDⓈ-M** (binanceusdm)
- **Bybit** (bybit)
- **OKX** (okx)
- **KuCoin** (kucoin)
- **Gate.io** (gate)
- **HTX** (htx)
- **Bitget** (bitget)
- **MEXC** (mexc)
- **Kraken** (kraken)
- **Coinbase** (coinbase)
- **Deribit** (deribit)
- **BitMEX** (bitmex)

### 检查交易所支持的功能
```javascript
console.log(exchange.has); // 查看支持的功能
console.log(exchange.has['watchOrderBook']); // 检查是否支持订单簿流
```

## 核心功能

### 公共数据流 (Public Streams)

#### 1. 订单簿 (Order Book)
- `watchOrderBook(symbol, limit, params)`
- `watchOrderBookForSymbols(symbols, limit, params)`

#### 2. 行情数据 (Ticker)
- `watchTicker(symbol, params)`
- `watchTickers(symbols, params)`

#### 3. 交易记录 (Trades)
- `watchTrades(symbol, since, limit, params)`
- `watchTradesForSymbols(symbols, since, limit, params)`

#### 4. K线数据 (OHLCV)
- `watchOHLCV(symbol, timeframe, since, limit, params)`
- `watchOHLCVForSymbols(symbolsAndTimeframes, since, limit, params)`

#### 5. 交易所状态
- `watchStatus(params)`

### 私有数据流 (Private Streams)

#### 1. 账户余额
- `watchBalance(params)`

#### 2. 订单管理
- `watchOrders(symbol, since, limit, params)`
- `watchMyTrades(symbol, since, limit, params)`

#### 3. 持仓信息 (期货)
- `watchPositions(symbols, since, limit, params)`

#### 4. WebSocket 订单操作
- `createOrderWs(symbol, type, side, amount, price, params)`
- `editOrderWs(id, symbol, type, side, amount, price, params)`
- `cancelOrderWs(id, symbol, params)`
- `cancelOrdersWs(ids, symbol, params)`
- `cancelAllOrdersWs(symbol, params)`

### 连接管理
- `unWatch(symbol, type)` - 停止特定数据流
- `close()` - 关闭所有连接

## API 参考

### 基本使用模式

所有 `watch*` 方法都返回 Promise，解析为初始数据快照，然后持续推送更新到缓存中。

```javascript
// 基本模式
while (true) {
    try {
        const data = await exchange.watchOrderBook('BTC/USDT');
        // 处理数据
        console.log(data);
    } catch (error) {
        console.error(error);
        break;
    }
}
```

### 参数说明

#### symbol
- 格式：`'BASE/QUOTE'` (现货) 或 `'BASE/QUOTE:SETTLE'` (期货)
- 示例：`'BTC/USDT'`, `'ETH/USDT:USDT'`

#### timeframe (K线周期)
- 支持：`'1m'`, `'5m'`, `'15m'`, `'1h'`, `'4h'`, `'1d'` 等
- 具体支持的周期因交易所而异

#### limit
- 限制返回数据的数量
- 订单簿：通常 5-1000
- 交易记录：通常 1-1000

#### since
- Unix 时间戳（毫秒）
- 用于获取指定时间之后的数据

## 代码示例

### 1. 监听订单簿

#### JavaScript
```javascript
const ccxt = require('ccxt').pro;

async function watchOrderBook() {
    const exchange = new ccxt.binance();
    const symbol = 'BTC/USDT';
    
    while (true) {
        try {
            const orderbook = await exchange.watchOrderBook(symbol);
            const bestBid = orderbook.bids[0];
            const bestAsk = orderbook.asks[0];
            
            console.log(`${symbol} - Bid: ${bestBid[0]} Ask: ${bestAsk[0]} Spread: ${(bestAsk[0] - bestBid[0]).toFixed(2)}`);
        } catch (error) {
            console.error('Error:', error.message);
            break;
        }
    }
    
    await exchange.close();
}

watchOrderBook();
```

#### Python
```python
import asyncio
import ccxt.pro as ccxtpro

async def watch_orderbook():
    exchange = ccxtpro.binance()
    symbol = 'BTC/USDT'
    
    while True:
        try:
            orderbook = await exchange.watch_order_book(symbol)
            best_bid = orderbook['bids'][0]
            best_ask = orderbook['asks'][0]
            
            print(f"{symbol} - Bid: {best_bid[0]} Ask: {best_ask[0]} Spread: {best_ask[0] - best_bid[0]:.2f}")
        except Exception as e:
            print(f"Error: {e}")
            break
    
    await exchange.close()

asyncio.run(watch_orderbook())
```

### 2. 监听多个交易对的行情

```javascript
const ccxt = require('ccxt').pro;

async function watchMultipleTickers() {
    const exchange = new ccxt.binance();
    const symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT'];
    
    while (true) {
        try {
            const tickers = await exchange.watchTickers(symbols);
            
            for (const symbol in tickers) {
                const ticker = tickers[symbol];
                console.log(`${symbol}: ${ticker.last} (${ticker.percentage}%)`);
            }
            console.log('---');
        } catch (error) {
            console.error('Error:', error.message);
            break;
        }
    }
    
    await exchange.close();
}

watchMultipleTickers();
```

### 3. 监听K线数据

```javascript
const ccxt = require('ccxt').pro;

async function watchOHLCV() {
    const exchange = new ccxt.binance();
    const symbol = 'BTC/USDT';
    const timeframe = '1m';
    
    while (true) {
        try {
            const ohlcv = await exchange.watchOHLCV(symbol, timeframe);
            const latest = ohlcv[ohlcv.length - 1];
            
            console.log(`${symbol} ${timeframe}: O:${latest[1]} H:${latest[2]} L:${latest[3]} C:${latest[4]} V:${latest[5]}`);
        } catch (error) {
            console.error('Error:', error.message);
            break;
        }
    }
    
    await exchange.close();
}

watchOHLCV();
```

### 4. 监听账户余额 (需要 API 密钥)

```javascript
const ccxt = require('ccxt').pro;

async function watchBalance() {
    const exchange = new ccxt.binance({
        apiKey: 'YOUR_API_KEY',
        secret: 'YOUR_SECRET_KEY',
        sandbox: true, // 使用测试环境
    });
    
    while (true) {
        try {
            const balance = await exchange.watchBalance();
            
            console.log('Free balances:');
            for (const currency in balance.free) {
                if (balance.free[currency] > 0) {
                    console.log(`${currency}: ${balance.free[currency]}`);
                }
            }
        } catch (error) {
            console.error('Error:', error.message);
            break;
        }
    }
    
    await exchange.close();
}

watchBalance();
```

### 5. 监听订单状态

```javascript
const ccxt = require('ccxt').pro;

async function watchOrders() {
    const exchange = new ccxt.binance({
        apiKey: 'YOUR_API_KEY',
        secret: 'YOUR_SECRET_KEY',
        sandbox: true,
    });
    
    const symbol = 'BTC/USDT';
    
    while (true) {
        try {
            const orders = await exchange.watchOrders(symbol);
            
            console.log(`Active orders for ${symbol}:`);
            orders.forEach(order => {
                console.log(`${order.id}: ${order.side} ${order.amount} ${order.symbol} @ ${order.price} (${order.status})`);
            });
        } catch (error) {
            console.error('Error:', error.message);
            break;
        }
    }
    
    await exchange.close();
}

watchOrders();
```

### 6. 多交易所同时监听

```javascript
const ccxt = require('ccxt').pro;

async function watchMultipleExchanges() {
    const exchanges = {
        binance: new ccxt.binance(),
        okx: new ccxt.okx(),
        bybit: new ccxt.bybit(),
    };
    
    const symbol = 'BTC/USDT';
    
    const promises = Object.entries(exchanges).map(async ([name, exchange]) => {
        while (true) {
            try {
                const ticker = await exchange.watchTicker(symbol);
                console.log(`${name}: ${ticker.last}`);
            } catch (error) {
                console.error(`${name} error:`, error.message);
                break;
            }
        }
    });
    
    await Promise.all(promises);
    
    // 关闭所有连接
    for (const exchange of Object.values(exchanges)) {
        await exchange.close();
    }
}

watchMultipleExchanges();
```

## 错误处理

### 常见错误类型

1. **网络连接错误**
   - `NetworkError`: 网络连接问题
   - `RequestTimeout`: 请求超时

2. **认证错误**
   - `AuthenticationError`: API 密钥无效
   - `PermissionDenied`: 权限不足

3. **交易所错误**
   - `ExchangeError`: 交易所返回的错误
   - `ExchangeNotAvailable`: 交易所不可用

4. **参数错误**
   - `BadSymbol`: 无效的交易对
   - `BadRequest`: 请求参数错误

### 错误处理最佳实践

```javascript
const ccxt = require('ccxt').pro;

async function robustWatchOrderBook() {
    const exchange = new ccxt.binance();
    const symbol = 'BTC/USDT';
    let retryCount = 0;
    const maxRetries = 5;
    
    while (retryCount < maxRetries) {
        try {
            const orderbook = await exchange.watchOrderBook(symbol);
            console.log(`${symbol} orderbook updated`);
            retryCount = 0; // 重置重试计数
        } catch (error) {
            console.error(`Error (attempt ${retryCount + 1}):`, error.message);
            
            if (error instanceof ccxt.NetworkError) {
                // 网络错误，等待后重试
                retryCount++;
                await new Promise(resolve => setTimeout(resolve, 1000 * retryCount));
            } else if (error instanceof ccxt.AuthenticationError) {
                // 认证错误，停止重试
                console.error('Authentication failed, stopping...');
                break;
            } else {
                // 其他错误，重试
                retryCount++;
                await new Promise(resolve => setTimeout(resolve, 1000));
            }
        }
    }
    
    await exchange.close();
}

robustWatchOrderBook();
```

## 最佳实践

### 1. 连接管理

```javascript
// 正确的连接管理
class ExchangeManager {
    constructor() {
        this.exchange = null;
        this.isRunning = false;
    }
    
    async start() {
        this.exchange = new ccxt.pro.binance();
        this.isRunning = true;
        
        // 监听多个数据流
        await Promise.all([
            this.watchOrderBook(),
            this.watchTicker(),
            this.watchTrades()
        ]);
    }
    
    async stop() {
        this.isRunning = false;
        if (this.exchange) {
            await this.exchange.close();
        }
    }
    
    async watchOrderBook() {
        while (this.isRunning) {
            try {
                const orderbook = await this.exchange.watchOrderBook('BTC/USDT');
                // 处理订单簿数据
            } catch (error) {
                if (this.isRunning) {
                    console.error('OrderBook error:', error.message);
                    await new Promise(resolve => setTimeout(resolve, 1000));
                }
            }
        }
    }
    
    // ... 其他方法
}

// 使用
const manager = new ExchangeManager();
manager.start();

// 优雅关闭
process.on('SIGINT', async () => {
    console.log('Shutting down...');
    await manager.stop();
    process.exit(0);
});
```

### 2. 数据缓存和处理

```javascript
class DataProcessor {
    constructor() {
        this.orderBookCache = new Map();
        this.tickerCache = new Map();
    }
    
    async processOrderBook(symbol, orderbook) {
        const previous = this.orderBookCache.get(symbol);
        this.orderBookCache.set(symbol, orderbook);
        
        if (previous) {
            const spreadChange = this.calculateSpreadChange(previous, orderbook);
            if (Math.abs(spreadChange) > 0.01) {
                console.log(`${symbol} spread changed by ${spreadChange.toFixed(4)}`);
            }
        }
    }
    
    calculateSpreadChange(prev, curr) {
        const prevSpread = prev.asks[0][0] - prev.bids[0][0];
        const currSpread = curr.asks[0][0] - curr.bids[0][0];
        return currSpread - prevSpread;
    }
}
```

### 3. 性能优化

```javascript
// 使用节流避免过度处理
function throttle(func, delay) {
    let timeoutId;
    let lastExecTime = 0;
    
    return function (...args) {
        const currentTime = Date.now();
        
        if (currentTime - lastExecTime > delay) {
            func.apply(this, args);
            lastExecTime = currentTime;
        } else {
            clearTimeout(timeoutId);
            timeoutId = setTimeout(() => {
                func.apply(this, args);
                lastExecTime = Date.now();
            }, delay - (currentTime - lastExecTime));
        }
    };
}

// 使用示例
const processOrderBook = throttle((orderbook) => {
    // 处理订单簿数据
    console.log('Processing orderbook:', orderbook.symbol);
}, 100); // 最多每100ms处理一次

while (true) {
    const orderbook = await exchange.watchOrderBook('BTC/USDT');
    processOrderBook(orderbook);
}
```

### 4. 多交易对管理

```javascript
class MultiSymbolWatcher {
    constructor(exchange, symbols) {
        this.exchange = exchange;
        this.symbols = symbols;
        this.watchers = new Map();
    }
    
    async startWatching() {
        for (const symbol of this.symbols) {
            this.watchers.set(symbol, this.watchSymbol(symbol));
        }
        
        await Promise.all(this.watchers.values());
    }
    
    async watchSymbol(symbol) {
        while (true) {
            try {
                const ticker = await this.exchange.watchTicker(symbol);
                this.onTickerUpdate(symbol, ticker);
            } catch (error) {
                console.error(`Error watching ${symbol}:`, error.message);
                await new Promise(resolve => setTimeout(resolve, 1000));
            }
        }
    }
    
    onTickerUpdate(symbol, ticker) {
        console.log(`${symbol}: ${ticker.last} (${ticker.percentage}%)`);
    }
    
    async stop() {
        await this.exchange.close();
    }
}

// 使用
const watcher = new MultiSymbolWatcher(
    new ccxt.pro.binance(),
    ['BTC/USDT', 'ETH/USDT', 'BNB/USDT']
);

watcher.startWatching();
```

## 常见问题

### Q1: 如何检查交易所是否支持特定功能？

```javascript
const exchange = new ccxt.pro.binance();

console.log('Supported features:');
console.log('watchOrderBook:', exchange.has['watchOrderBook']);
console.log('watchTicker:', exchange.has['watchTicker']);
console.log('watchTrades:', exchange.has['watchTrades']);
console.log('watchOHLCV:', exchange.has['watchOHLCV']);
console.log('watchBalance:', exchange.has['watchBalance']);
```

### Q2: 如何处理连接断开？

CCXT Pro 内置自动重连机制，但你也可以手动处理：

```javascript
async function watchWithReconnect() {
    const exchange = new ccxt.pro.binance();
    
    while (true) {
        try {
            const orderbook = await exchange.watchOrderBook('BTC/USDT');
            // 处理数据
        } catch (error) {
            if (error.message.includes('connection')) {
                console.log('Connection lost, reconnecting...');
                await new Promise(resolve => setTimeout(resolve, 5000));
                continue;
            }
            throw error;
        }
    }
}
```

### Q3: 如何限制数据更新频率？

```javascript
let lastUpdate = 0;
const updateInterval = 1000; // 1秒

while (true) {
    const orderbook = await exchange.watchOrderBook('BTC/USDT');
    const now = Date.now();
    
    if (now - lastUpdate >= updateInterval) {
        // 处理数据
        console.log('Orderbook updated');
        lastUpdate = now;
    }
}
```

### Q4: 如何同时监听现货和期货？

```javascript
const spotExchange = new ccxt.pro.binance();
const futuresExchange = new ccxt.pro.binanceusdm();

Promise.all([
    // 现货
    (async () => {
        while (true) {
            const ticker = await spotExchange.watchTicker('BTC/USDT');
            console.log('Spot BTC/USDT:', ticker.last);
        }
    })(),
    
    // 期货
    (async () => {
        while (true) {
            const ticker = await futuresExchange.watchTicker('BTC/USDT:USDT');
            console.log('Futures BTC/USDT:', ticker.last);
        }
    })()
]);
```

### Q5: 如何处理 API 限制？

CCXT Pro 内置速率限制处理，但你可以额外配置：

```javascript
const exchange = new ccxt.pro.binance({
    rateLimit: 1200, // 毫秒
    enableRateLimit: true,
});
```

### Q6: 如何在生产环境中使用？

```javascript
// 生产环境配置
const exchange = new ccxt.pro.binance({
    apiKey: process.env.BINANCE_API_KEY,
    secret: process.env.BINANCE_SECRET,
    sandbox: false, // 生产环境
    enableRateLimit: true,
    timeout: 30000,
    // 可选：代理配置
    // proxy: 'http://proxy.example.com:8080',
});

// 错误监控
exchange.on('error', (error) => {
    console.error('Exchange error:', error);
    // 发送到监控系统
});
```

## 总结

CCXT Pro 为加密货币交易提供了强大的实时数据流功能，通过统一的 API 接口支持多个主流交易所。正确使用 CCXT Pro 可以帮助开发者构建高效的交易机器人、市场监控工具和数据分析系统。

关键要点：
1. **理解异步编程**：所有 watch 方法都是异步的
2. **正确处理错误**：实现重连和错误恢复机制
3. **管理连接**：及时关闭不需要的连接
4. **优化性能**：使用节流和缓存机制
5. **安全考虑**：保护 API 密钥，使用环境变量

通过遵循本文档的指导和最佳实践，你可以充分利用 CCXT Pro 的强大功能来构建专业级的加密货币交易应用。