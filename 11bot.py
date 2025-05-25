import requests
import time
from telegram import Bot

# 配置项
BINANCE_API_BASE = 'https://api.binance.com'
TELEGRAM_TOKEN = '7716824946:AAG30yV7U894-E0TmS2xFhf-1z7TvPZ_WAg'
CHAT_ID = '你的chat id'
SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'OPUSDT', 'DOGEUSDT']  # 可自定义币种

VOLUME_MULTIPLIER = 2.0  # 成交量暴涨倍数
PERCENT_CHANGE_THRESHOLD = 3.0  # 涨幅阈值，单位 %

bot = Bot(TELEGRAM_TOKEN)

# 获取K线数据
def get_klines(symbol, interval='5m', limit=20):
    url = f"{BINANCE_API_BASE}/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    response = requests.get(url)
    return response.json()

# 获取资金费率
def get_funding_rate(symbol):
    url = f"{BINANCE_API_BASE}/fapi/v1/premiumIndex?symbol={symbol}"
    response = requests.get(url)
    data = response.json()
    return float(data['lastFundingRate']) * 100  # 转百分比

# 监控函数
def monitor_market():
    while True:
        for symbol in SYMBOLS:
            try:
                klines = get_klines(symbol)
                volumes = [float(k[5]) for k in klines[:-1]]  # 前19根
                last_volume = float(klines[-1][5])
                avg_volume = sum(volumes) / len(volumes)

                # 涨跌幅 %
                open_price = float(klines[-1][1])
                close_price = float(klines[-1][4])
                percent_change = ((close_price - open_price) / open_price) * 100

                # 资金费率
                funding_rate = get_funding_rate(symbol)

                # 成交量暴涨
                if last_volume > avg_volume * VOLUME_MULTIPLIER:
                    bot.send_message(chat_id=CHAT_ID, text=f"🚨 {symbol} 成交量暴涨！\n当前: {last_volume:.2f}\n均值: {avg_volume:.2f}")

                # 涨幅异常
                if abs(percent_change) > PERCENT_CHANGE_THRESHOLD:
                    bot.send_message(chat_id=CHAT_ID, text=f"🚨 {symbol} 短时涨幅异常！\n涨跌: {percent_change:.2f}%")

                # 资金费率异常
                if abs(funding_rate) > 0.1:
                    bot.send_message(chat_id=CHAT_ID, text=f"⚠️ {symbol} 资金费率异常！\n当前: {funding_rate:.4f}%")

                time.sleep(1)

            except Exception as e:
                print(f"出错了：{e}")
                continue

        time.sleep(60)  # 每60秒轮询一轮

# 启动监控
if __name__ == "__main__":
    monitor_market()
