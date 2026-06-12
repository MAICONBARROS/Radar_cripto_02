# Radar Cripto IA

Bot gratuito em Python para analisar BTC, ETH e SOL e enviar sinais no Telegram.

## O que ele faz

- Busca histórico de preço pela CoinGecko.
- Calcula RSI, EMA 9, EMA 21 e EMA 50.
- Analisa volume.
- Gera sinal: COMPRA, VENDA / REDUZIR POSIÇÃO ou AGUARDAR.
- Envia relatório no Telegram.

## Arquivos

- `bot.py`: script principal.
- `requirements.txt`: dependências.
- `.github/workflows/radar-cripto.yml`: automação gratuita no GitHub Actions.

## Como configurar o Telegram

1. Abra o Telegram.
2. Procure por `@BotFather`.
3. Envie `/newbot`.
4. Copie o token do bot.
5. Envie uma mensagem qualquer para o seu bot.
6. Para descobrir seu chat_id, abra no navegador:

https://api.telegram.org/botSEU_TOKEN/getUpdates

Substitua `SEU_TOKEN` pelo token real.

## Como configurar no GitHub

1. Crie um repositório no GitHub.
2. Envie estes arquivos.
3. Vá em Settings > Secrets and variables > Actions.
4. Crie os secrets:
   - TELEGRAM_BOT_TOKEN
   - TELEGRAM_CHAT_ID
5. Vá em Actions e rode manualmente pela primeira vez.

## Aviso

Este bot não faz recomendação financeira. Ele apenas gera alertas técnicos.