from util.sLogger import logger
import asyncio

async def openOrderFilter(orders,symbolName):
    target = []
    for order in orders:
        if order['symbol'] == symbolName and order['status'] == 'open':
            target.append(order)
            # logger.info(f"找到{symbolName}未成交订单: {order['id']}")
    return target

#根据id查找订单
async def findOrderById(orders,orderId):
    for order in orders:
        if order['id'] == orderId:
            return order
    return None

async def positionMarginSize(position,symbolName):
    if len(position) == 0:
        return 0.0
    marginSize = 0.0
    for pos in position:
      # logger.info(pos)
      if pos['symbol'] == symbolName:
          marginSize += float(pos['info']['marginSize'])
    return marginSize

# 获取指定交易对的所有仓位（支持双向持仓）
async def getPositionsBySymbol(positions, symbolName):
    """获取指定交易对的所有仓位"""
    symbol_positions = []
    for pos in positions:
        if pos['symbol'] == symbolName:
            symbol_positions.append(pos)
    return symbol_positions

# 计算净持仓数量（做多数量 - 做空数量）
async def calculateNetPosition(positions, symbolName):
    """计算净持仓数量，做多为正，做空为负"""
    long_size = 0.0
    short_size = 0.0
    
    for pos in positions:
        if pos['symbol'] == symbolName:
            if pos['side'] == 'long':
                long_size += float(pos['contracts'])
            elif pos['side'] == 'short':
                short_size += float(pos['contracts'])
    
    # 净持仓 = 做多数量 - 做空数量
    net_position = long_size - short_size
    return net_position, long_size, short_size

# 获取指定方向的仓位
async def getPositionBySide(positions, symbolName, side):
    """获取指定交易对和方向的仓位"""
    for pos in positions:
        if pos['symbol'] == symbolName and pos['side'] == side:
            return pos
    return None

#检查当前订单列表未成交的订单数量是不是2，且是不是1个买单和1个卖单
async def checkOpenOrder(openOrders):
    if len(openOrders) != 2:
        return False
    buyCount = 0
    sellCount = 0
    for order in openOrders:
        if order['info']['side'] == 'buy':
            buyCount += 1
        elif order['info']['side'] == 'sell':
            sellCount += 1
    if buyCount == 1 and sellCount == 1:
        return True
    return False
