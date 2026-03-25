import os
from supabase import create_client, Client
from langchain_core.tools import tool
from dotenv import load_dotenv

# NOVO IMPORT: O criador de vetores do Gemini
from langchain_google_genai import GoogleGenerativeAIEmbeddings

load_dotenv(override=True)

url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(url, key)

# Inicializando a "máquina" que transforma texto em matemática (vetores)
gerador_vetores = GoogleGenerativeAIEmbeddings(
    model="models/gemini-embedding-001", # <-- Atualizado para o novo modelo oficial
    google_api_key=os.getenv("GEMINI_API_KEY") 
)

@tool
def buscar_boulder(termo_busca: str) -> str:
    """
    Busca informações sobre um boulder, setor ou grau usando Busca Semântica Avançada (RAG).
    """
    try:
        # 1. Transforma o que o usuário digitou em um vetor matemático
        vetor_busca = gerador_vetores.embed_query(termo_busca)
        
        # 2. Chama a função inteligente do Supabase em vez da busca burra de texto
        response = supabase.rpc(
            'match_boulders', 
            {
                'query_embedding': vetor_busca,
                'match_threshold': 0.3, # A similaridade mínima (30%). Ajuste se precisar ser mais rigoroso!
                'match_count': 3        # Traz apenas os 3 boulders mais parecidos para não encher a tela
            }
        ).execute()
        
        data = response.data
        
        if not data:
            return f"Não encontrei nenhuma via parecida com '{termo_busca}'. O banco de dados pode estar vazio ou a descrição foi muito fora do padrão."
            
        resultados = []
        for b in data:
            foto = b.get('foto_url')
            link_foto = f"[Ver foto da linha]({foto})" if foto else "Sem foto cadastrada"
            
            # Pegando a porcentagem de "Match" para mostrar para o usuário
            match_porcento = round(b.get('similarity', 0) * 100)
            
            resultados.append(
                f"🎯 **Match: {match_porcento}%**\n"
                f"- Nome: {b.get('nome_boulder')}\n"
                f"  Bloco: {b.get('nome_bloco') or 'Não informado'}\n"
                f"  Setor: {b.get('setor')}\n"
                f"  Grau: {b.get('grau')}\n"
                f"  Saída: {b.get('saida')}\n"
                f"  Beta/Info: {b.get('beta')}\n"
                f"  Foto: {link_foto}\n"
            )
        
        return f"Encontrei as vias que mais combinam com o que você pediu:\n\n" + "\n\n".join(resultados)
        
    except Exception as e:
        return f"Erro ao acessar o banco de dados semântico: {str(e)}"

@tool
def cadastrar_boulder(nome: str, setor: str, grau: str, saida: str, beta: str = "", bloco: str = "", foto_url: str = "") -> str:
    """
    Salva um novo boulder no banco de dados já com a inteligência semântica.
    ATENÇÃO: Só use esta ferramenta APÓS ter coletado os dados com o usuário.
    """
    try:
        # 1. Juntamos tudo que importa sobre a via em um texto contínuo
        texto_para_vetor = f"Via chamada {nome}, localizada no bloco {bloco}, setor {setor}. O grau é {grau} e a saída é {saida}. Informações adicionais e beta: {beta}."
        
        # 2. Transformamos a alma da via em um vetor de 768 números
        vetor_da_via = gerador_vetores.embed_query(texto_para_vetor)

        # 3. Empacotamos tudo para enviar para o Supabase
        novo_boulder = {
            "nome_boulder": nome,
            "nome_bloco": bloco,
            "setor": setor,
            "grau": grau,
            "saida": saida, 
            "beta": beta,
            "foto_url": foto_url,
            "embedding": vetor_da_via  # <-- O grande segredo adicionado aqui!
        }
        
        response = supabase.table('boulders').insert(novo_boulder).execute()
        
        if response.data:
            return f"Sucesso! O boulder '{nome}' foi cadastrado com inteligência semântica no croqui digital."
        else:
            return "Ocorreu um erro desconhecido ao tentar salvar no banco."
            
    except Exception as e:
        return f"Erro ao tentar cadastrar no banco de dados: {str(e)}"

# Empacotando as ferramentas para o agente conseguir importar
ferramentas = [buscar_boulder, cadastrar_boulder]