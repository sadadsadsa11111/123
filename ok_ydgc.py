from okx import Trade as Trade
from okx import MarketData as MarketData
from okx import Account as Account
import time
import math
from decimal import Decimal
import uuid

# API initialization (replace with your actual API keys)
api_key = ""
secret_key = ""
passphrase = ""
flag = "0"  # Real trading: 0, Demo trading: 1

# Initialize OKX APIs
tradeAPI = Trade.TradeAPI(api_key, secret_key, passphrase, False, flag)
marketAPI = MarketData.MarketAPI(flag=flag)
accountAPI = Account.AccountAPI(api_key, secret_key, passphrase, False, flag)

# Trading parameters
instId = "WIF-USDT-SWAP"  # Trading pair
leverage = "10"  # 杠杆倍数
initial_investment = 2  # Initial investment in USDT
tp_rate = 0.05  # 5% 止盈
sl_rate = 0.05  # 5% 止损
td_mode = "isolated"  # Isolated margin mode
pos_side = "long"  # 方向

# Global flag to stop trading after stop-loss
stop_trading = False

def get_market_price():
    """Get the latest market price."""
    result = marketAPI.get_ticker(instId=instId)
    if result["code"] == "0":
        return float(result["data"][0]["last"])
    else:
        print(f"Error fetching market price: {result['msg']}")
        return None

def place_market_order(size, side):
    """下市价单"""
    clOrdId = uuid.uuid4().hex  # 移除连字符，生成 32 字符 ID
    result = tradeAPI.place_order(
        instId=instId,
        tdMode=td_mode,
        side=side,
        ordType="market",
        sz=str(size),
        posSide=pos_side,
        clOrdId=clOrdId
    )
    if result["code"] == "0":
        print(f"{side.capitalize()} 订单下单成功: {size} USDT")
        return result["data"][0]["ordId"]
    print(f"下单失败 {side}: {result['data'][0]['sMsg']}")
    return None

def place_take_profit_stop_loss(order_price, size):
    """Set take-profit and stop-loss orders."""
    # Calculate TP and SL prices
    tp_price = order_price * (1 + tp_rate) if pos_side == "long" else order_price * (1 - tp_rate)
    sl_price = order_price * (1 - sl_rate) if pos_side == "long" else order_price * (1 + sl_rate)
    
    # Round prices to appropriate precision
    precision = abs(Decimal(str(order_price)).as_tuple().exponent)
    tp_price = float(format(tp_price, f".{precision}f"))
    sl_price = float(format(sl_price, f".{precision}f"))

    # Place TP/SL order using algo order
    clOrdId = str(uuid.uuid4())
    result = tradeAPI.place_algo_order(
        instId=instId,
        tdMode=td_mode,
        side="sell" if pos_side == "long" else "buy",
        ordType="oco",
        sz=str(size),
        posSide=pos_side,
        tpTriggerPx=str(tp_price),
        tpOrdPx="-1",  # Market order for TP
        slTriggerPx=str(sl_price),
        slOrdPx="-1"   # Market order for SL
    )
    if result["code"] == "0":
        print(f"TP/SL set: TP at {tp_price}, SL at {sl_price}")
        return result["data"][0]["algoId"]
    else:
        print(f"Failed to set TP/SL: {result['data'][0]['sMsg']}")
        return None

def get_position():
    """Get current position details."""
    result = accountAPI.get_positions(instType="SWAP", instId=instId)
    if result["code"] == "0" and result["data"]:
        return result["data"][0]
    return None

def get_account_balance():
    """Get USDT balance."""
    result = accountAPI.get_account_balance(ccy="USDT")
    if result["code"] == "0":
        return float(result["data"][0]["details"][0]["availBal"])
    return 0

def main():
    global stop_trading
    # Set leverage
    accountAPI.set_leverage(instId=instId, lever=leverage, mgnMode=td_mode)
    
    # Initial investment
    current_investment = initial_investment
    
    while not stop_trading:
        # Get current market price
        market_price = get_market_price()
        if not market_price:
            time.sleep(5)
            continue
        
        # Calculate position size
        quantity = math.floor((current_investment * float(leverage)) / market_price)
        if quantity <= 0:
            print("Insufficient funds to open position.")
            time.sleep(60)
            continue
        
        # Place market order
        order_id = place_market_order(quantity, "buy" if pos_side == "long" else "sell")
        if not order_id:
            time.sleep(5)
            continue
        
        # Wait for order to fill
        time.sleep(2)
        order_info = tradeAPI.get_order(instId=instId, ordId=order_id)
        if order_info["code"] == "0" and order_info["data"][0]["state"] == "filled":
            avg_price = float(order_info["data"][0]["avgPx"])
            # Set TP/SL
            algo_id = place_take_profit_stop_loss(avg_price, quantity)
            if not algo_id:
                tradeAPI.cancel_order(instId=instId, ordId=order_id)
                continue
            
            # Monitor TP/SL
            while True:
                algo_order = get_orders_algo_history(instId, algo_id)
                if algo_order["code"] == "0" and algo_order["data"]:
                    status = algo_order["data"][0]["state"]
                    if status in ["canceled", "filled"]:
                        if algo_order["data"][0]["slTriggerPx"]:
                            print("Stop-loss triggered. Stopping trading.")
                            stop_trading = True
                            break
                        elif algo_order["data"][0]["tpTriggerPx"]:
                            print("Take-profit triggered. Reinvesting profits.")
                            # Update investment with profits
                            current_investment += current_investment * tp_rate
                            break
                time.sleep(5)
        
        # Wait before opening new position
        time.sleep(60)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {e}")
        time.sleep(60)
