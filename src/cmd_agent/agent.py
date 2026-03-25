import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# Importe a lista de ferramentas do seu arquivo tools.py
# Substitua 'ferramentas' pelo nome correto da sua variável, caso seja diferente
from tools import ferramentas 

class AgenteCMD:
    def __init__(self):
        # 1. Configuração do Modelo
        self.llm = ChatGoogleGenerativeAI(
            model='gemini-flash-latest',
            temperature=0.1,
            api_key=os.getenv('GEMINI_API_KEY')
        )

        # 2. Instruções do Sistema (Prompt)
        instrucoes_sistema = """
        Você é o assistente virtual do Guia de Boulders.
        Sua função é fornecer informações e cadastrar novas vias no banco de dados.

        ### REGRAS OBRIGATÓRIAS PARA CADASTRO DE NOVO BOULDER:
        Para evitar loops infinitos, execute o cadastro seguindo estritamente esta ordem:

        PASSO 1: Solicite ao usuário os dados em texto (nome do boulder, grau, setor e descrição).
        PASSO 2: Ao receber os dados do Passo 1, peça para o usuário enviar a foto da linha no chat.
        PASSO 3: PARE E AGUARDE O ENVIO DA FOTO. Não acione a ferramenta de banco de dados para salvar ainda.
        PASSO 4: O sistema backend interceptará a imagem enviada pelo usuário e enviará para você uma mensagem interna contendo a URL pública da foto.
        PASSO 5: Imediatamente após receber essa URL interna do sistema, acione a ferramenta de salvar no banco de dados utilizando todos os dados coletados e o link da foto. Em seguida, confirme ao usuário que o boulder foi salvo com sucesso.
        """

        # 3. Montagem do Template
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", instrucoes_sistema),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

        # 4. Criação do Agente e Executor
        self.agent = create_tool_calling_agent(self.llm, ferramentas, self.prompt)
        
        # verbose=True permite ver o raciocínio do bot nos logs do Render
        self.agent_executor = AgentExecutor(
            agent=self.agent, 
            tools=ferramentas, 
            verbose=True, 
            handle_parsing_errors=True
        )

    def invocar(self, mensagem_usuario, historico_chat):
        """
        Envia a mensagem e o histórico para o modelo e retorna a resposta em texto.
        """
        try:
            resposta = self.agent_executor.invoke({
                "input": mensagem_usuario,
                "chat_history": historico_chat
            })
            return resposta["output"]
        except Exception as e:
            return f"Desculpa, ocorreu um erro interno ao processar sua solicitação: {e}"