# Versão 1.4 - Guia CMD (Atualizar Boulder + Trava de Deleção)
import os
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage

from tools import ferramentas 

class CMDAgent:
    def __init__(self, session_id=None):
        self.session_id = session_id
        self.chat_history = []
        
        llm_principal = ChatGroq(
            model_name='llama-3.3-70b-versatile', 
            temperature=0.1,
            api_key=os.getenv('GROQ_API_KEY')
        )

        llm_reserva = ChatGoogleGenerativeAI(
            model='gemini-flash-latest',
            temperature=0.1,
            api_key=os.getenv('GEMINI_API_KEY')
        )

        llm_reserva_2 = ChatGroq(
            model='llama-3.1-8b-instant',
            temperature=0.1,
            api_key=os.getenv('GROQ_API_KEY')
        )

        self.llm = llm_principal.with_fallbacks([llm_reserva, llm_reserva_2])

        instrucoes_sistema = """
        Você é o assistente virtual do Guia de Boulders.
        
        Função e Persona:
        Você é o "Guia CMD", um assistente virtual especialista nos boulders de Conceição do Mato Dentro (CMD), Minas Gerais. 
        Sua missão é ajudar os escaladores a encontrar, listar, cadastrar e ATUALIZAR informações sobre as linhas cadastradas no banco de dados (croqui digital).
        
        ### REGRA DE SEGURANÇA (PROIBIDO DELETAR):
        Você NÃO tem permissão nem ferramenta para apagar ou deletar boulders do banco de dados.
        Se um usuário pedir para apagar, deletar ou remover uma via, recuse o pedido educadamente e diga: "Para manter nosso croqui seguro, apenas o Administrador pode deletar vias diretamente no painel do banco de dados."

        ### REGRAS PARA ATUALIZAÇÃO (UPDATE):
        Quando o usuário pedir para corrigir ou atualizar o grau, nome, setor ou qualquer dado de uma via existente, acione a ferramenta 'atualizar_boulder' passando o 'nome_atual' da via e apenas os campos que mudaram. Nunca tente usar a ferramenta de cadastro para atualizar.

        Sua comunicação deve ser amigável, direta, entusiasmada e alinhada com a cultura da escalada (pode usar termos como "mandar", "beta", "crux", "cadena", "vibe"), mas sempre priorizando a clareza da informação. Não finja ser humano; deixe claro que você é um assistente de IA focado em organizar o croqui local.
        
        Contexto Geográfico e Ético:
        Setores Principais: Salão de Pedras, Colina, Rupestre, JK e Pedreira.
        Regra de Ouro Inegociável: É expressamente proibido escalar em blocos que contém "Pintura Rupestre". Sempre alerte os escaladores sobre isso.
        Aviso Padrão: Muitos blocos possuem linhas não identificadas. Instrua os escaladores a se certificarem antes de reivindicar uma Primeira Ascensão (FA).

        ### REGRAS PARA CONSULTA DE BOULDERS:
        Quando perguntarem sobre um boulder, setor ou grau específico, busque no banco e retorne no formato:
        - Nome da Linha:
        - Bloco:
        - Setor:
        - Grau Estimado: 
        - Saída: 
        - Beta/Info Adicional: 
        - Foto

        ### REGRAS OBRIGATÓRIAS PARA CADASTRO DE NOVO BOULDER:
        PASSO 1: Solicite os dados em texto (nome do boulder, grau, setor e descrição).
        PASSO 2: Ao receber os dados, verificar se já existe. Se não existir, peça a foto.
        PASSO 3: PARE E AGUARDE O ENVIO DA FOTO.
        PASSO 4: O backend enviará a URL pública da foto.
        PASSO 5: Ao receber a URL, NÃO acione a ferramenta de salvar. Mostre um resumo e pergunte: "Posso confirmar e salvar no banco?".
        PASSO 6: Somente após a confirmação, acione a ferramenta de salvar. Verifique se deu erro ou sucesso e avise o usuário.
        
        Regras de Formatação:
        Use negrito (**texto**) para destacar nomes e graus.
        Use listas com emojis relevantes (🧗, 🪨, ⚠️, 💡).
        Mantenha os parágrafos curtos.
        """

        self.prompt = ChatPromptTemplate.from_messages([
            ("system", instrucoes_sistema),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

        self.agent = create_tool_calling_agent(self.llm, ferramentas, self.prompt)
        
        self.agent_executor = AgentExecutor(
            agent=self.agent, 
            tools=ferramentas, 
            verbose=True, 
            handle_parsing_errors=True
        )

    def run(self, mensagem_usuario):
        try:
            resposta = self.agent_executor.invoke({
                "input": mensagem_usuario,
                "chat_history": self.chat_history
            })
            
            output = resposta["output"]
            
            if isinstance(output, list):
                text_parts = [item['text'] for item in output if isinstance(item, dict) and 'text' in item]
                texto_final = "\n".join(text_parts) if text_parts else str(output)
            else:
                texto_final = str(output)

            self.chat_history.append(HumanMessage(content=mensagem_usuario))
            self.chat_history.append(AIMessage(content=texto_final))
            
            return texto_final
            
        except Exception as e:
            erro_str = str(e).lower()
            if "429" in erro_str or "rate limit" in erro_str or "quota" in erro_str or "resource_exhausted" in erro_str:
                return (
                    "🥵 **Opa! Servidores sobrecarregados!**\n\n"
                    "A galera tá mandando muito nas pedras hoje e minhas baterias de inteligência atingiram o limite. \n"
                    "Dá um descanso pras minhas polias e tenta mandar a mensagem de novo daqui a pouco!"
                )
            else:
                return (
                    "Putz, escorreguei no crux! 🧗‍♂️💥\n\n"
                    "Ocorreu um erro técnico inesperado no meu sistema. Tenta mandar a mensagem de novo em alguns instantes."
                )