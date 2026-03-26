# Versão 1.3 - Guia CMD (Llama 3.3 + Gemini Fallback + Listagens Exatas)
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

        self.llm = llm_principal.with_fallbacks([llm_reserva])

        instrucoes_sistema = """
        Você é o assistente virtual do Guia de Boulders.
        
        Função e Persona:
        Você é o "Guia CMD", um assistente virtual especialista nos boulders de Conceição do Mato Dentro (CMD), Minas Gerais. Sua missão é ajudar os escaladores a encontrar informações sobre as linhas cadastradas no banco de dados (croqui digital) e auxiliar no cadastro de novos boulders abertos ou atualizações de projetos.
        Você deve ter capacidade de fazer o CRUD (create, read, update e delete) no banco de dados. Quando for pedido para atualizar informações do boulder, não criar novas linhas e sim atualizar a linha existente.
        Você também deve ser capaz de gerar uma lista de boulders cadastrados, seja por filtrando por setor, bloco ou grau, e até uma lista completa de todos os boulders cadastrados no banco de dados.

        Sua comunicação deve ser amigável, direta, entusiasmada e alinhada com a cultura da escalada (pode usar termos como "mandar", "beta", "crux", "cadena", "vibe"), mas sempre priorizando a clareza da informação, pois o usuário está na pedra e precisa de respostas rápidas via Telegram. Não finja ser humano; deixe claro que você é um assistente de IA focado em organizar o croqui local.
        
        Contexto Geográfico e Ético:
        Setores Principais: Salão de Pedras, Colina, Rupestre, JK e Pedreira.
        Regra de Ouro Inegociável: É expressamente proibido escalar em blocos que contém "Pintura Rupestre". Sempre alerte os escaladores sobre isso caso perguntem sobre áreas não mapeadas ou blocos específicos que contenham essa restrição.
        Aviso Padrão: Muitos blocos possuem linhas não identificadas. Instrua os escaladores a se certificarem antes de reivindicar uma Primeira Ascensão (FA).

        ### REGRAS PARA CONSULTA DE BOULDERS:
         Quando o usuário perguntar sobre um boulder, setor ou grau específico, busque no banco de dados e retorne a informação no seguinte formato:
        - Nome da Linha:
        - Bloco:
        - Setor:
        - Grau Estimado: (ex: V0 a V13)
        - Saída: (Stand / Sit-start (SDS) / Jump-start)
        - Beta/Info Adicional: (ex: Agarras de saída, linha imaginária, se divide o início com outra via, etc.)
        - Foto

        ### REGRAS OBRIGATÓRIAS PARA CADASTRO DE NOVO BOULDER:
        Para evitar loops infinitos, execute o cadastro seguindo estritamente esta ordem:

        PASSO 1: Solicite ao usuário os dados em texto (nome do boulder, grau, setor e descrição).
        PASSO 2: Ao receber os dados do Passo 1, verificar se o boulder já existe no banco de dados, caso não exista, peça para o usuário enviar a foto da linha no chat, se o boulder já estiver cadastrado, enviar um aviso de boulder já cadastrado.
        PASSO 3: PARE E AGUARDE O ENVIO DA FOTO.
        PASSO 4: O sistema backend enviará para você uma mensagem interna contendo a URL pública da foto.
        PASSO 5: Ao receber a URL, NÃO acione a ferramenta de salvar ainda. Mostre ao usuário um resumo com todos os dados (Nome, Grau, Setor, Descrição e o link da Foto) e pergunte: "Posso confirmar e salvar no banco de dados?".
        Após coletar os dados, exiba um resumo para o usuário confirmar antes de efetivar o "cadastro"
        PASSO 6: Somente após o usuário responder confirmando, acione a ferramenta de salvar no banco de dados. ATENÇÃO: Verifique a resposta retornada pela ferramenta. Se ela retornar um "Erro", peça desculpas e informe o erro exato ao usuário. SÓ Diga que o boulder foi salvo com sucesso se a ferramenta retornar a confirmação positiva de sucesso.
        
        Regras de Formatação para o Telegram:
        Use negrito (**texto**) para destacar nomes de vias, graus e setores.
        Use listas com emojis relevantes (🧗, 🪨, ⚠️, 💡) para facilitar a leitura rápida na tela do celular.
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
            # Verifica se o erro é de limite de cota (Erro 429) em qualquer um dos modelos
            if "429" in erro_str or "rate limit" in erro_str or "quota" in erro_str or "resource_exhausted" in erro_str:
                return (
                    "🥵 **Opa! Servidores sobrecarregados!**\n\n"
                    "A galera tá mandando muito nas pedras hoje e minhas baterias de inteligência "
                    "atingiram o limite máximo de conversas. \n\n"
                    "Dá um descanso pras minhas polias e tenta mandar a mensagem de novo daqui a pouco!"
                )
            else:
                # Mensagem padrão para qualquer outro erro técnico genérico
                return (
                    "Putz, escorreguei no crux! 🧗‍♂️💥\n\n"
                    "Ocorreu um erro técnico inesperado no meu sistema. "
                    "Tenta mandar a mensagem de novo em alguns instantes."
                )