from util.sLogger import logger
import asyncio

async def openOrderFilter(orders,symbolName):
    target = []
    for order in orders:
        if order['symbol'] == symbolName and order['status'] == 'open':
            target.append(order)
            logger.info(f"找到{symbolName}未成交订单: {order['id']}")
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
          marginSize = float(pos['info']['marginSize'])
    return marginSize

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
