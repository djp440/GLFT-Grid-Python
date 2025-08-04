import ccxt
import ccxt.pro
import asyncio
from util.sLogger import logger
import os
from dotenv import load_dotenv


async def devMode():
    exchange = ccxt.pro.bitget({
        'apiKey': os.getenv('prod_apiKey'),
        'secret': os.getenv('prod_secret'),
        'password': os.getenv('prod_password'),
        'enableRateLimit': True,
        'sandbox': False,
        'options': {
            'defaultType': 'swap',
        }
    })
    symbol = "SBTC/SUSDT:SUSDT"
    try:
        # 测试获取仓位信息
        logger.info("=== 测试获取仓位信息 ===")
        positions = await exchange.fetch_positions([symbol], params={
            'productType': 'SUSDT-FUTURES'
        })
        logger.info(f"原始仓位数据: {positions}")
        
        # 测试双向持仓计算
        from util import tradeUtil
        
        # 获取指定交易对的所有仓位
        symbol_positions = await tradeUtil.getPositionsBySymbol(positions, symbol)
        logger.info(f"交易对 {symbol} 的所有仓位: {len(symbol_positions)} 个")
        
        # 计算净持仓
        net_position, long_size, short_size = await tradeUtil.calculateNetPosition(positions, symbol)
        logger.info(f"净持仓计算结果 - 做多:{long_size}, 做空:{short_size}, 净持仓:{net_position}")
        
        # 获取做多仓位
        long_pos = await tradeUtil.getPositionBySide(positions, symbol, 'long')
        if long_pos:
            logger.info(f"做多仓位: {long_pos['contracts']} 合约")
        else:
            logger.info("无做多仓位")
            
        # 获取做空仓位
        short_pos = await tradeUtil.getPositionBySide(positions, symbol, 'short')
        if short_pos:
            logger.info(f"做空仓位: {short_pos['contracts']} 合约")
        else:
            logger.info("无做空仓位")
            
        # 测试余额获取
        logger.info("\n=== 测试余额获取 ===")
        balance = await exchange.fetchBalance()
        logger.info(f"余额信息: {balance}")
        
        if 'SUSDT' in balance:
            logger.info(f"SUSDT余额: {balance['SUSDT']}")
        else:
            logger.info("未找到SUSDT余额，将使用假定值: 2534.7881")
            
    except Exception as e:
        logger.error(f"错误: {e}")
        import traceback
        logger.error(f"详细错误信息: {traceback.format_exc()}")
    finally:
        await exchange.close()


def main():
    load_dotenv()
    asyncio.run(devMode())


if __name__ == "__main__":
    main()
