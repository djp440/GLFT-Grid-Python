import ccxt
import ccxt.pro
import asyncio
import core.tradeManager
from core.enhancedTradeManager import EnhancedTradeManager
import core.websocketManager
from util.sLogger import logger
import os
from dotenv import load_dotenv
import signal
import sys
import json
from core.chartManager import chart_manager
from core.dataRecorder import data_recorder
from config.config import GlobalConfig

load_dotenv()
# 读取沙盒环境配置
apiKey = os.getenv("apiKey")
secret = os.getenv("secret")
password = os.getenv("password")
# 读取实盘环境配置
prod_apiKey = os.getenv("prod_apiKey")
prod_secret = os.getenv("prod_secret")
prod_password = os.getenv("prod_password")
sandbox = os.getenv("sandbox")
# 读取图表开关配置
enable_charts = os.getenv("enable_charts", "True").lower() == "true"

# 根据sandbox参数选择API配置
if sandbox == "False":
    # 实盘模式，使用实盘API配置
    current_apiKey = prod_apiKey
    current_secret = prod_secret
    current_password = prod_password
    is_sandbox = False
    logger.info("使用实盘API配置")
else:
    # 沙盒模式，使用沙盒API配置
    current_apiKey = apiKey
    current_secret = secret
    current_password = password
    is_sandbox = True
    logger.info("使用沙盒API配置")

# 全局变量
exchangeWS = None
shutdown_event = None
tasks = []
running = False
symbol_tasks = {}  # 存储每个交易对的任务组
symbol_managers = {}  # 存储每个交易对的管理器


def load_symbols_config():
    """加载交易对配置"""
    try:
        config_path = os.path.join(os.path.dirname(
            __file__), 'config', 'symbols.json')
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        # 将对象格式转换为数组格式，只返回启用的交易对
        enabled_symbols = []
        for symbol_name, symbol_config in config.items():
            if symbol_config.get('enabled', False):
                # 添加symbol字段
                symbol_config['symbol'] = symbol_name
                enabled_symbols.append(symbol_config)

        logger.info(f"加载配置文件成功，启用的交易对数量: {len(enabled_symbols)}")
        return enabled_symbols
    except FileNotFoundError:
        logger.warning("配置文件不存在，使用默认配置")
        os._exit(1)

    except Exception as e:
        logger.error(f"加载配置文件失败: {e}，使用默认配置")
        os._exit(1)


async def runWebsocketTask(symbol_config: dict):
    """为单个交易对运行websocket任务"""
    global symbol_tasks, symbol_managers

    symbolName = symbol_config['symbol']
    level = symbol_config['level']
    coin = symbol_config['coin']

    try:
        # 为每个交易对创建独立的交易所连接
        exchangeBitget = ccxt.pro.bitget({
            'apiKey': current_apiKey,
            'secret': current_secret,
            'password': current_password,
            'options': {
                'defaultType': 'swap',
            },
            'sandbox': is_sandbox
        })
        logger.info(f"开始初始化交易对 {symbolName}")
        await exchangeBitget.set_position_mode(True, symbolName, {'productType': 'USDT-FUTURES'})
        logger.info(f"交易对 {symbolName} 持仓模式设置为双向")
        await exchangeBitget.set_leverage(level, symbolName, {'productType': 'USDT-FUTURES'})
        logger.info(f"交易对 {symbolName} 杠杆设置为 {level}")

        # 检查是否使用增强版交易管理器
        config = GlobalConfig()
        use_enhanced = config.TradeConfig.USE_ENHANCED_MANAGER
        
        if use_enhanced:
            logger.info(f"为 {symbolName} 使用增强版交易管理器")
            tm = EnhancedTradeManager(
                symbolName,
                exchangeBitget,
                baseSpread=symbol_config.get('baseSpread', 0.001),
                minSpread=symbol_config.get('minSpread', 0.0008),
                maxSpread=symbol_config.get('maxSpread', 0.003),
                orderCoolDown=symbol_config.get('orderCoolDown', 0.1),
                maxStockRadio=symbol_config.get('maxStockRadio', 0.25),
                orderAmountRatio=symbol_config.get('orderAmountRatio', 0.05),
                coin=symbol_config.get('coin', 'USDT'),
                direction=symbol_config.get('direction', 'both')
            )
        else:
            logger.info(f"为 {symbolName} 使用标准交易管理器")
            tm = core.tradeManager.TradeManager(
                symbolName,
                exchangeBitget,
                baseSpread=symbol_config.get('baseSpread', 0.001),
                minSpread=symbol_config.get('minSpread', 0.0008),
                maxSpread=symbol_config.get('maxSpread', 0.003),
                orderCoolDown=symbol_config.get('orderCoolDown', 0.1),
                maxStockRadio=symbol_config.get('maxStockRadio', 0.25),
                orderAmountRatio=symbol_config.get('orderAmountRatio', 0.05),
                coin=symbol_config.get('coin', 'USDT'),
                direction=symbol_config.get('direction', 'both')
            )
        await tm.initSymbolInfo()
        wm = core.websocketManager.WebSocketManager(
            symbolName, exchangeBitget, tm)

        # 存储管理器引用
        symbol_managers[symbolName] = {
            'tradeManager': tm,
            'websocketManager': wm,
            'exchange': exchangeBitget
        }

        # 创建定期检查任务
        async def periodic_check():
            """定期检查交易状态并自动恢复"""
            while True:
                try:
                    await asyncio.sleep(10)  # 每10秒检查一次
                    await tm.checkAndRecoverTrading()
                except asyncio.CancelledError:
                    logger.info(f"{symbolName}定期检查任务被取消")
                    break
                except Exception as e:
                    logger.error(f"{symbolName}定期检查任务发生错误: {e}")
                    await asyncio.sleep(5)  # 出错后等待5秒再继续

        # 创建该交易对的任务组
        symbol_task_list = [
            asyncio.create_task(wm.watchTicker()),
            asyncio.create_task(wm.watchMyBalance()),
            asyncio.create_task(wm.watchMyPosition()),
            asyncio.create_task(wm.watchMyOrder()),
            asyncio.create_task(wm.watchOpenOrder()),
            asyncio.create_task(periodic_check()),  # 添加定期检查任务
        ]
        
        # 启动波动率监控任务
        volatility_task = await tm.startVolatilityMonitoring()
        if volatility_task:
            symbol_task_list.append(volatility_task)
            logger.info(f"交易对 {symbolName} 波动率监控任务已添加")

        # 存储任务引用
        symbol_tasks[symbolName] = symbol_task_list

        # 绑定websocket管理器并开始交易
        await tm.bindWebsocketManager(wm)
        logger.info(f"交易对 {symbolName} 开始执行初始交易")
        try:
            await tm.runTrade()
            logger.info(f"交易对 {symbolName} 初始交易执行完成")
        except Exception as e:
            logger.error(f"交易对 {symbolName} 初始交易执行失败: {e}")

        logger.info(f"交易对 {symbolName} 初始化完成，开始运行")

        # 等待关闭事件或任务完成
        done, pending = await asyncio.wait(
            symbol_task_list + [asyncio.create_task(shutdown_event.wait())],
            return_when=asyncio.FIRST_COMPLETED
        )

        # 取消所有挂起的任务
        for task in pending:
            if not task.done():
                task.cancel()

        # 等待任务完成取消（设置超时避免无限等待）
        if pending:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*pending, return_exceptions=True),
                    timeout=5.0
                )
            except asyncio.TimeoutError:
                logger.warning(f"交易对 {symbolName} 任务取消超时")

    except asyncio.CancelledError:
        logger.info(f"交易对 {symbolName} 任务被取消")
    except Exception as e:
        logger.error(f"交易对 {symbolName} 运行时错误: {e}")
    finally:
        # 清理该交易对的资源
        await cleanup_symbol_resources(symbolName)


async def cleanup_symbol_resources(symbolName: str):
    """清理单个交易对的资源"""
    global symbol_managers, symbol_tasks

    # 清理交易所连接
    if symbolName in symbol_managers:
        # 停止波动率监控
        trade_manager = symbol_managers[symbolName].get('tradeManager')
        if trade_manager:
            try:
                trade_manager.stopVolatilityMonitoring()
                logger.info(f"交易对 {symbolName} 的波动率监控已停止")
            except Exception as e:
                logger.error(f"停止交易对 {symbolName} 的波动率监控时出错: {e}")
        
        exchange = symbol_managers[symbolName].get('exchange')
        if exchange:
            try:
                await exchange.close()
                logger.info(f"交易对 {symbolName} 的交换所连接已关闭")
            except Exception as e:
                logger.error(f"关闭交易对 {symbolName} 的交换所连接时出错: {e}")

        # 移除管理器引用
        del symbol_managers[symbolName]

    # 移除任务引用
    if symbolName in symbol_tasks:
        del symbol_tasks[symbolName]


async def cleanup_resources():
    """清理所有资源"""
    global symbol_managers, symbol_tasks

    # 停止图表管理器并生成最终报告（如果启用了图表功能）
    try:
        if enable_charts:
            chart_manager.stop_charts()  # 这会生成最终图表
            logger.info("图表管理器已停止，最终报告已生成")
        data_recorder.stop()
        logger.info("数据记录器已停止")
    except Exception as e:
        logger.error(f"停止图表管理器或数据记录器时发生错误: {e}")

    # 清理所有交易对的资源
    for symbolName in list(symbol_managers.keys()):
        await cleanup_symbol_resources(symbolName)

    logger.info("所有资源清理完成")


def signal_handler(signum, frame):
    """信号处理器"""
    global shutdown_event
    logger.info("收到中断信号，准备关闭程序")
    if shutdown_event and not shutdown_event.is_set():
        shutdown_event.set()


async def runMultipleSymbols(symbol_configs: list):
    """运行多个交易对"""
    global shutdown_event

    # 为每个交易对创建任务
    symbol_main_tasks = []
    for symbol_config in symbol_configs:
        task = asyncio.create_task(runWebsocketTask(symbol_config))
        symbol_main_tasks.append(task)
        logger.info(f"已创建交易对 {symbol_config['symbol']} 的主任务")

    try:
        # 等待所有任务完成或关闭事件
        done, pending = await asyncio.wait(
            symbol_main_tasks + [asyncio.create_task(shutdown_event.wait())],
            return_when=asyncio.FIRST_COMPLETED
        )

        # 如果是关闭事件触发，取消所有任务
        if shutdown_event.is_set():
            logger.info("收到关闭信号，正在停止所有交易对...")
            for task in pending:
                if not task.done():
                    task.cancel()

            # 等待所有任务完成取消
            if pending:
                try:
                    await asyncio.wait_for(
                        asyncio.gather(*pending, return_exceptions=True),
                        timeout=10.0
                    )
                except asyncio.TimeoutError:
                    logger.warning("部分任务取消超时")

    except Exception as e:
        logger.error(f"多交易对运行错误: {e}")
        # 取消所有任务
        for task in symbol_main_tasks:
            if not task.done():
                task.cancel()


async def main_async():
    """异步主函数"""
    global shutdown_event
    shutdown_event = asyncio.Event()

    try:
        # 根据配置决定是否启动图表管理器
        if enable_charts:
            logger.info("启动图表管理器...")
            chart_manager.start_charts()
        else:
            logger.info("图表功能已禁用，跳过图表启动")

        # 从配置文件加载交易对
        symbol_configs = load_symbols_config()
        symbol_names = [config['symbol'] for config in symbol_configs]

        logger.info(f"准备启动多交易对网格交易，交易对: {symbol_names}")

        await runMultipleSymbols(symbol_configs)
    except KeyboardInterrupt:
        logger.info("程序被手动中断")
    except Exception as e:
        logger.error(f"程序运行错误: {e}")
    finally:
        await cleanup_resources()
        logger.info("程序清理完成")


def main():
    """主函数"""
    # 设置信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    if hasattr(signal, 'SIGTERM'):
        signal.signal(signal.SIGTERM, signal_handler)

    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        logger.info("程序已手动中断")
    except Exception as e:
        logger.error(f"程序启动错误: {e}")
    finally:
        logger.info("程序已退出")


if __name__ == "__main__":
    main()
