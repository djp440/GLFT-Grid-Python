import ccxt
import ccxt.pro
import asyncio
import core.tradeManager
import core.websocketManager
from util.sLogger import logger
import os
from dotenv import load_dotenv
import signal
import sys

load_dotenv()
apiKey = os.getenv("apiKey")
secret = os.getenv("secret")
password = os.getenv("password")
okx_apiKey = os.getenv("okx_apiKey")
okx_secret = os.getenv("okx_secret")
okx_password = os.getenv("okx_password")
sandbox = os.getenv("sandbox")

# 全局变量
exchangeWS = None
shutdown_event = None
tasks = []
running = False

async def runWebsocketTask(symbolName: str):
    global exchangeWS, tasks
    try:
        exchangeBitget = ccxt.pro.bitget({
            'apiKey': apiKey,
            'secret': secret,
            'password': password,
            'options': {
                'defaultType': 'swap',
            },
            'sandbox': sandbox == "True"
        })
        exchangeOkx = ccxt.pro.okx({
            'apiKey': okx_apiKey,
            'secret': okx_secret,
            'password': okx_password,
            'options': {
                'defaultType': 'future',
            },
            'sandbox': sandbox == "True"
        })

        exchangeWS = exchangeBitget
        # test = await exchangeWS.loadMarkets()
        # logger.info(test[symbolName])
        tm = core.tradeManager.TradeManager(symbolName, exchangeWS)
        await tm.initSymbolInfo()
        wm = core.websocketManager.WebSocketManager(symbolName, exchangeWS, tm)
        
        # 创建任务并存储引用
        tasks = [
            asyncio.create_task(wm.watchTicker()),
            asyncio.create_task(wm.watchMyBalance()),
            asyncio.create_task(wm.watchMyPosition()),
            asyncio.create_task(wm.watchMyOrder()),
            asyncio.create_task(wm.watchOpenOrder()),
        ]
        #我想让这两行在上面5个任务被初始化后被执行
        await tm.bindWebsocketManager(wm)
        await tm.runTrade()
        
        # 等待关闭事件或任务完成
        done, pending = await asyncio.wait(
            tasks + [asyncio.create_task(shutdown_event.wait())],
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
                logger.warning("任务取消超时")
        
    except asyncio.CancelledError:
        logger.info("主任务被取消")
    except Exception as e:
        logger.error(f"运行时错误: {e}")
    finally:
        # 清理资源
        await cleanup_resources()

async def cleanup_resources():
    """清理资源"""
    global exchangeWS
    if exchangeWS:
        try:
            await exchangeWS.close()
            logger.info("交换所连接已关闭")
        except Exception as e:
            logger.error(f"关闭交换所连接时出错: {e}")
        finally:
            exchangeWS = None

def signal_handler(signum, frame):
    """信号处理器"""
    global shutdown_event
    logger.info("收到中断信号，准备关闭程序")
    if shutdown_event and not shutdown_event.is_set():
        shutdown_event.set()

async def main_async():
    """异步主函数"""
    global shutdown_event
    shutdown_event = asyncio.Event()
    
    try:
        await runWebsocketTask("ETH/USDT:USDT")
    except KeyboardInterrupt:
        logger.info("程序被手动中断")
    except Exception as e:
        logger.error(f"程序运行错误: {e}")
    finally:
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