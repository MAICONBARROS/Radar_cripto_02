import os
import math
import requests
from datetime import datetime, timezone

# ==========================
# CONFIGURAÇÕES DO BOT
# ==========================

COINS = {
    "bitcoin": "BTC",
    "ethereum": "ETH",
    "solana": "SOL"
}

VS_CURRENCY = "usd"
DAYS_HISTORY = 30

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Se quiser testar localmente, você pode definir:
# TELEGRAM_BOT_TOKEN = "SEU_TOKEN_AQUI"
# TELEGRAM_CHAT_ID = "SEU_CHAT_ID_AQUI"


# ==========================
# FUNÇÕES DE INDICADORES
# ==========================

def calculate_ema(values, period):
    if len(values) < period:
        return None

    multiplier = 2 / (period + 1)
    ema = sum(values[:period]) / period

    for price in values[period:]:
        ema = (price - ema) * multiplier + ema

    return ema


def calculate_rsi(values, period=14):
    if len(values) <= period:
        return None

    gains = []
    losses = []

    for i in range(1, len(values)):
        change = values[i] - values[i - 1]
        if change >= 0:
            gains.append(change)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(change))

    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period

    if avg_loss == 0:
        return 100

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calculate_variation(values):
    if len(values) < 2:
        return 0
    return ((values[-1] - values[-2]) / values[-2]) * 100


# ==========================
# BUSCA DE DADOS
# ==========================

def get_market_chart(coin_id):
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
    params = {
        "vs_currency": VS_CURRENCY,
        "days": DAYS_HISTORY
    }

    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()

    prices = [item[1] for item in data.get("prices", [])]
    volumes = [item[1] for item in data.get("total_volumes", [])]

    return prices, volumes


# ==========================
# REGRA DE DECISÃO
# ==========================

def analyze_coin(coin_id, symbol):
    prices, volumes = get_market_chart(coin_id)

    if len(prices) < 50:
        return {
            "symbol": symbol,
            "signal": "SEM DADOS",
            "confidence": 0,
            "reason": "Poucos dados retornados pela API."
        }

    current_price = prices[-1]
    rsi = calculate_rsi(prices, 14)
    ema_9 = calculate_ema(prices, 9)
    ema_21 = calculate_ema(prices, 21)
    ema_50 = calculate_ema(prices, 50)
    variation = calculate_variation(prices)

    avg_volume = sum(volumes[-30:]) / 30 if len(volumes) >= 30 else sum(volumes) / len(volumes)
    current_volume = volumes[-1]
    volume_strength = current_volume / avg_volume if avg_volume else 1

    score = 0
    reasons = []

    # Tendência pelas médias móveis
    if ema_9 and ema_21 and ema_9 > ema_21:
        score += 2
        reasons.append("EMA 9 acima da EMA 21, tendência curta positiva")
    else:
        score -= 2
        reasons.append("EMA 9 abaixo da EMA 21, tendência curta fraca")

    if ema_21 and ema_50 and ema_21 > ema_50:
        score += 2
        reasons.append("EMA 21 acima da EMA 50, tendência média positiva")
    else:
        score -= 1
        reasons.append("EMA 21 abaixo da EMA 50, atenção na tendência média")

    # RSI
    if rsi is not None:
        if rsi < 30:
            score += 2
            reasons.append("RSI abaixo de 30, possível sobrevenda")
        elif rsi > 70:
            score -= 2
            reasons.append("RSI acima de 70, possível sobrecompra")
        elif 45 <= rsi <= 60:
            score += 1
            reasons.append("RSI em zona saudável")
        else:
            reasons.append("RSI em zona neutra")

    # Volume
    if volume_strength > 1.2:
        score += 1
        reasons.append("Volume acima da média")
    elif volume_strength < 0.7:
        score -= 1
        reasons.append("Volume abaixo da média")

    # Variação recente
    if variation > 3:
        score += 1
        reasons.append("Preço subindo forte no curto prazo")
    elif variation < -3:
        score -= 1
        reasons.append("Preço caindo forte no curto prazo")

    # Decisão final
    if score >= 4:
        signal = "COMPRA"
    elif score <= -4:
        signal = "VENDA / REDUZIR POSIÇÃO"
    else:
        signal = "AGUARDAR"

    confidence = min(95, max(30, 50 + abs(score) * 8))

    return {
        "symbol": symbol,
        "price": current_price,
        "rsi": rsi,
        "ema_9": ema_9,
        "ema_21": ema_21,
        "ema_50": ema_50,
        "variation": variation,
        "volume_strength": volume_strength,
        "score": score,
        "signal": signal,
        "confidence": confidence,
        "reason": "; ".join(reasons)
    }


# ==========================
# TELEGRAM
# ==========================

def send_telegram_message(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram não configurado. Mensagem abaixo:")
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


def format_report(results):
    now = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")

    lines = []
    lines.append("📊 <b>Radar Cripto IA</b>")
    lines.append(f"🕒 Atualização: {now}")
    lines.append("")
    lines.append("⚠️ <b>Aviso:</b> isto é análise automatizada, não é recomendação financeira.")
    lines.append("")

    for item in results:
        lines.append(f"🪙 <b>{item['symbol']}</b>")
        lines.append(f"Sinal: <b>{item['signal']}</b>")
        lines.append(f"Confiança: <b>{item['confidence']}%</b>")

        if "price" in item:
            lines.append(f"Preço: ${item['price']:,.2f}")
            lines.append(f"RSI: {item['rsi']:.2f}" if item["rsi"] is not None else "RSI: indisponível")
            lines.append(f"Variação curta: {item['variation']:.2f}%")
            lines.append(f"Força do volume: {item['volume_strength']:.2f}x")
            lines.append(f"Score técnico: {item['score']}")

        lines.append(f"Motivo: {item['reason']}")
        lines.append("")

    lines.append("✅ Regra de ouro: use stop loss e nunca opere alavancado sem experiência.")
    return "\n".join(lines)


def main():
    results = []

    for coin_id, symbol in COINS.items():
        try:
            result = analyze_coin(coin_id, symbol)
            results.append(result)
        except Exception as error:
            results.append({
                "symbol": symbol,
                "signal": "ERRO",
                "confidence": 0,
                "reason": str(error)
            })

    report = format_report(results)
    send_telegram_message(report)


if __name__ == "__main__":
    main()