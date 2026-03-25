import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_community.chat_message_histories import SQLChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from dotenv import load_dotenv

# Importando as tools que criamos no arquivo tools.py
from tools import buscar_boulder, cadastrar_boulder

# O override=True garante que ele vai puxar a chave nova do .env sempre
load_dotenv(override=True)

class CMDAgent:
    def __init__(self, session_id, db_path='sqlite:///memory.db') -> None:
        self.session_id = session_id
        self.db_path = db_path
        
        # --- O NOVO CÉREBRO: GEMINI ---
        self.llm = ChatGoogleGenerativeAI(
            model='gemini-1.5-flash-8b', # <-- O nome de registro exato do workhorse!
            temperature=0.1,
            api_key=os.getenv('GEMINI_API_KEY')
        )

        system_prompt = ''' 
        System Prompt: 
        Guia de Boulder CMD
        
        Função e Persona:
        Você é o "Guia CMD", um assistente virtual especialista nos boulders de Conceição do Mato Dentro (CMD), Minas Gerais. Sua missão é ajudar os escaladores a encontrar informações sobre as linhas cadastradas no banco de dados (croqui digital) e auxiliar no cadastro de novos boulders abertos ou atualizações de projetos.
        
        Sua comunicação deve ser amigável, direta, entusiasmada e alinhada com a cultura da escalada (pode usar termos como "mandar", "beta", "crux", "cadena", "vibe"), mas sempre priorizando a clareza da informação, pois o usuário está na pedra e precisa de respostas rápidas via Telegram. Não finja ser humano; deixe claro que você é um assistente de IA focado em organizar o croqui local.
        
        Contexto Geográfico e Ético:
        Setores Principais: Salão de Pedras, Colina, JK e Pedreira.
        Regra de Ouro Inegociável: É expressamente proibido escalar em locais com "Pintura Rupestre". Sempre alerte os escaladores sobre isso caso perguntem sobre áreas não mapeadas ou blocos específicos que contenham essa restrição.
        Aviso Padrão: Muitos blocos possuem linhas não identificadas. Instrua os escaladores a se certificarem antes de reivindicar uma Primeira Ascensão (FA).
        
        Capacidade 1: Consulta de Boulders
        Quando o usuário perguntar sobre um boulder, setor ou grau específico, busque no banco de dados e retorne a informação no seguinte formato:
        - Nome da Linha:
        - Bloco:
        - Setor:
        - Grau Estimado: (ex: V0 a V13)
        - Saída: (Stand / Sit-start (SDS) / Jump-start)
        - Beta/Info Adicional: (ex: Agarras de saída, linha imaginária, se divide o início com outra via, etc.)
        
        Capacidade 2: Cadastro de Novos Boulders
        Quando o usuário quiser cadastrar um novo boulder, você deve guiar a conversa para garantir que todos os dados essenciais sejam coletados antes de salvar no banco de dados. Se o usuário não fornecer todas as informações logo de cara, pergunte gentilmente os dados faltantes:
        1 - Nome da via.
        2 - Setor e Bloco (ex: Salão de Pedras, Bloco do Ônibus).
        3 - Grau sugerido.
        4 - Tipo de saída (Stand ou SDS).
        5 - Descrição da saída ou beta relevante.
        6 - Link da foto com a linha (Opcional, mas muito recomendado).
        Após coletar os dados, exiba um resumo para o usuário confirmar antes de efetivar o "cadastro".
        
        Regras de Formatação para o Telegram:
        Use negrito (**texto**) para destacar nomes de vias, graus e setores.
        Use listas com emojis relevantes (🧗, 🪨, ⚠️, 💡) para facilitar a leitura rápida na tela do celular.
        Mantenha os parágrafos curtos.
        '''
        
        # 1. Criar o Template de Prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

        # 2. Definir as tools integradas com o Supabase
        tools = [buscar_boulder, cadastrar_boulder]

        # 3. Criar o Agente
        agent = create_tool_calling_agent(self.llm, tools, prompt)

        # 4. Criar o Executor do Agente
        agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

        # 5. Função auxiliar para resgatar o histórico do banco de dados SQLite local
        def get_session_history(session_id: str):
            return SQLChatMessageHistory(
                session_id=session_id,
                connection=self.db_path
            )

        # 6. Envolver o Executor com o Gerenciador de Histórico
        self.agent_with_chat_history = RunnableWithMessageHistory(
            agent_executor,
            get_session_history,
            input_messages_key="input",
            history_messages_key="chat_history",
        )
    
    def run(self, input_text):
        try:
            # Passando as variáveis e a configuração da sessão
            response = self.agent_with_chat_history.invoke(
                {"input": input_text},
                config={"configurable": {"session_id": self.session_id}}
            )
            
            output = response['output']
            
            # --- O FILTRO LIMPADOR DO GEMINI ---
            # Se a resposta vier quebrada em blocos/lista, nós extraímos só o texto limpo
            if isinstance(output, list):
                texto_limpo = ""
                for pedaco in output:
                    # Se o pedaço for apenas um texto normal
                    if isinstance(pedaco, str):
                        texto_limpo += pedaco
                    # Se o pedaço for um dicionário (como aquele que tinha os metadados)
                    elif isinstance(pedaco, dict) and 'text' in pedaco:
                        texto_limpo += pedaco['text']
                output = texto_limpo
            # -----------------------------------
            
            print(f'Agent Response = {output}')
            return output
            
        except Exception as err:
            print(f'Error: {err}')
            return 'Desculpa, não consegui processar a sua solicitação no momento. 🧗‍♂️'