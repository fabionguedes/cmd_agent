import os
import unicodedata
from supabase import create_client, Client
from langchain_core.tools import tool
from dotenv import load_dotenv

from langchain_google_genai import GoogleGenerativeAIEmbeddings

load_dotenv(override=True)

url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(url, key)

gerador_vetores = GoogleGenerativeAIEmbeddings(
    model="models/gemini-embedding-001",
    google_api_key=os.getenv("GEMINI_API_KEY") 
)

def remover_acentos(texto: str) -> str:
    if not texto:
        return ""
    texto_sem_acento = ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
    return texto_sem_acento.lower().strip()

@tool
def buscar_boulder(termo_busca: str) -> str:
    """Busca informações sobre UM boulder específico usando Busca Semântica Avançada."""
    try:
        vetor_busca = gerador_vetores.embed_query(termo_busca)[:768]
        response = supabase.rpc('match_boulders', {'query_embedding': vetor_busca, 'match_threshold': 0.3, 'match_count': 3}).execute()
        data = response.data
        if not data: return f"Não encontrei nenhuma via parecida com '{termo_busca}'."
            
        resultados = []
        for b in data:
            foto = b.get('foto_url')
            link_foto = f"[Ver foto da linha]({foto})" if foto else "Sem foto cadastrada"
            match_porcento = round(b.get('similarity', 0) * 100)
            resultados.append(
                f"🎯 **Match: {match_porcento}%**\n- Nome: {b.get('nome_boulder')}\n  Bloco: {b.get('nome_bloco') or 'Não informado'}\n  Setor: {b.get('setor')}\n  Grau: {b.get('grau')}\n  Saída: {b.get('saida')}\n  Beta/Info: {b.get('beta')}\n  Foto: {link_foto}\n"
            )
        return f"Encontrei as vias que mais combinam com o que você pediu:\n\n" + "\n\n".join(resultados)
    except Exception as e:
        return f"Erro ao acessar o banco de dados semântico: {str(e)}"

@tool
def listar_boulders(setor: str = "", bloco: str = "", grau: str = "") -> str:
    """Gera listas exatas do banco de dados ignorando acentos."""
    try:
        response = supabase.table('boulders').select('nome_boulder, nome_bloco, setor, grau').execute()
        data = response.data
        if not data: return "O banco de dados está vazio."
        
        if setor:
            setor_norm = remover_acentos(setor)
            data = [b for b in data if b.get('setor') and setor_norm in remover_acentos(b.get('setor'))]
        if bloco:
            bloco_norm = remover_acentos(bloco)
            data = [b for b in data if b.get('nome_bloco') and bloco_norm in remover_acentos(b.get('nome_bloco'))]
        if grau:
            grau_norm = remover_acentos(grau)
            data = [b for b in data if b.get('grau') and grau_norm in remover_acentos(b.get('grau'))]
            
        if not data: return "Nenhum resultado encontrado para esses filtros."
        
        blocos_unicos = {}
        for b in data:
            nome_original = b.get('nome_bloco')
            if nome_original:
                nome_norm = remover_acentos(nome_original)
                if nome_norm not in blocos_unicos:
                    blocos_unicos[nome_norm] = nome_original
        
        blocos_encontrados = sorted(list(blocos_unicos.values()))
        linhas = [f"- **{b.get('nome_boulder')}** ({b.get('grau')}) | Bloco: {b.get('nome_bloco') or '?'}" for b in data]
            
        resultado_texto = f"Encontrei {len(data)} via(s) baseada(s) no seu pedido:\n\n"
        if blocos_encontrados: resultado_texto += f"🪨 **Blocos nesta lista:** {', '.join(blocos_encontrados)}\n\n"
        resultado_texto += "🧗 **Lista de Boulders:**\n" + "\n".join(linhas)
        return resultado_texto
    except Exception as e:
        return f"Erro ao gerar a lista no banco de dados: {str(e)}"

@tool
def cadastrar_boulder(nome: str, setor: str, grau: str, saida: str, beta: str = "", bloco: str = "", foto_url: str = "") -> str:
    """Salva um novo boulder no banco de dados."""
    try:
        checagem = supabase.table('boulders').select('nome_boulder').ilike('nome_boulder', nome).execute()
        if checagem.data: return f"⚠️ ERRO DE DUPLICIDADE: Já existe uma via chamada '{nome}' cadastrada no guia. O cadastro foi cancelado."

        texto_para_vetor = f"Via chamada {nome}, localizada no bloco {bloco}, setor {setor}. O grau é {grau} e a saída é {saida}. Informações adicionais e beta: {beta}."
        vetor_da_via = gerador_vetores.embed_query(texto_para_vetor)[:768]

        novo_boulder = {"nome_boulder": nome, "nome_bloco": bloco, "setor": setor, "grau": grau, "saida": saida, "beta": beta, "foto_url": foto_url, "embedding": vetor_da_via}
        response = supabase.table('boulders').insert(novo_boulder).execute()
        
        if response.data: return f"Sucesso! O boulder '{nome}' foi cadastrado no croqui digital."
        else: return "Ocorreu um erro desconhecido ao tentar salvar no banco."
    except Exception as e:
        return f"Erro ao tentar cadastrar no banco de dados: {str(e)}"

@tool
def atualizar_boulder(nome_atual: str, novo_nome: str = "", setor: str = "", grau: str = "", saida: str = "", beta: str = "", bloco: str = "", foto_url: str = "") -> str:
    """
    Atualiza as informações de um boulder que JÁ EXISTE no banco de dados.
    Forneça o 'nome_atual' exato da via e preencha apenas os campos que deseja alterar.
    """
    try:
        # 1. Busca a via existente
        busca = supabase.table('boulders').select('*').ilike('nome_boulder', nome_atual).execute()
        if not busca.data:
            return f"⚠️ Erro: Não encontrei nenhuma via chamada '{nome_atual}' para atualizar."
            
        via_existente = busca.data[0]
        via_id = via_existente['id']
        
        # 2. Substitui apenas os campos que foram preenchidos pelo usuário
        nome_final = novo_nome if novo_nome else via_existente.get('nome_boulder', '')
        setor_final = setor if setor else via_existente.get('setor', '')
        grau_final = grau if grau else via_existente.get('grau', '')
        saida_final = saida if saida else via_existente.get('saida', '')
        beta_final = beta if beta else via_existente.get('beta', '')
        bloco_final = bloco if bloco else via_existente.get('nome_bloco', '')
        foto_final = foto_url if foto_url else via_existente.get('foto_url', '')
        
        # 3. Recria o vetor de busca (inteligência) para refletir a atualização
        texto_para_vetor = f"Via chamada {nome_final}, localizada no bloco {bloco_final}, setor {setor_final}. O grau é {grau_final} e a saída é {saida_final}. Informações adicionais e beta: {beta_final}."
        vetor_da_via = gerador_vetores.embed_query(texto_para_vetor)[:768]
        
        # 4. Salva a atualização no Supabase
        dados_atualizados = {
            "nome_boulder": nome_final, "nome_bloco": bloco_final, "setor": setor_final,
            "grau": grau_final, "saida": saida_final, "beta": beta_final,
            "foto_url": foto_final, "embedding": vetor_da_via 
        }
        response = supabase.table('boulders').update(dados_atualizados).eq('id', via_id).execute()
        
        if response.data: return f"✅ Sucesso! O boulder '{nome_atual}' foi atualizado perfeitamente no croqui."
        else: return "Ocorreu um erro desconhecido ao tentar atualizar no banco."
            
    except Exception as e:
        return f"Erro ao tentar atualizar no banco de dados: {str(e)}"

# A quarta ferramenta foi adicionada à lista!
ferramentas = [buscar_boulder, listar_boulders, cadastrar_boulder, atualizar_boulder]