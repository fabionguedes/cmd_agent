import os
import asyncio
from threading import Thread
from flask import Flask

# Ligamos o motor assíncrono ANTES de carregar o Pyrogram
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

from telegram import TelegramBot

# 1. Criamos um "falso site" para enganar o servidor da nuvem
app = Flask(__name__)

@app.route('/')
def health_check():
    return "O Guia CMD está online na nuvem."

def run_server():
    # O Render vai nos dar uma porta (PORT) dinâmica, precisamos ouvi-la
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

if __name__ == "__main__":
    # 2. Iniciamos o site em uma thread paralela (segundo plano)
    server_thread = Thread(target=run_server)
    server_thread.start()

    # 3. Iniciamos o nosso bot na thread principal
    bot = TelegramBot()
    bot.run()