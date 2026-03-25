import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# IMPORTANTE: Importando as classes de memória do LangChain
from langchain_core.messages import HumanMessage, AIMessage

from tools import ferramentas 

class CMDAgent:
    def __init__(self, session_id=None):
        self.session_id = session_id
        
        # NOVO: Inicia a memória vazia apenas uma vez quando o usuário entra
        self.chat_history = []
        
        self.llm = ChatGoogleGenerativeAI(
            model='gemini-flash-latest',
            temperature=0.1,
            api_key=os.getenv('GEMINI_API_KEY')
        )

        # CORREÇÃO: Prompt atualizado exigindo a confirmação do usuário antes de salvar
        instrucoes_sistema = """
        Você é o assistente virtual do Guia de Boulders.
        Sua função é fornecer informações e cadastrar novas vias no banco de dados.

        ### REGRAS OBRIGATÓRIAS PARA CADASTRO DE NOVO BOULDER:
        Para evitar loops infinitos, execute o cadastro seguindo estritamente esta ordem:

        PASSO 1: Solicite ao usuário os dados em texto (nome do boulder, grau, setor e descrição).
        PASSO 2: Ao receber os dados do Passo 1, peça para o usuário enviar a foto da linha no chat.
        PASSO 3: PARE E AGUARDE O ENVIO DA FOTO.
        PASSO 4: O sistema backend enviará para você uma mensagem interna contendo a URL pública da foto.
        PASSO 5: Ao receber a URL, NÃO acione a ferramenta de salvar ainda. Mostre ao usuário um resumo com todos os dados (Nome, Grau, Setor, Descrição e o link da Foto) e pergunte: "Posso confirmar e salvar no banco de dados?".
        PASSO 6: Somente após o usuário responder confirmando (ex: "sim", "pode", "salvar"), acione a ferramenta de salvar no banco de dados. Em seguida, avise que foi salvo com sucesso.
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
                "chat_history": self.chat_history # CORREÇÃO: Agora passa o histórico real
            })
            
            output = resposta["output"]
            
            # Garante a extração apenas do texto limpo
            if isinstance(output, list):
                text_parts = [item['text'] for item in output if isinstance(item, dict) and 'text' in item]
                texto_final = "\n".join(text_parts) if text_parts else str(output)
            else:
                texto_final = str(output)

            # NOVO: Salva a interação na memória para a próxima mensagem
            self.chat_history.append(HumanMessage(content=mensagem_usuario))
            self.chat_history.append(AIMessage(content=texto_final))
            
            return texto_final
            
        except Exception as e:
            return f"Desculpa, ocorreu um erro interno ao processar sua solicitação: {e}"