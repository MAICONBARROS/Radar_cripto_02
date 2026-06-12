import os
import time
import requests
from datetime import datetime, timezone

COINS = {
    "BTCUSDT": "BTC",
    "ETHUSDT": "ETH",
    "BNBUSDT": "BNB",
    "SOLUSDT": "SOL",
    "XRPUSDT": "XRP",
    "ADAUSDT": "ADA",
    "DOGEUSDT": "DOGE",
    "AVAXUSDT": "AVAX",
    "LINKUSDT": "LINK",
    "TRXUSDT": "TRX"
}

INTERVAL = "4h"
LIMIT = 120

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


def get_klines(symbol):
    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": symbol, "interval": INTERVAL, "limit": LIMIT}
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()

    candles = []
    for item in data:
        candles.append({
            "open": float(item[1]),
            "high": float(item[2]),
            "low": float(item[3]),
            "close": float(item[4]),
            "volume": float(item[5])
        })

    return candles


def ema(values, period):
    if len(values) < period:
        return None

    multiplier = 2 / (period + 1)
    result = sum(values[:period]) / period

    for price in values[period:]:
        result = (price - result) * multiplier + result

    return result


def rsi(values, period=14):
    if len(values) <= period:
        return None

    gains = []
    losses = []

    for i in range(1, len(values)):
        change = values[i] - values[i - 1]
        gains.append(max(change, 0))
        losses.append(abs(min(change, 0)))

    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period

    if avg_loss == 0:
        return 100

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def macd(values):
    ema_12 = ema(values, 12)
    ema_26 = ema(values, 26)

    if ema_12 is None or ema_26 is None:
        return None, None

    macd_line = ema_12 - ema_26

    macd_values = []
    for i in range(26, len(values)):
        short = ema(values[:i + 1], 12)
        long = ema(values[:i + 1], 26)
        if short is not None and long is not None:
            macd_values.append(short - long)

    signal_line = ema(macd_values, 9) if len(macd_values) >= 9 else None
    return macd_line, signal_line


def bollinger(values, period=20):
    if len(values) < period:
        return None, None, None

    recent = values[-period:]
    middle = sum(recent) / period
    variance = sum((x - middle) ** 2 for x in recent) / period
    std = variance ** 0.5

    upper = middle + (2 * std)
    lower = middle - (2 * std)

    return upper, middle, lower


def atr(candles, period=14):
    if len(candles) <= period:
        return None

    trs = []

    for i in range(1, len(candles)):
        high = candles[i]["high"]
        low = candles[i]["low"]
        prev_close = candles[i - 1]["close"]

        tr = max(
            high - low,
            abs(high - prev_close),
            abs(low - prev_close)
        )

        trs.append(tr)

    return sum(trs[-period:]) / period


def heikin_ashi(candles):
    ha = []

    for i, candle in enumerate(candles):
        ha_close = (
            candle["open"] +
            candle["high"] +
            candle["low"] +
            candle["close"]
        ) / 4

        if i == 0:
            ha_open = (candle["open"] + candle["close"]) / 2
        else:
            ha_open = (ha[-1]["open"] + ha[-1]["close"]) / 2

        ha_high = max(candle["high"], ha_open, ha_close)
        ha_low = min(candle["low"], ha_open, ha_close)

        ha.append({
            "open": ha_open,
            "close": ha_close,
            "high": ha_high,
            "low": ha_low
        })

    last = ha[-1]
    previous = ha[-2]

    if last["close"] > last["open"] and previous["close"] > previous["open"]:
        return "ALTA"
    elif last["close"] < last["open"] and previous["close"] < previous["open"]:
        return "BAIXA"
    elif last["close"] > last["open"] and previous["close"] < previous["open"]:
        return "VIRANDO PARA ALTA"
    elif last["close"] < last["open"] and previous["close"] > previous["open"]:
        return "VIRANDO PARA BAIXA"

    return "NEUTRO"


def support_resistance(candles):
    lows = [c["low"] for c in candles[-30:]]
    highs = [c["high"] for c in candles[-30:]]

    support = min(lows)
    resistance = max(highs)

    return support, resistance


def analyze(symbol, name):
    candles = get_klines(symbol)

    closes = [c["close"] for c in candles]
    volumes = [c["volume"] for c in candles]

    price = closes[-1]

    ema_9 = ema(closes, 9)
    ema_21 = ema(closes, 21)
    ema_50 = ema(closes, 50)
    rsi_14 = rsi(closes, 14)
    macd_line, macd_signal = macd(closes)
    bb_upper, bb_middle, bb_lower = bollinger(closes)
    atr_value = atr(candles)
    ha_status = heikin_ashi(candles)
    support, resistance = support_resistance(candles)

    avg_volume = sum(volumes[-30:]) / 30
    volume_strength = volumes[-1] / avg_volume if avg_volume else 1

    score = 0
    reasons = []

    if ema_9 > ema_21:
        score += 2
        reasons.append("EMA 9 acima da EMA 21")
    else:
        score -= 2
        reasons.append("EMA 9 abaixo da EMA 21")

    if ema_21 > ema_50:
        score += 2
        reasons.append("EMA 21 acima da EMA 50")
    else:
        score -= 1
        reasons.append("EMA 21 abaixo da EMA 50")

    if rsi_14 < 30:
        score += 2
        reasons.append("RSI em sobrevenda")
    elif rsi_14 > 70:
        score -= 2
        reasons.append("RSI em sobrecompra")
    elif 40 <= rsi_14 <= 65:
        score += 1
        reasons.append("RSI saudável")

    if macd_line and macd_signal:
        if macd_line > macd_signal:
            score += 2
            reasons.append("MACD positivo")
        else:
            score -= 2
            reasons.append("MACD negativo")

    if ha_status in ["ALTA", "VIRANDO PARA ALTA"]:
        score += 2
        reasons.append(f"Heikin Ashi: {ha_status}")
    elif ha_status in ["BAIXA", "VIRANDO PARA BAIXA"]:
        score -= 2
        reasons.append(f"Heikin Ashi: {ha_status}")

    if volume_strength > 1.2:
        score += 1
        reasons.append("Volume acima da média")
    elif volume_strength < 0.7:
        score -= 1
        reasons.append("Volume fraco")

    if bb_upper and bb_lower:
        if price <= bb_lower:
            score += 1
            reasons.append("Preço perto da banda inferior")
        elif price >= bb_upper:
            score -= 1
            reasons.append("Preço perto da banda superior")

    if score >= 7:
        signal = "🟢 COMPRA FORTE"
    elif score >= 4:
        signal = "🟢 COMPRA MODERADA"
    elif score <= -7:
        signal = "🔴 VENDA FORTE"
    elif score <= -4:
        signal = "🟠 VENDA / REDUZIR"
    else:
        signal = "⚪ AGUARDAR"

    confidence = min(95, max(35, 50 + abs(score) * 6))

    stop = price - (atr_value * 1.5) if atr_value else support
    target_1 = price + (atr_value * 2) if atr_value else resistance
    target_2 = price + (atr_value * 3) if atr_value else resistance

    return {
        "symbol": name,
        "price": price,
        "signal": signal,
        "confidence": confidence,
        "score": score,
        "rsi": rsi_14,
        "macd": macd_line,
        "macd_signal": macd_signal,
        "heikin": ha_status,
        "volume_strength": volume_strength,
        "support": support,
        "resistance": resistance,
        "stop": stop,
        "target_1": target_1,
        "target_2": target_2,
        "reasons": reasons
    }


def send_telegram_message(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print(message)
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }

    response = requests.post(url, json=payload, timeout=30)
    response.raise_for_status()


def format_money(value):
    return f"${value:,.4f}" if value < 10 else f"${value:,.2f}"


def format_report(results):
    now = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")

    valid = [r for r in results if "error" not in r]
    errors = [r for r in results if "error" in r]

    opportunities = sorted(valid, key=lambda x: x["score"], reverse=True)[:3]
    risks = sorted(valid, key=lambda x: x["score"])[:3]

    lines = []
    lines.append("📊 <b>Radar Cripto IA 2.0</b>")
    lines.append(f"🕒 Atualização: {now}")
    lines.append("")
    lines.append("⚠️ <b>Aviso:</b> análise automatizada. Não é recomendação financeira.")
    lines.append("")

    lines.append("🏆 <b>TOP OPORTUNIDADES</b>")
    for i, item in enumerate(opportunities, start=1):
        lines.append(
            f"{i}. <b>{item['symbol']}</b> - {item['signal']} "
            f"({item['confidence']}%)"
        )

    lines.append("")
    lines.append("⚠️ <b>MAIORES RISCOS</b>")
    for i, item in enumerate(risks, start=1):
        lines.append(
            f"{i}. <b>{item['symbol']}</b> - {item['signal']} "
            f"({item['confidence']}%)"
        )

    lines.append("")
    lines.append("📌 <b>DETALHES DAS MOEDAS</b>")
    lines.append("")

    for item in valid:
        lines.append(f"🪙 <b>{item['symbol']}</b>")
        lines.append(f"Sinal: <b>{item['signal']}</b>")
        lines.append(f"Confiança: <b>{item['confidence']}%</b>")
        lines.append(f"Preço: {format_money(item['price'])}")
        lines.append(f"RSI: {item['rsi']:.2f}")
        lines.append(f"Heikin Ashi: {item['heikin']}")
        lines.append(f"Volume: {item['volume_strength']:.2f}x")
        lines.append(f"Suporte: {format_money(item['support'])}")
        lines.append(f"Resistência: {format_money(item['resistance'])}")
        lines.append(f"🛑 Stop: {format_money(item['stop'])}")
        lines.append(f"🎯 Alvo 1: {format_money(item['target_1'])}")
        lines.append(f"🎯 Alvo 2: {format_money(item['target_2'])}")
        lines.append(f"Motivos: {'; '.join(item['reasons'][:4])}")
        lines.append("")

    if errors:
        lines.append("❌ <b>ERROS</b>")
        for item in errors:
            lines.append(f"{item['symbol']}: {item['error']}")

    lines.append("✅ Use stop loss. Evite alavancagem sem experiência.")

    message = "\n".join(lines)

    if len(message) > 3900:
        message = message[:3900] + "\n\nMensagem reduzida pelo limite do Telegram."

    return message


def main():
    results = []

    for symbol, name in COINS.items():
        try:
            result = analyze(symbol, name)
            results.append(result)
            time.sleep(2)

        except Exception as error:
            results.append({
                "symbol": name,
                "error": str(error)
            })

    report = format_report(results)
    send_telegram_message(report)


if __name__ == "__main__":
    main()
