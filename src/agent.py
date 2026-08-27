"""
src/agent.py
============
Agente RashBot — LangGraph + LangChain + Google Gemini.

Arquitetura:
  ┌─────────────────────────────────────────────────────┐
  │                  RashBot Agent                      │
  │                                                     │
  │  HumanMessage ──► [llm_node] ──► ToolMessage       │
  │                        │                            │
  │                   (tool calls?)                     │
  │                        │ YES                        │
  │                   [tools_node] ──► [llm_node] ...   │
  │                        │ NO                         │
  │                     END                             │
  └─────────────────────────────────────────────────────┘

Fluxo com MemorySaver para manter contexto da conversa
entre múltiplas interações (thread_id por sessão).
"""

import os
import sys
import logging
import pathlib
from typing import Annotated, Literal

from dotenv import load_dotenv

from langchain_core.messages import SystemMessage, AIMessage, ToolMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver

from typing_extensions import TypedDict

# Garante imports relativos quando executado de src/
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import tools as rashbot_tools

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── Variáveis de ambiente & Secrets ───────────────────────────────────────────

# Carrega .env da raiz do projeto (dois níveis acima de src/)
_ENV_FILE = pathlib.Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=_ENV_FILE)


def get_config_var(key: str, default: str = "") -> str:
    """
    Obtém uma configuração da variável de ambiente (os.getenv) ou dos
    segredos do Streamlit (st.secrets), se disponível.
    """
    # 1. Tenta variável de ambiente do sistema / .env
    val = os.getenv(key)
    if val:
        return val.strip()

    # 2. Tenta Streamlit secrets (Streamlit Cloud ou .streamlit/secrets.toml)
    try:
        import streamlit as st
        if hasattr(st, "secrets") and key in st.secrets:
            secret_val = st.secrets[key]
            if secret_val:
                return str(secret_val).strip()
    except Exception:
        pass

    return default


GEMINI_API_KEY = get_config_var("GEMINI_API_KEY", "")
# Modelo configurável com fallback seguro para gemini-1.5-flash
GEMINI_MODEL = get_config_var("GEMINI_MODEL", "gemini-1.5-flash")

if not GEMINI_API_KEY:
    raise EnvironmentError(
        "GEMINI_API_KEY não encontrada. Crie o arquivo .env na raiz do projeto "
        "com base no .env.example ou defina nos secrets do Streamlit com sua chave da API do Google."
    )

# ── Prompt de Sistema ─────────────────────────────────────────────────────────

SYSTEM_PROMPT = """Você é o RashBot, assistente técnico e comercial da Rash Rolamentos Industriais.

## SUA MISSÃO
Ajudar compradores industriais, mecânicos e gerentes de manutenção a encontrar
o rolamento certo para cada aplicação, gerar cotações formais e agilizar o
atendimento técnico-comercial.

## REGRAS ABSOLUTAS — NUNCA QUEBRE ESTAS REGRAS

1. **ZERO ALUCINAÇÃO DE CATÁLOGO**
   Você JAMAIS inventa códigos, preços, medidas ou especificações técnicas.
   Para qualquer informação de produto, você OBRIGATORIAMENTE usa as ferramentas
   disponíveis. Se a ferramenta não retornar o produto, você informa que não
   está no catálogo atual.

2. **CONSULTA DETERMINÍSTICA**
   Preços, estoques e dimensões apresentados ao cliente vêm EXCLUSIVAMENTE do
   banco de dados. Nunca estime, arredonde ou suponha valores.

3. **COLETA OBRIGATÓRIA ANTES DE COTAÇÃO**
   Antes de chamar tool_gerar_cotacao, você DEVE coletar:
   - Nome completo do cliente ou razão social da empresa
   - Contato (WhatsApp com DDD ou e-mail corporativo)
   Se o cliente não informar espontaneamente, pergunte educadamente.

4. **VERIFICAÇÃO ANTES DE COTAR**
   Antes de incluir qualquer produto em uma cotação, use
   tool_verificar_estoque_preco para confirmar disponibilidade e preço.

5. **TRANSPARÊNCIA DO FLUXO DE APROVAÇÃO (Human-in-the-Loop)**
   Toda cotação gerada fica com status "AGUARDANDO APROVAÇÃO".
   Você SEMPRE informa o cliente que um vendedor humano irá revisar
   a cotação antes do envio da proposta formal. Nunca prometa prazo
   ou condição comercial sem aprovação humana.

6. **PRIVACIDADE (LGPD)**
   Trate dados de contato com discrição. Não repita o contato do
   cliente desnecessariamente no chat.

## COMO ATENDER

**Passo a passo recomendado:**

1. Entenda a necessidade: aplicação, dimensões ou código da peça.
2. Use as ferramentas para buscar produtos compatíveis.
3. Apresente as opções com especificações técnicas e preços do catálogo.
4. Se o cliente quiser cotar, colete nome e contato (se ainda não tiver).
5. Confirme os itens e quantidades com o cliente.
6. Chame tool_gerar_cotacao e apresente a confirmação com o número do pedido.

## FERRAMENTAS DISPONÍVEIS

- **tool_consultar_aplicacao**: busca por descrição de aplicação mecânica
- **tool_consultar_dimensoes**: busca por diâmetro interno, externo e largura (mm)
- **tool_verificar_estoque_preco**: verifica estoque e preço por código ISO
- **tool_gerar_cotacao**: registra cotação formal (status: AGUARDANDO APROVAÇÃO)

## TOM E ESTILO

- Profissional, técnico e objetivo — você fala com especialistas industriais.
- Use terminologia técnica correta (diâmetro interno, carga radial, vedação, etc.).
- Seja direto e eficiente: o cliente está no chão de fábrica ou no escritório
  de compras, não tem tempo a perder.
- Em caso de dúvida técnica que ultrapasse o catálogo, recomende consulta
  com a equipe de engenharia da Rash Rolamentos.
"""

# ── Estado do Grafo ───────────────────────────────────────────────────────────

class AgentState(TypedDict):
    """Estado compartilhado entre os nós do grafo LangGraph."""
    messages: Annotated[list, add_messages]


# ── Configuração do LLM ───────────────────────────────────────────────────────

def _build_llm(model_name: str = None):
    """Instancia o modelo Gemini com as ferramentas vinculadas."""
    target_model = model_name or get_config_var("GEMINI_MODEL", "gemini-1.5-flash")
    # Garante que não haja duplicações de 'models/' ou espaços na string do modelo
    clean_model = str(target_model).strip()
    if clean_model.startswith("models/"):
        clean_model = clean_model[len("models/"):]

    api_key = GEMINI_API_KEY or get_config_var("GEMINI_API_KEY", "")
    llm = ChatGoogleGenerativeAI(
        model=clean_model,
        google_api_key=api_key,
        temperature=0.1,
        max_retries=0,
    )
    return llm.bind_tools(rashbot_tools.TOOLS)


# ── Helper de Extração de Texto Limpo ────────────────────────────────────────

def extract_text_from_message_content(content) -> str:
    """
    Extrai apenas o texto legível em Markdown a partir do content da mensagem.
    Suporta strings puras, listas de blocos de texto (Gemini) e dicionários,
    removendo metadados técnicos como assinaturas e chaves internas.
    """
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        text_parts = []
        for item in content:
            if isinstance(item, dict):
                # Extrai apenas o campo de texto, ignorando 'extras', 'signature', etc.
                if "text" in item and item["text"]:
                    text_parts.append(str(item["text"]))
                elif "content" in item and item["content"]:
                    text_parts.append(str(item["content"]))
            elif isinstance(item, str) and item.strip():
                text_parts.append(item)
            else:
                val = getattr(item, "text", None) or getattr(item, "content", None)
                if val:
                    text_parts.append(str(val))
        return "\n\n".join(text_parts) if text_parts else str(content)

    if isinstance(content, dict):
        if "text" in content:
            return str(content["text"])
        if "content" in content:
            return str(content["content"])

    return str(content)


# Variável global para rastrear o modelo ativo com sucesso e modelos indisponíveis
ACTIVE_MODEL = get_config_var("GEMINI_MODEL", "gemini-1.5-flash")
UNAVAILABLE_MODELS = set()


def llm_node(state: AgentState) -> dict:
    """
    Nó principal: envia mensagens ao LLM (com system prompt) e
    retorna a resposta do modelo, com retentativas automáticas e fallback inteligente.
    """
    import time
    global ACTIVE_MODEL, UNAVAILABLE_MODELS
    mensagens = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    
    env_model = get_config_var("GEMINI_MODEL", "gemini-1.5-flash")

    # Monta lista de prioridades de modelo evitando os sabidamente 404
    candidate_list = []
    if ACTIVE_MODEL and ACTIVE_MODEL not in UNAVAILABLE_MODELS:
        candidate_list.append(ACTIVE_MODEL)
    if env_model and env_model not in candidate_list and env_model not in UNAVAILABLE_MODELS:
        candidate_list.append(env_model)

    for fallback in [env_model, "gemini-1.5-flash", "gemini-2.5-flash", "gemini-flash-latest", "gemini-3.6-flash"]:
        if fallback and fallback not in candidate_list and fallback not in UNAVAILABLE_MODELS:
            candidate_list.append(fallback)
            
    last_exception = None
    for model_name in candidate_list:
        try:
            llm = _build_llm(model_name)
            resposta = llm.invoke(mensagens)
            ACTIVE_MODEL = model_name
            logger.debug("LLM resposta (%s): %s", model_name, resposta)
            return {"messages": [resposta]}
        except Exception as exc:
            last_exception = exc
            err_str = str(exc).lower()
            logger.warning("Erro com modelo %s: %s", model_name, exc)
            if "404" in err_str or "not_found" in err_str:
                # Adiciona ao cache de indisponíveis para não tentar mais nessa execução
                UNAVAILABLE_MODELS.add(model_name)
                continue
            elif "429" in err_str or "resource_exhausted" in err_str or "quota" in err_str:
                time.sleep(1.0)
                continue
            else:
                continue

    err_msg = str(last_exception)
    if "429" in err_msg.lower() or "resource_exhausted" in err_msg.lower():
        msg_content = (
            "**Limite temporário de requisições atingido (Quota 429)**:\n\n"
            "A taxa limite de consultas por minuto da chave foi alcançada. "
            "Por favor, aguarde cerca de 30 segundos e envie sua mensagem novamente."
        )
    else:
        msg_content = (
            "Ocorreu uma instabilidade na consulta com o assistente técnico.\n\n"
            f"`{err_msg[:120]}`\n\n"
            "Por favor, tente novamente em instantes."
        )
        
    return {"messages": [AIMessage(content=msg_content)]}


# ── Construção do Grafo ───────────────────────────────────────────────────────

def build_graph() -> StateGraph:
    """
    Monta e compila o grafo LangGraph do RashBot.
    """
    builder = StateGraph(AgentState)
    builder.add_node("llm", llm_node)
    tool_node = ToolNode(tools=rashbot_tools.TOOLS)
    builder.add_node("tools", tool_node)

    builder.add_edge(START, "llm")
    builder.add_conditional_edges(
        "llm",
        tools_condition,
        {"tools": "tools", END: END},
    )
    builder.add_edge("tools", "llm")

    memory = MemorySaver()
    graph = builder.compile(checkpointer=memory)
    return graph


# ── Interface de Conversação ──────────────────────────────────────────────────

class RashBotAgent:
    """
    Wrapper de alto nível para o agente RashBot.
    """

    def __init__(self, thread_id: str = "default"):
        self.thread_id = thread_id
        self.graph = build_graph()
        self._config = {"configurable": {"thread_id": thread_id}}
        logger.info("RashBotAgent iniciado | thread_id=%r", thread_id)

    @property
    def active_model(self) -> str:
        """Retorna o modelo de linguagem ativo."""
        global ACTIVE_MODEL
        return ACTIVE_MODEL

    def chat(self, mensagem_usuario: str) -> str:
        """
        Envia uma mensagem do usuário e retorna a resposta do agente em texto puro formatado.
        """
        from langchain_core.messages import HumanMessage

        logger.info("Usuário [%s]: %r", self.thread_id, mensagem_usuario[:80])

        resultado = self.graph.invoke(
            {"messages": [HumanMessage(content=mensagem_usuario)]},
            config=self._config,
        )

        resposta = resultado["messages"][-1]
        raw_content = resposta.content if hasattr(resposta, "content") else str(resposta)
        
        # Extrai apenas texto limpo
        texto_limpo = extract_text_from_message_content(raw_content)

        logger.info("RashBot [%s]: %r", self.thread_id, texto_limpo[:80])
        return texto_limpo

    def get_history(self) -> list[dict]:
        """
        Retorna o histórico de mensagens da sessão atual formatado.
        """
        state = self.graph.get_state(config=self._config)
        historico = []
        for msg in state.values.get("messages", []):
            if isinstance(msg, AIMessage):
                historico.append({
                    "role": "ai",
                    "content": extract_text_from_message_content(msg.content)
                })
            elif isinstance(msg, ToolMessage):
                historico.append({
                    "role": "tool",
                    "content": extract_text_from_message_content(msg.content)
                })
            else:
                raw = getattr(msg, "content", str(msg))
                historico.append({
                    "role": "human",
                    "content": extract_text_from_message_content(raw)
                })
        return historico

    def reset(self) -> None:
        """Reinicia a conversa criando um novo thread_id."""
        import uuid
        self.thread_id = str(uuid.uuid4())
        self._config = {"configurable": {"thread_id": self.thread_id}}
        logger.info("Sessão reiniciada | novo thread_id=%r", self.thread_id)


# ── Entrypoint direto (modo CLI simples) ──────────────────────────────────────

if __name__ == "__main__":
    print("\n=== RashBot — Agente de Vendas Tecnicas (modo CLI) ===")
    print("Digite 'sair' para encerrar.\n")

    agente = RashBotAgent(thread_id="cli-session")

    while True:
        try:
            entrada = input("Voce: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nEncerrando...")
            break

        if entrada.lower() in ("sair", "exit", "quit"):
            print("RashBot: Ate logo! Bom trabalho.")
            break

        if not entrada:
            continue

        resposta = agente.chat(entrada)
        print(f"\nRashBot: {resposta}\n")
