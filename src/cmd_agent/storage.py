import os
from tools import supabase # Reaproveita a conexão que já existe no seu tools.py

def upload_foto_supabase(file_path, user_id):
    """
    Recebe o caminho da imagem e o ID do utilizador.
    Faz o upload para o bucket 'boulders' e devolve a URL pública.
    """
    try:
        file_name = os.path.basename(file_path)
        supabase_path = f"fotos/{user_id}_{file_name}"
        
        with open(file_path, "rb") as f:
            supabase.storage.from_("boulders").upload(
                path=supabase_path,
                file=f,
                file_options={"content-type": "image/jpeg"}
            )
            
        link_publico = supabase.storage.from_("boulders").get_public_url(supabase_path)
        return link_publico
        
    except Exception as e:
        print(f"Erro interno no upload do Supabase: {e}")
        return None