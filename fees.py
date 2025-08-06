# -*- coding: utf-8 -*-

import ccxt
import os
import datetime
import time
from dotenv import load_dotenv

def calculate_total_fees():
    """
    连接交易所，获取指定时间后的所有合约成交记录，并统计手续费。
    """
    # --- 1. 加载和设置 ---
    
    # 从 .env 文件加载环境变量 (API_KEY, API_SECRET)
    load_dotenv()
    api_key = os.getenv('apiKey')
    api_secret = os.getenv('secret')
    # Bitget 可能需要密码 (passphrase)，如果你的 API 密钥有这个设置，请在 .env 文件中添加
    passphrase = os.getenv('password') 

    if not api_key or not api_secret:
        print("错误：请确保 .env 文件中已设置 EXCHANGE_API_KEY 和 EXCHANGE_API_SECRET。")
        return

    # --- 2. 配置交易所 ---
    
    # 已为你修改为 Bitget
    exchange_id = 'bitget' 
    
    try:
        exchange_class = getattr(ccxt, exchange_id)
    except AttributeError:
        print(f"错误：找不到交易所 '{exchange_id}'。请检查 ccxt 是否支持该交易所，或 ID 是否拼写正确。")
        return
        
    config = {
        'apiKey': api_key,
        'secret': api_secret,
        'options': {
            'defaultType': 'swap',  # Bitget 使用 'swap' 来表示合约
        },
    }
    # 如果有密码，则添加到配置中
    if passphrase:
        config['password'] = passphrase
        
    exchange = exchange_class(config)

    # --- 3. 设置起始时间 ---
    
    # 将你提供的时间字符串转换为交易所需要的 UTC 毫秒时间戳
    start_time_str = '2025-08-02 15:10:00'
    # 假设输入的是本地时间（东八区），先转换为 UTC 时间
    local_tz = datetime.timezone(datetime.timedelta(hours=8))
    dt_local = datetime.datetime.strptime(start_time_str, '%Y-%m-%d %H:%M:%S').replace(tzinfo=local_tz)
    dt_utc = dt_local.astimezone(datetime.timezone.utc)
    since_timestamp = int(dt_utc.timestamp() * 1000)
    
    print(f"将从 UTC 时间 {dt_utc.strftime('%Y-%m-%d %H:%M:%S')} 开始统计手续费...")

    # --- 4. 获取并处理数据 ---
    
    try:
        # 检查交易所是否支持 fetchMyTrades 方法
        if not exchange.has['fetchMyTrades']:
            print(f"错误：交易所 '{exchange_id}' 不支持 fetchMyTrades 方法，无法获取个人成交记录。")
            return

        print("正在加载市场列表以获取所有合约交易对...")
        markets = exchange.load_markets()
        # 筛选出所有合约交易对 (swap)
        symbols = [
            market['symbol'] for market in markets.values() 
            if market.get('swap') and market.get('active')
        ]
        
        if not symbols:
            print("错误：未能从交易所获取到任何活跃的合约交易对。")
            return

        print(f"成功获取到 {len(symbols)} 个合约交易对。开始逐个查询成交记录...")
        
        total_fees = {}  # 使用字典来分别统计不同币种的手续费, e.g., {'USDT': 10.5}

        # 遍历所有交易对
        for i, symbol in enumerate(symbols):
            try:
                # 使用 fetch_my_trades 获取指定交易对和时间之后的所有成交记录
                trades = exchange.fetch_my_trades(symbol=symbol, since=since_timestamp, limit=500)
                
                if trades:
                    print(f"[{i+1}/{len(symbols)}] 在 {symbol} 发现 {len(trades)} 条成交记录...")
                    for trade in trades:
                        # 检查订单信息中是否包含手续费(fee)字段
                        if 'fee' in trade and trade['fee'] is not None:
                            fee_cost = trade['fee']['cost']
                            fee_currency = trade['fee']['currency']
                            
                            # 累加手续费
                            if fee_currency in total_fees:
                                total_fees[fee_currency] += fee_cost
                            else:
                                total_fees[fee_currency] = fee_cost
                
                # 为了防止API请求过于频繁而被限制，每次请求后暂停一小段时间
                time.sleep(exchange.rateLimit / 1000)

            except ccxt.NetworkError as e:
                print(f"查询 {symbol} 时发生网络错误: {e}，稍后重试...")
                time.sleep(5)
            except ccxt.ExchangeError as e:
                # 某些交易对可能没有交易历史，交易所会报错，这通常是正常的，可以忽略
                pass
            except Exception as e:
                print(f"查询 {symbol} 时发生未知错误: {e}")

        # --- 5. 显示结果 ---
        
        print("\n" + "="*40)
        print("✨ 手续费统计完成 ✨")
        print("="*40)
        
        if not total_fees:
            print("在指定时间段内没有找到任何已付手续费的成交记录。")
        else:
            print("总计手续费如下：")
            for currency, amount in total_fees.items():
                # 使用 :.8f 来格式化输出，保留8位小数，适合加密货币
                print(f"  - {amount:.8f} {currency}")
        print("="*40)

    except Exception as e:
        print(f"\n程序运行出错: {e}")
        print("请检查：")
        print("1. API 密钥是否有误或权限不足（需要有读取交易历史的权限）。")
        print("2. 网络连接是否正常。")
        print("3. 如果你的 Bitget API 密钥设置了密码，请确保在 .env 文件中添加了 EXCHANGE_API_PASSPHRASE。")

# 运行主函数
if __name__ == "__main__":
    calculate_total_fees()
