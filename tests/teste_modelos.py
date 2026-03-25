import os
import google.generativeai as genai
from dotenv import load_dotenv

# Carrega a sua chave do arquivo .env
load_dotenv(override=True)

chave = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=chave)

print("🔍 Buscando modelos liberados para a sua chave...\n")

try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"- {m.name}")
except Exception as e:
    print(f"Erro ao buscar: {e}")