import os
import asyncio
import logging
from dotenv import load_dotenv
from pyrogram import Client, filters
from pyrogram.handlers import MessageHandler
from pyrogram.types import Message
from pyrogram.enums import ChatAction
from agent import CMDAgent

# Importamos o cliente do Supabase que já criámos no tools.py
from tools import supabase 

load_dotenv()

class TelegramBot:
    def __init__(self) -> None:
        logging.basicConfig(
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            level=logging.INFO
        )
        self.logger = logging.getLogger(__name__)

        self.app = Client(
            "cmd_agent",
            api_id=os.getenv('TELEGRAM_API_ID'),
            api_hash=os.getenv('TELEGRAM_API_HASH'),
            bot_token=os.getenv('TELEGRAM_TOKEN'),
        )

        self.app.add_handler(MessageHandler(self.start, filters.command("start")))
        
        # ATUALIZAÇÃO: O filtro agora aceita mensagens de texto OU fotografias
        self.app.add_handler(MessageHandler(
            self.handle_message, 
            (filters.text | filters.photo) & ~filters.command("start")
        ))

    async def start(self, client: Client, message: Message):
        await message.reply_text(
            'Fala Bactéria, estás a querer escalar o quê em CMD? 🧗‍♂️'
        )
        self.logger.info(f'Utilizador {message.from_user.id} iniciou uma conversa.')

    async def handle_message(self, client: Client, message: Message):
        user_id = message.from_user.id
        
        # O texto pode vir da mensagem normal ou da legenda (caption) de uma fotografia
        user_input = message.text or message.caption or ""

        await client.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

        # --- LÓGICA DE INTERCEÇÃO DA FOTOGRAFIA ---
        foto_url = None
        if message.photo:
            try:
                self.logger.info(f"A descarregar fotografia do utilizador {user_id}...")
                
                # 1. Faz o download da imagem do Telegram para uma pasta local temporária
                file_path = await message.download()
                file_name = os.path.basename(file_path)
                
                # 2. Caminho único no Supabase (ex: fotos/123456_imagem.jpg)
                supabase_path = f"fotos/{user_id}_{file_name}"
                
                # 3. Faz o upload para o bucket 'boulders' no Supabase
                with open(file_path, "rb") as f:
                    supabase.storage.from_("boulders").upload(
                        path=supabase_path,
                        file=f,
                        file_options={"content-type": "image/jpeg"}
                    )
                
                # 4. Obtém o link público da imagem gerada
                foto_url = supabase.storage.from_("boulders").get_public_url(supabase_path)
                
                # 5. Apaga o ficheiro local para não encher o disco do servidor
                os.remove(file_path)
                
                self.logger.info(f"Fotografia guardada com sucesso: {foto_url}")
                
            except Exception as e:
                self.logger.error(f"Erro ao processar imagem: {e}")
                await message.reply_text("Ups! Tive um problema a guardar a fotografia da via. Podemos continuar, mas a linha vai ficar sem foto por agora.")

        # --- PREPARAÇÃO DA MENSAGEM PARA O AGENTE ---
        # Se detetámos uma fotografia, injetamos o link silenciosamente no texto que o Agente vai ler
        if foto_url:
            user_input += f"\n\n[Nota do Sistema: O utilizador enviou uma fotografia. O link seguro gerado para a foto é: {foto_url}]"

        # Se o utilizador mandar SÓ a foto sem texto, o Agente vai receber apenas a "[Nota do Sistema...]" e vai saber lidar com isso
        if not user_input.strip():
            user_input = "Estou a enviar apenas esta fotografia."

        self.agent = CMDAgent(session_id=str(user_id))

        try:
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(
                None,
                self.agent.run,
                user_input
            )
        except Exception as err:
            self.logger.error(f"Erro ao processar a mensagem do utilizador {user_id}: {err}", exc_info=True)
            response = "Desculpa, ocorreu um erro a processar o teu pedido. Por favor, tenta novamente. 🪨"

        await message.reply_text(response)
        self.logger.info(f"Resposta enviada para o utilizador {user_id}.")

    def run(self):
        self.logger.info("Bot do Telegram Iniciado! Pronto para o cadena.")
        self.app.run()