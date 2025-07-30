def openOrderFilter(orders,symbolName):
    target = []
    for order in orders:
        if order['symbol'] == symbolName and order['status'] == 'open':
            target.append(order)
    return target

def positionMarginSize(position,symbolName):
    marginSize = 0
    for pos in position:
        if pos['symbol'] == symbolName:
            marginSize = pos['marginSize']
    return marginSize