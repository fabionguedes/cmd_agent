import os
from supabase import create_client, Client
from langchain_core.tools import tool
from dotenv import load_dotenv

from langchain_google_genai import GoogleGenerativeAIEmbeddings

load_dotenv(override=True)

url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(url, key)

# Inicializando a "máquina" com o modelo mais recente
gerador_vetores = GoogleGenerativeAIEmbeddings(
    model="models/gemini-embedding-001",
    google_api_key=os.getenv("GEMINI_API_KEY") 
)

@tool
def buscar_boulder(termo_busca: str) -> str:
    """
    Busca informações sobre UM boulder específico usando Busca Semântica Avançada.
    Use esta ferramenta quando o usuário procurar por descrições, nomes aproximados ou características de UMA via.
    """
    try:
        vetor_busca = gerador_vetores.embed_query(termo_busca)
        vetor_busca = vetor_busca[:768]
        
        response = supabase.rpc(
            'match_boulders', 
            {
                'query_embedding': vetor_busca,
                'match_threshold': 0.3, 
                'match_count': 3        
            }
        ).execute()
        
        data = response.data
        
        if not data:
            return f"Não encontrei nenhuma via parecida com '{termo_busca}'."
            
        resultados = []
        for b in data:
            foto = b.get('foto_url')
            link_foto = f"[Ver foto da linha]({foto})" if foto else "Sem foto cadastrada"
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
def listar_boulders(setor: str = "", bloco: str = "", grau: str = "") -> str:
    """
    Gera listas exatas do banco de dados. 
    Use APENAS quando o usuário pedir listas ou categorias (ex: "quais os V3", "blocos do setor Colina", "lista de vias do bloco X").
    """
    try:
        query = supabase.table('boulders').select('nome_boulder, nome_bloco, setor, grau')
        
        # Aplica os filtros exatos que a Inteligência Artificial identificar na frase do usuário
        if setor:
            query = query.ilike('setor', f'%{setor}%')
        if bloco:
            query = query.ilike('nome_bloco', f'%{bloco}%')
        if grau:
            query = query.ilike('grau', f'%{grau}%')
            
        response = query.execute()
        data = response.data
        
        if not data:
            return "Nenhum resultado encontrado para esses filtros."
        
        # Extrai uma lista única de blocos encontrados na busca
        blocos_encontrados = sorted(list(set(b.get('nome_bloco') for b in data if b.get('nome_bloco'))))
        
        linhas = []
        for b in data:
            linhas.append(f"- **{b.get('nome_boulder')}** ({b.get('grau')}) | Bloco: {b.get('nome_bloco') or '?'}")
            
        resultado_texto = f"Encontrei {len(data)} via(s) baseada(s) no seu pedido:\n\n"
        
        if blocos_encontrados:
            resultado_texto += f"🪨 **Blocos nesta lista:** {', '.join(blocos_encontrados)}\n\n"
            
        resultado_texto += "🧗 **Lista de Boulders:**\n" + "\n".join(linhas)
        
        return resultado_texto

    except Exception as e:
        return f"Erro ao gerar a lista no banco de dados: {str(e)}"

@tool
def cadastrar_boulder(nome: str, setor: str, grau: str, saida: str, beta: str = "", bloco: str = "", foto_url: str = "") -> str:
    """
    Salva um novo boulder no banco de dados já com a inteligência semântica.
    """
    try:
        texto_para_vetor = f"Via chamada {nome}, localizada no bloco {bloco}, setor {setor}. O grau é {grau} e a saída é {saida}. Informações adicionais e beta: {beta}."
        vetor_da_via = gerador_vetores.embed_query(texto_para_vetor)
        vetor_da_via = vetor_da_via[:768]

        novo_boulder = {
            "nome_boulder": nome,
            "nome_bloco": bloco,
            "setor": setor,
            "grau": grau,
            "saida": saida, 
            "beta": beta,
            "foto_url": foto_url,
            "embedding": vetor_da_via 
        }
        
        response = supabase.table('boulders').insert(novo_boulder).execute()
        
        if response.data:
            return f"Sucesso! O boulder '{nome}' foi cadastrado com inteligência semântica no croqui digital."
        else:
            return "Ocorreu um erro desconhecido ao tentar salvar no banco."
            
    except Exception as e:
        return f"Erro ao tentar cadastrar no banco de dados: {str(e)}"

# CORREÇÃO IMPORTANTE: Agora temos TRÊS ferramentas na lista!
ferramentas = [buscar_boulder, listar_boulders, cadastrar_boulder]