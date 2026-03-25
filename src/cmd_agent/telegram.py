import os
import asyncio
import logging
from dotenv import load_dotenv
from pyrogram import Client, filters
from pyrogram.handlers import MessageHandler
from pyrogram.types import Message
from pyrogram.enums import ChatAction
from agent import CMDAgent

from storage import upload_foto_supabase 

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

        # NOVO: Dicionário para manter a memória do agente de cada usuário viva
        self.sessoes = {} 

        self.app.add_handler(MessageHandler(self.start, filters.command("start")))
        
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
        
        user_input = message.text or message.caption or ""

        await client.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

        foto_url = None
        if message.photo:
            try:
                self.logger.info(f"A descarregar fotografia do utilizador {user_id}...")
                
                file_path = await message.download()
                foto_url = upload_foto_supabase(file_path, user_id)
                
                if os.path.exists(file_path):
                    os.remove(file_path)
                
                if foto_url:
                    self.logger.info(f"Fotografia guardada com sucesso: {foto_url}")
                else:
                    raise Exception("A função de storage devolveu um link vazio.")
                
            except Exception as e:
                self.logger.error(f"Erro ao processar imagem: {e}")
                await message.reply_text("Ups! Tive um problema a guardar a fotografia da via. Podemos continuar, mas a linha vai ficar sem foto por agora.")

        if foto_url:
            user_input += f"\n\n[Nota do Sistema: O utilizador enviou uma fotografia. O link seguro gerado para a foto é: {foto_url}]"

        if not user_input.strip():
            user_input = "Estou a enviar apenas esta fotografia."

        # CORREÇÃO: Verifica se o usuário já tem um agente com memória. Se não, cria um.
        if user_id not in self.sessoes:
            self.sessoes[user_id] = CMDAgent(session_id=str(user_id))
        
        agente_atual = self.sessoes[user_id]

        try:
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(
                None,
                agente_atual.run,
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