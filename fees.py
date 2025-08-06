# -*- coding: utf-8 -*-

import ccxt
import os
import datetime
import time
import sys
import json
from dotenv import load_dotenv

def fetch_all_trades(exchange, symbol, since_timestamp):
    """
    分页获取指定交易对的所有交易记录
    """
    all_trades = []
    limit = 100  # 每页获取的记录数
    now = exchange.milliseconds()
    empty_count = 0  # 连续空结果的计数器
    max_empty_attempts = 3  # 最大连续空结果尝试次数
    
    while since_timestamp < now and empty_count < max_empty_attempts:
        try:
            # 获取一页交易记录
            trades = exchange.fetch_my_trades(symbol=symbol, since=since_timestamp, limit=limit)
            
            if not trades:  # 如果没有更多交易记录
                empty_count += 1
                print(f"  -> 获取到空结果，尝试次数: {empty_count}/{max_empty_attempts}")
                
                # 如果已经达到最大尝试次数，并且时间戳很近当前时间，说明真的没有更多数据了
                if empty_count >= max_empty_attempts:
                    print(f"  -> 达到最大空结果尝试次数，停止查询")
                    break
                
                # 稍微增加时间戳，继续请求下一页
                since_timestamp += 60000 * limit  # 向前推limit分钟
                time.sleep(exchange.rateLimit / 1000)
                continue
            else:
                empty_count = 0  # 重置空结果计数器
                
            # 添加到总记录中
            all_trades.extend(trades)
            
            # 更新since_timestamp为最后一条记录的时间，避免重复
            since_timestamp = trades[-1]['timestamp'] + 1
            
            print(f"  -> 已获取 {len(trades)} 条记录，总计 {len(all_trades)} 条记录")
            
            # 防止API请求过于频繁
            time.sleep(exchange.rateLimit / 1000)
            
        except ccxt.NetworkError as e:
            print(f"获取 {symbol} 交易记录时发生网络错误: {e}")
            time.sleep(exchange.rateLimit / 1000)
            continue
        except ccxt.ExchangeError as e:
            print(f"获取 {symbol} 交易记录时交易所返回错误: {e}")
            break
        except Exception as e:
            print(f"获取 {symbol} 交易记录时发生未知错误: {e}")
            break
    
    return all_trades

def calculate_total_fees(symbols: list):
    """
    连接交易所，获取指定交易对在指定时间后的所有成交记录，并统计手续费。
    """
    # --- 1. 加载和设置 ---
    
    # --- 1. 加载和设置 ---
    load_dotenv()

    # 根据 .env 中的 sandbox 设置决定使用实盘还是模拟盘
    is_sandbox = os.getenv('sandbox', 'false').lower() == 'true'

    if is_sandbox:
        print("*** 正在使用模拟盘环境 ***")
        api_key = os.getenv('apiKey')
        api_secret = os.getenv('secret')
        passphrase = os.getenv('password')
    else:
        print("*** 正在使用实盘环境 ***")
        api_key = os.getenv('prod_apiKey')
        api_secret = os.getenv('prod_secret')
        passphrase = os.getenv('prod_password')

    if not api_key or not api_secret:
        env_type = "模拟盘" if is_sandbox else "实盘"
        print(f"错误：请确保 .env 文件中已为 {env_type} 环境设置了对应的 API Key 和 Secret。")
        return

    # --- 2. 配置交易所 ---
    exchange_id = 'bitget'
    try:
        exchange_class = getattr(ccxt, exchange_id)
    except AttributeError:
        print(f"错误：找不到交易所 '{exchange_id}'。")
        return

    config = {
        'apiKey': api_key,
        'secret': api_secret,
        'options': {
            'defaultType': 'swap',
        },
    }
    if passphrase:
        config['password'] = passphrase

    exchange = exchange_class(config)

    # 设置模拟盘
    if is_sandbox:
        exchange.set_sandbox_mode(True)

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

        total_fees = {}  # 使用字典来分别统计不同币种的手续费

        for i, symbol in enumerate(symbols):
            try:
                print(f"[{i+1}/{len(symbols)}] 正在获取交易对 {symbol} 的成交记录...")
                # 使用分页获取所有交易记录
                trades = fetch_all_trades(exchange, symbol, since_timestamp)

                if trades:
                    print(f"  -> 在 {symbol} 发现 {len(trades)} 条成交记录，正在处理...")
                    for trade in trades:
                        if 'fee' in trade and trade['fee'] is not None and trade['fee'].get('cost') is not None and trade['fee'].get('currency'):
                            fee_cost = trade['fee']['cost']
                            fee_currency = trade['fee']['currency']
                            total_fees[fee_currency] = total_fees.get(fee_currency, 0) + fee_cost
                else:
                    print(f"  -> 在 {symbol} 没有找到符合条件的成交记录")

            except ccxt.NetworkError as e:
                print(f"查询 {symbol} 时发生网络错误: {e}，跳过此交易对。")
            except ccxt.ExchangeError as e:
                print(f"查询 {symbol} 时交易所返回错误: {e}，跳过此交易对。")
            except Exception as e:
                print(f"查询 {symbol} 时发生未知错误: {e}，跳过此交易对。")

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
    try:
        with open('config/symbols.json', 'r') as f:
            symbols_config = json.load(f)
        
        # 筛选出所有启用的交易对
        enabled_symbols = [s for s, c in symbols_config.items() if c.get('enabled', False)]

        if not enabled_symbols:
            print("错误：在 config/symbols.json 中没有找到任何启用的 ('enabled': true) 交易对。")
            sys.exit(1)

        print(f"将要查询以下 {len(enabled_symbols)} 个交易对的费用: {', '.join(enabled_symbols)}")
        calculate_total_fees(symbols=enabled_symbols)

    except FileNotFoundError:
        print("错误：找不到配置文件 'config/symbols.json'。")
        sys.exit(1)
    except json.JSONDecodeError:
        print("错误：配置文件 'config/symbols.json' 格式不正确。")
        sys.exit(1)
    except Exception as e:
        print(f"启动脚本时发生未知错误: {e}")
        sys.exit(1)