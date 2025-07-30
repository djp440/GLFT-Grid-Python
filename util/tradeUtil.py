from util.sLogger import logger

def openOrderFilter(orders,symbolName):
    target = []
    for order in orders:
        if order['symbol'] == symbolName and order['status'] == 'open':
            target.append(order)
    return target

def positionMarginSize(position,symbolName):
    if len(position) == 0:
        return 0.0
    marginSize = 0.0
    for pos in position:
      # logger.info(pos)
      if pos['symbol'] == symbolName:
          marginSize = float(pos['info']['marginSize'])
    return marginSize

#检查当前订单列表未成交的订单数量是不是2，且是不是1个买单和1个卖单
def checkOpenOrder(openOrders):
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
