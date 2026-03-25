import os
from supabase import create_client, Client
from langchain_core.tools import tool
from dotenv import load_dotenv

load_dotenv()

url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(url, key)

@tool
def buscar_boulder(termo_busca: str) -> str:
    """
    Busca informações sobre um boulder, setor ou grau no banco de dados.
    """
    try:
        # Busca nas colunas exatas do seu banco
        response = supabase.table('boulders').select('*').or_(
            f"nome_boulder.ilike.%{termo_busca}%,nome_bloco.ilike.%{termo_busca}%,setor.ilike.%{termo_busca}%,grau.ilike.%{termo_busca}%"
        ).execute()
        
        data = response.data
        
        if not data:
            return f"Nenhum boulder encontrado para '{termo_busca}'. Verifique se o nome está correto ou pergunte se o usuário quer cadastrar!"
            
        resultados = []
        for b in data:
            foto = b.get('foto_url')
            link_foto = f"[Ver foto da linha]({foto})" if foto else "Sem foto cadastrada"
            
            # Resgatando os dados puxando pelas colunas corretas
            resultados.append(
                f"- Nome: {b.get('nome_boulder')}\n"
                f"  Bloco: {b.get('nome_bloco') or 'Não informado'}\n"
                f"  Setor: {b.get('setor')}\n"
                f"  Grau: {b.get('grau')}\n"
                f"  Saída: {b.get('saida')}\n"
                f"  Beta/Info: {b.get('beta')}\n"
                f"  Foto: {link_foto}\n"
            )
        
        return f"Encontrei os seguintes boulders:\n\n" + "\n\n".join(resultados)
        
    except Exception as e:
        return f"Erro ao acessar o banco de dados: {str(e)}"

@tool
def cadastrar_boulder(nome: str, setor: str, grau: str, saida: str, beta: str = "", bloco: str = "", foto_url: str = "") -> str:
    """
    Salva um novo boulder no banco de dados. 
    ATENÇÃO: Só use esta ferramenta APÓS ter coletado os dados com o usuário.
    """
    try:
        # Mapeamento: pegamos os dados que o bot coletou e colocamos nas colunas exatas do seu Supabase
        novo_boulder = {
            "nome_boulder": nome,
            "nome_bloco": bloco,
            "setor": setor,
            "grau": grau,
            "saida": saida, 
            "beta": beta,
            "foto_url": foto_url
        }
        
        # Inserindo na tabela correta
        response = supabase.table('boulders').insert(novo_boulder).execute()
        
        if response.data:
            return f"Sucesso! O boulder '{nome}' foi cadastrado no croqui digital."
        else:
            return "Ocorreu um erro desconhecido ao tentar salvar no banco."
            
    except Exception as e:
        return f"Erro ao tentar cadastrar no banco de dados: {str(e)}"