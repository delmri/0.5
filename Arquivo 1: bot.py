import logging
import os
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import pytesseract
import cv2
import re
from flask import Flask, request

# ===================== CONFIGURAÇÃO =====================
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("Defina a variável de ambiente BOT_TOKEN")

logging.basicConfig(level=logging.INFO)

# ===================== FUNÇÃO DE ANÁLISE =====================
def analisar_dados(multiplicadores):
    if not multiplicadores:
        return "Não há dados suficientes para análise."

    media = sum(multiplicadores) / len(multiplicadores)
    abaixo_2 = len([x for x in multiplicadores if x < 2]) / len(multiplicadores) * 100
    acima_5 = len([x for x in multiplicadores if x > 5]) / len(multiplicadores) * 100

    previsao = "Neutra"
    if abaixo_2 > 60:
        previsao = "Probabilidade maior de 2x a 4x"
    elif acima_5 > 20:
        previsao = "Possível sequência de multiplicadores baixos"

    return f"""
📊 Análise Estatística

Média: {media:.2f}x
Abaixo de 2x: {abaixo_2:.1f}%
Acima de 5x: {acima_5:.1f}%

📈 Tendência: {previsao}
⚠️ Apenas análise probabilística
"""

# ===================== HANDLERS =====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Envie um print com os resultados.")

async def analisar_imagem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("Envie uma imagem válida.")
        return

    photo = await update.message.photo[-1].get_file()
    await photo.download("imagem.png")

    img = cv2.imread("imagem.png")
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)[1]

    texto = pytesseract.image_to_string(gray)
    numeros = re.findall(r'\d+(?:\.\d+)?', texto)
    multiplicadores = [float(n) for n in numeros]

    if len(multiplicadores) < 5:
        await update.message.reply_text("Não consegui identificar números suficientes.")
        return

    resposta = analisar_dados(multiplicadores)
    await update.message.reply_text(resposta)

# ===================== INICIALIZAÇÃO DO BOT =====================
app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.PHOTO, analisar_imagem))

# ===================== FLASK PARA WEBHOOK =====================
app_web = Flask(__name__)

@app_web.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), app.bot)
    asyncio.run(app.process_update(update))
    return "ok"

@app_web.route("/")
def home():
    return "Bot está online!"

# ===================== RUN =====================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app_web.run(host="0.0.0.0", port=port)
