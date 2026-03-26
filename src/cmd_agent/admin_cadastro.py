import os
from dotenv import load_dotenv
from tools import cadastrar_boulder

# Carrega as chaves do seu arquivo .env local
load_dotenv(override=True)

def painel_admin():
    print("🧗‍♂️ --- Painel Admin: Cadastro Manual de Boulders CMD --- 🧗‍♂️")
    print("Digite 'sair' no nome do boulder a qualquer momento para encerrar o programa.\n")

    while True:
        nome = input("Nome do boulder: ")
        if nome.lower() == 'sair':
            print("Saindo do painel... Boas escaladas!")
            break
        bloco = input("Nome do bloco: ")
        setor = input("Setor (ex: Salão de Pedras, Colina, Rupestre, JK, Pedreira): ")
        grau = input("Grau (ex: V3, V10): ")
        saida = input("Saída (ex: SDS, Stand, Jump): ")
        beta = input("Descrição/Beta (opcional, aperte Enter para pular): ")
        foto_url = input("Link público da foto (opcional, aperte Enter para pular): ")

        print("\nProcessando e gerando inteligência semântica com o Google...")
        
        try:
            # Como cadastrar_boulder é uma ferramenta do LangChain (@tool), usamos o .invoke()
            resultado = cadastrar_boulder.invoke({
                "nome": nome,
                "bloco": bloco,
                "setor": setor,
                "grau": grau,
                "saida": saida,
                "beta": beta,
                "foto_url": foto_url
            })
            
            print(f"\n✅ {resultado}\n")
            print("-" * 60 + "\n")
            
        except Exception as e:
            print(f"\n❌ Erro ao tentar cadastrar: {e}\n")
            print("-" * 60 + "\n")

if __name__ == "__main__":
    painel_admin()