"""
app.py
======
Rash Rolamentos Industriais — Agente de Vendas Técnicas ("Soluções em Movimento").
Interface Web Corporativa B2B com Enquadramento Inicial, Tipografia e Responsividade Mobile Otimizadas.
"""

import os
import sys
import uuid
import base64
import sqlite3
import pathlib
import logging
import textwrap
from datetime import datetime
from typing import Optional

import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

# ── Path setup ────────────────────────────────────────────────────────────────
_ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ROOT / "src"))

load_dotenv(_ROOT / ".env")

import database as db
from agent import RashBotAgent, GEMINI_MODEL

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("rashbot.app")

# ── Helper de Extração de Texto Limpo ─────────────────────────────────────────
def extract_text_from_message_content(content) -> str:
    """Extrai texto em Markdown limpo do content da mensagem."""
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        text_parts = []
        for item in content:
            if isinstance(item, dict):
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


def get_logo_icon_base64() -> str:
    """Retorna o logo_icon.png em base64 para renderização HTML direta."""
    icon_path = _ROOT / "assets" / "logo_icon.png"
    if not icon_path.exists():
        icon_path = _ROOT / "assets" / "logo_clean.png"
    if not icon_path.exists():
        icon_path = _ROOT / "assets" / "logo.png"

    if icon_path.exists():
        with open(icon_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    return ""


# ═══════════════════════════════════════════════════════════════════════════════
#  CONFIGURAÇÃO DA PÁGINA
# ═══════════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="Rash Rolamentos Industriais — Vendas Técnicas",
    layout="wide",
    initial_sidebar_state="auto",
)

# ═══════════════════════════════════════════════════════════════════════════════
#  CSS GLOBAL — PONTO DE ENTRADA, TIPOGRAFIA, RESPONSIVIDADE MOBILE & NAV
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown("""
<style>
/* ── Fontes Corporativas ── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

/* ── Reset e Base ── */
html, body, [class*="css"], .stMarkdown, p, div, span, label {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    color: #E2E8F0;
}

/* ── Header nativo do Streamlit (botão de toggle acessível no Desktop) ── */
header[data-testid="stHeader"],
[data-testid="stHeader"] {
    background: transparent !important;
    height: 2.2rem !important;
    z-index: 99 !important;
}

[data-testid="stHeader"] [data-testid="stSidebarCollapseButton"] button {
    color: #D4AF37 !important;
    background: rgba(22, 34, 56, 0.8) !important;
    border: 1px solid rgba(212, 175, 55, 0.3) !important;
    border-radius: 4px !important;
}

.main {
    overflow-anchor: none !important;
}

.block-container {
    padding-top: 0.2rem !important;
    padding-bottom: 3.5rem !important;
    max-width: 100% !important;
}

[data-testid="stSidebarContent"] {
    padding-top: 0.4rem !important;
    padding-bottom: 0.6rem !important;
    padding-left: 0.85rem !important;
    padding-right: 0.85rem !important;
}

/* ── Background Principal ── */
.stApp {
    background: linear-gradient(150deg, #0D1B2A 0%, #162238 60%, #0D1B2A 100%) !important;
    min-height: 100vh;
}

/* ── Barra Lateral (Compacta e Delimitada) ── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0D1B2A 0%, #111D2E 100%) !important;
    border-right: 1px solid rgba(212, 175, 55, 0.22) !important;
    min-width: 280px !important;
    max-width: 320px !important;
}

/* ── CABEÇALHO PRINCIPAL COM LOGO INTEGRADO ── */
.main-header-wrapper {
    position: sticky !important;
    top: 0 !important;
    z-index: 100 !important;
    display: flex;
    align-items: center;
    gap: 12px;
    background: rgba(22, 34, 56, 0.95) !important;
    border: 1px solid rgba(212, 175, 55, 0.28) !important;
    border-radius: 6px !important;
    padding: 8px 14px !important;
    margin-bottom: 6px !important;
    backdrop-filter: blur(12px) !important;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.35) !important;
}

.main-header-icon {
    width: 32px !important;
    height: 32px !important;
    object-fit: contain;
    flex-shrink: 0;
}

.main-header-text {
    display: flex;
    flex-direction: column;
    justify-content: center;
    overflow: hidden;
}

.main-header-title {
    font-size: 1.22rem !important;
    font-weight: 700 !important;
    color: #FFFFFF !important;
    margin: 0 !important;
    line-height: 1.2 !important;
    letter-spacing: -0.01em;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.main-header-subtitle {
    font-size: 0.74rem !important;
    color: #D4AF37 !important;
    font-weight: 500 !important;
    margin: 1px 0 0 0 !important;
    line-height: 1.2 !important;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

/* ── Mini-Painel de Métricas (2x2) ── */
.sidebar-section-title {
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #D4AF37 !important;
    margin-bottom: 0.45rem;
    padding-bottom: 0.2rem;
    border-bottom: 1px solid rgba(212, 175, 55, 0.15);
}

.metrics-grid-2x2 {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 6px;
    margin-bottom: 0.45rem;
}

.metric-card-box {
    background: #111D2E !important;
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
    border-radius: 6px !important;
    padding: 6px 8px !important;
    display: flex;
    flex-direction: column;
    justify-content: center;
}

.metric-card-label {
    font-size: 0.68rem;
    font-weight: 600;
    text-transform: uppercase;
    color: #94A3B8 !important;
    margin-bottom: 1px;
    letter-spacing: 0.04em;
}

.metric-card-value {
    font-size: 1.02rem;
    font-weight: 700;
    color: #F8FAFC !important;
    line-height: 1.1;
    white-space: nowrap !important;
    overflow: hidden;
    text-overflow: clip;
}

.metric-card-value-accent {
    color: #F3C64F !important;
}

/* ── EXPANDERS (Dark/Navy & Alto Contraste) ── */
[data-testid="stExpander"] {
    background-color: #111D2E !important;
    border: 1px solid rgba(212, 175, 55, 0.22) !important;
    border-radius: 6px !important;
    color: #E2E8F0 !important;
    margin-bottom: 0.40rem !important;
}

[data-testid="stExpander"] summary,
[data-testid="stExpander"] summary p,
[data-testid="stExpander"] summary span {
    background-color: #111D2E !important;
    color: #F3C64F !important;
    font-weight: 600 !important;
    font-size: 0.80rem !important;
}

[data-testid="stExpander"] summary:hover,
[data-testid="stExpander"] summary:hover p,
[data-testid="stExpander"] summary:hover span {
    color: #FFFFFF !important;
    background-color: #16253B !important;
}

[data-testid="stExpander"] div[role="region"] {
    background-color: #0E1726 !important;
    color: #E2E8F0 !important;
    border-top: 1px solid rgba(212, 175, 55, 0.12) !important;
    border-bottom-left-radius: 6px !important;
    border-bottom-right-radius: 6px !important;
    padding: 0.50rem 0.65rem !important;
}

/* ── Cards de Cotação Pendente ── */
.cotacao-card {
    background: rgba(17, 29, 46, 0.95) !important;
    border: 1px solid rgba(229, 184, 66, 0.35) !important;
    border-radius: 6px !important;
    padding: 0.50rem 0.65rem !important;
    margin-bottom: 0.40rem !important;
}

.cotacao-id {
    font-size: 0.74rem;
    font-weight: 800;
    color: #E5B842 !important;
}

.cotacao-cliente {
    font-size: 0.82rem;
    color: #FFFFFF !important;
    font-weight: 600;
    margin: 2px 0;
}

.cotacao-total {
    font-size: 0.90rem;
    font-weight: 800;
    color: #E5B842 !important;
}

.cotacao-data {
    font-size: 0.68rem;
    color: #94A3B8 !important;
}

/* ── Status Badges ── */
.status-aguardando {
    background: rgba(229, 184, 66, 0.15);
    color: #E5B842 !important;
    border: 1px solid rgba(229, 184, 66, 0.4);
    padding: 1px 5px;
    border-radius: 3px;
    font-size: 0.66rem;
    font-weight: 700;
    text-transform: uppercase;
}

.status-aprovado {
    background: rgba(46, 196, 182, 0.15);
    color: #2EC4B6 !important;
    border: 1px solid rgba(46, 196, 182, 0.4);
    padding: 1px 5px;
    border-radius: 3px;
    font-size: 0.66rem;
    font-weight: 700;
    text-transform: uppercase;
}

.status-rejeitado {
    background: rgba(230, 57, 70, 0.15);
    color: #E63946 !important;
    border: 1px solid rgba(230, 57, 70, 0.4);
    padding: 1px 5px;
    border-radius: 3px;
    font-size: 0.66rem;
    font-weight: 700;
    text-transform: uppercase;
}

/* ── Mensagens do Chat ── */
.chat-scroll-area {
    margin-top: 0 !important;
    margin-bottom: 85px !important;
}

[data-testid="stChatMessage"] {
    background: rgba(27, 38, 59, 0.75) !important;
    border: 1px solid rgba(212, 175, 55, 0.15) !important;
    border-radius: 6px !important;
    padding: 8px 12px !important;
    margin-bottom: 6px !important;
    color: #E2E8F0 !important;
    font-size: 0.86rem !important;
}

[data-testid="stChatMessage"]:first-of-type {
    margin-top: 0 !important;
}

[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]),
[data-testid="stChatMessage"]:has([aria-label="Chat message from user"]) {
    background: rgba(13, 27, 42, 0.9) !important;
    border: 1px solid rgba(212, 175, 55, 0.28) !important;
}

/* ── Badges Técnicas de Ferramentas ── */
.tool-badge {
    display: inline-flex;
    align-items: center;
    background: rgba(212, 175, 55, 0.12);
    border: 1px solid rgba(212, 175, 55, 0.35);
    color: #E5B842 !important;
    padding: 1px 5px;
    border-radius: 3px;
    font-size: 0.68rem;
    font-weight: 600;
    font-family: 'JetBrains Mono', monospace;
    margin-right: 4px;
    margin-bottom: 3px;
}

/* ── BOTÕES GLOBAIS & SUGESTÕES TÉCNICAS ── */
div[data-testid="stButton"] > button {
    background: rgba(27, 38, 59, 0.85) !important;
    color: #E2E8F0 !important;
    font-weight: 600 !important;
    border: 1px solid rgba(212, 175, 55, 0.25) !important;
    border-radius: 5px !important;
    font-size: 0.78rem !important;
    line-height: 1.2 !important;
    height: auto !important;
    min-height: 38px !important;
    padding: 6px 10px !important;
    white-space: normal !important;
    word-wrap: break-word !important;
    text-align: left !important;
    transition: all 0.15s ease !important;
}

div[data-testid="stButton"] > button:hover {
    background: rgba(27, 38, 59, 1.0) !important;
    border-color: #E5B842 !important;
    color: #FFFFFF !important;
    transform: translateY(-1px) !important;
}

div[data-testid="stButton"] > button[kind="primary"] {
    background: linear-gradient(135deg, #D4AF37 0%, #AA820A 100%) !important;
    color: #0D1B2A !important;
    font-weight: 700 !important;
    border: 1px solid #E5B842 !important;
}

/* Botões da Sidebar */
[data-testid="stSidebar"] div[data-testid="stButton"] > button {
    white-space: nowrap !important;
    text-align: center !important;
    min-height: unset !important;
    padding: 4px 8px !important;
    font-size: 0.74rem !important;
}

/* ── Input do Chat Fixado ── */
[data-testid*="Bottom"],
[data-testid*="bottom"],
[data-testid="stBottom"],
[data-testid="stBottom"] > div,
[data-testid="stBottomBlockContainer"],
.stBottomBlockContainer,
.stChatFloatingInputContainer,
div[data-testid="stBottomBlockContainer"],
div[data-testid="stBottom"] div,
section[data-testid="stBottom"],
.stBottom,
footer,
[data-testid="stFooter"] {
    background: transparent !important;
    background-color: transparent !important;
    box-shadow: none !important;
    border: none !important;
    outline: none !important;
}

.stChatFloatingInputContainer,
.stChatFloatingInputContainer * {
    background-color: transparent !important;
}

[data-testid="stChatInput"],
[data-testid="stChatInput"] > div,
.stChatInput,
.stChatInput > div {
    background: transparent !important;
    background-color: transparent !important;
    border: none !important;
    box-shadow: none !important;
}

[data-testid="stChatInput"] textarea,
.stChatInput textarea,
div[data-testid="stChatInput"] textarea {
    background: #162238 !important;
    background-color: #162238 !important;
    color: #FFFFFF !important;
    border: 1px solid rgba(212, 175, 55, 0.35) !important;
    border-radius: 6px !important;
    font-size: 0.88rem !important;
    box-shadow: 0 4px 16px rgba(0,0,0,0.4) !important;
}

[data-testid="stChatInput"] textarea:focus,
.stChatInput textarea:focus {
    border-color: #E5B842 !important;
    box-shadow: 0 0 0 2px rgba(229, 184, 66, 0.2) !important;
}

[data-testid="stChatInput"] button,
.stChatInput button {
    color: #E5B842 !important;
    background: transparent !important;
}

/* ── Separadores ── */
hr {
    margin: 0.5rem 0 !important;
    border-color: rgba(212, 175, 55, 0.15) !important;
}

/* ── Ocultar elementos desnecessários ── */
#MainMenu, footer { visibility: hidden; }

/* ── DESKTOP (> 768px): Oculta a barra de abas exclusiva de mobile ── */
@media (min-width: 769px) {
    div[data-testid="element-container"]:has(.mobile-nav-marker),
    div[data-testid="element-container"]:has(.mobile-nav-marker) + div[data-testid="stHorizontalBlock"] {
        display: none !important;
    }
}

/* ── RESPONSIVIDADE MOBILE (<= 768px) ── */
@media (max-width: 768px) {
    header[data-testid="stHeader"],
    [data-testid="stHeader"] {
        display: none !important;
    }

    .block-container {
        padding-left: 0.45rem !important;
        padding-right: 0.45rem !important;
        padding-top: 0.15rem !important;
        padding-bottom: 4.8rem !important;
    }

    .main-header-wrapper {
        padding: 6px 10px !important;
        gap: 8px !important;
        margin-bottom: 4px !important;
    }

    .main-header-icon {
        width: 26px !important;
        height: 26px !important;
    }

    .main-header-title {
        font-size: 1.02rem !important;
    }

    .main-header-subtitle {
        font-size: 0.67rem !important;
    }

    [data-testid="stChatMessage"] {
        padding: 7px 10px !important;
        font-size: 0.84rem !important;
        margin-bottom: 5px !important;
    }

    div[data-testid="stButton"] > button {
        min-height: 42px !important;
        font-size: 0.76rem !important;
        padding: 6px 8px !important;
    }

    .metrics-grid-2x2 {
        gap: 5px !important;
    }

    .metric-card-box {
        padding: 5px 6px !important;
    }

    .metric-card-value {
        font-size: 0.95rem !important;
    }
}
</style>
""", unsafe_allow_html=True)

# ── Trava de Scroll no Topo no Carregamento Inicial ───────────────────────────
components.html(
    """
    <script>
        window.parent.document.querySelector('.main').scrollTop = 0;
        window.scrollTo(0, 0);
    </script>
    """,
    height=0,
)


# ═══════════════════════════════════════════════════════════════════════════════
#  HELPERS DE BANCO DE DADOS
# ═══════════════════════════════════════════════════════════════════════════════

def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(db.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_cotacoes_pendentes() -> list[dict]:
    """Retorna cotações com status AGUARDANDO_APROVACAO."""
    with _conn() as conn:
        rows = conn.execute("""
            SELECT p.id, p.cliente_nome, p.cliente_contato,
                   p.total, p.data_criacao,
                   COUNT(i.id) as qtd_itens
            FROM pedidos p
            LEFT JOIN itens_pedido i ON i.pedido_id = p.id
            WHERE p.status = 'AGUARDANDO_APROVACAO'
            GROUP BY p.id
            ORDER BY p.data_criacao DESC
            LIMIT 10
        """).fetchall()
        return [dict(r) for r in rows]


def get_ultimos_pedidos(limite: int = 4) -> list[dict]:
    """Retorna os últimos pedidos cadastrados."""
    with _conn() as conn:
        rows = conn.execute("""
            SELECT id, cliente_nome, status, total, data_criacao
            FROM pedidos
            ORDER BY data_criacao DESC
            LIMIT ?
        """, (limite,)).fetchall()
        return [dict(r) for r in rows]


def get_itens_pedido(pedido_id: int) -> list[dict]:
    """Retorna itens de um pedido com código do produto."""
    with _conn() as conn:
        rows = conn.execute("""
            SELECT p.codigo, p.tipo, i.quantidade, i.preco_unitario,
                   (i.quantidade * i.preco_unitario) as subtotal
            FROM itens_pedido i
            JOIN produtos p ON p.id = i.produto_id
            WHERE i.pedido_id = ?
        """, (pedido_id,)).fetchall()
        return [dict(r) for r in rows]


def atualizar_status_pedido(pedido_id: int, novo_status: str) -> None:
    """Atualiza o status de um pedido (ação humana)."""
    with _conn() as conn:
        conn.execute(
            "UPDATE pedidos SET status = ? WHERE id = ?",
            (novo_status, pedido_id)
        )
        conn.commit()


def get_auditoria_resumo() -> dict:
    """Totais de tokens e custo da sessão."""
    with _conn() as conn:
        row = conn.execute("""
            SELECT COUNT(*) as chamadas,
                   COALESCE(SUM(prompt_tokens), 0) as prompt_tk,
                   COALESCE(SUM(completion_tokens), 0) as comp_tk,
                   COALESCE(SUM(custo_estimado_usd), 0) as custo_total
            FROM auditoria_ia
        """).fetchone()
        return dict(row) if row else {}


# ═══════════════════════════════════════════════════════════════════════════════
#  INICIALIZAÇÃO DO SESSION STATE
# ═══════════════════════════════════════════════════════════════════════════════

def init_session():
    """Inicializa variáveis de sessão."""
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())[:8]

    if "active_tab" not in st.session_state:
        st.session_state.active_tab = "chat"

    if "agent" not in st.session_state:
        st.session_state.agent = RashBotAgent(
            thread_id=st.session_state.session_id
        )

    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "ai",
                "content": (
                    "Bem-vindo à **Rash Rolamentos Industriais** — *Soluções em Movimento*.\n\n"
                    "Assistente técnico corporativo para consulta de catálogo determinístico, "
                    "verificação de medidas e emissão de cotações comerciais."
                ),
                "tools_used": [],
            }
        ]


# ═══════════════════════════════════════════════════════════════════════════════
#  PAINEL OPERACIONAL MODULARIZADO (HITL, MÉTRICAS E AUDITORIA)
# ═══════════════════════════════════════════════════════════════════════════════

def render_painel_operacional(is_sidebar: bool = False):
    """
    Renderiza o painel operacional completo com suporte tanto a sidebar (desktop)
    quanto à área principal (mobile/tablet).
    """
    prefix = "sb" if is_sidebar else "main"

    if not is_sidebar:
        col_title, col_back = st.columns([3, 1])
        with col_title:
            st.markdown('<div class="sidebar-section-title" style="font-size:0.85rem;margin-top:0.2rem;">Painel Operacional & Governança</div>', unsafe_allow_html=True)
        with col_back:
            if st.button("💬 Ir ao Chat", key=f"btn_goto_chat_{prefix}", type="primary", use_container_width=True):
                st.session_state.active_tab = "chat"
                st.rerun()
    else:
        st.markdown('<div class="sidebar-section-title">Painel Operacional</div>', unsafe_allow_html=True)

    # ── 1. Mini-Painel de Métricas 2x2 ───────────────────────────────────
    resumo = db.resumo_banco()
    pendentes = get_cotacoes_pendentes()
    qtd_pendentes = len(pendentes)

    total_prods = resumo.get('total_produtos', 0)
    total_peds = resumo.get('total_pedidos', 0)
    estoque_fmt = f"{resumo.get('estoque_total', 0):,}".replace(",", ".")
    val_pend_color = "metric-card-value-accent" if qtd_pendentes > 0 else ""

    st.markdown(f"""
    <div class="metrics-grid-2x2">
        <div class="metric-card-box">
            <div class="metric-card-label">Catálogo</div>
            <div class="metric-card-value">{total_prods}</div>
        </div>
        <div class="metric-card-box">
            <div class="metric-card-label">Pedidos</div>
            <div class="metric-card-value">{total_peds}</div>
        </div>
        <div class="metric-card-box">
            <div class="metric-card-label">Estoque</div>
            <div class="metric-card-value">{estoque_fmt}</div>
        </div>
        <div class="metric-card-box">
            <div class="metric-card-label">Pendentes</div>
            <div class="metric-card-value {val_pend_color}">{qtd_pendentes}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # ── 2. Aprovação de Cotações (HITL) ──────────────────────────────────
    label_hitl = f"Cotações Pendentes ({qtd_pendentes})"
    with st.expander(label_hitl, expanded=False):
        if not pendentes:
            st.caption("Nenhuma cotação aguardando aprovação humana.")
        else:
            for cotacao in pendentes:
                pedido_id = cotacao["id"]
                cliente   = cotacao["cliente_nome"]
                total     = cotacao["total"]
                qtd_itens = cotacao["qtd_itens"]
                data_raw  = cotacao.get("data_criacao", "")

                try:
                    dt = datetime.strptime(data_raw[:19], "%Y-%m-%d %H:%M:%S")
                    data_fmt = dt.strftime("%d/%m %H:%M")
                except Exception:
                    data_fmt = data_raw[:16] if data_raw else "—"

                st.markdown(
                    f'<div class="cotacao-card">'
                    f'<div class="cotacao-id">COTAÇÃO #{pedido_id}</div>'
                    f'<div class="cotacao-cliente">{cliente}</div>'
                    f'<div class="cotacao-total">R$ {total:,.2f}'.replace(",", "X").replace(".", ",").replace("X", ".") + f'</div>'
                    f'<div class="cotacao-data">{qtd_itens} item(ns) • {data_fmt}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

                itens = get_itens_pedido(pedido_id)
                if itens:
                    for item in itens:
                        sub = item["quantidade"] * item["preco_unitario"]
                        st.caption(f"• {item['codigo']} × {item['quantidade']} = R$ {sub:.2f}")

                col_a, col_r = st.columns([1, 1])
                with col_a:
                    if st.button("Aprovar", key=f"ap_{pedido_id}_{prefix}", type="primary", use_container_width=True):
                        atualizar_status_pedido(pedido_id, "APROVADO")
                        db.registrar_auditoria(0, 0, 0.0, session_id=f"op-approve-{pedido_id}")
                        st.success(f"Cotação #{pedido_id} aprovada com sucesso.")
                        st.rerun()
                with col_r:
                    if st.button("Rejeitar", key=f"rej_{pedido_id}_{prefix}", use_container_width=True):
                        atualizar_status_pedido(pedido_id, "REJEITADO")
                        st.warning(f"Cotação #{pedido_id} rejeitada.")
                        st.rerun()

    # ── 3. Histórico Recente ──────────────────────────────────────────────
    with st.expander("Histórico Recente de Pedidos", expanded=False):
        ultimos = get_ultimos_pedidos(4)
        if not ultimos:
            st.caption("Nenhum pedido registrado.")
        else:
            for p in ultimos:
                status_cls = {
                    "AGUARDANDO_APROVACAO": "status-aguardando",
                    "APROVADO": "status-aprovado",
                    "REJEITADO": "status-rejeitado",
                }.get(p["status"], "status-aguardando")

                status_label = {
                    "AGUARDANDO_APROVACAO": "Pendente",
                    "APROVADO": "Aprovado",
                    "REJEITADO": "Rejeitado",
                }.get(p["status"], p["status"])

                nome_curto = p["cliente_nome"][:16] + ("…" if len(p["cliente_nome"]) > 16 else "")
                st.markdown(
                    f'<div style="display:flex;justify-content:space-between;align-items:center;padding:4px 0;border-bottom:1px solid rgba(212,175,55,0.08);">'
                    f'<div>'
                    f'  <span style="color:#E5B842;font-size:0.74rem;font-weight:700">#{p["id"]}</span> '
                    f'  <span style="color:#FFFFFF;font-size:0.78rem;">{nome_curto}</span><br>'
                    f'  <span style="color:#E5B842;font-size:0.74rem;font-weight:700">R$ {p["total"]:.2f}</span>'
                    f'</div>'
                    f'<span class="{status_cls}">{status_label}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

    # ── 4. Auditoria de Governança ────────────────────────────────────────
    with st.expander("Auditoria de Governança & Custos", expanded=False):
        audit = get_auditoria_resumo()
        chamadas = audit.get("chamadas", 0)
        custo_val = audit.get("custo_total", 0.0)
        custo_str = f"${custo_val:.4f}"

        st.markdown(f"""
        <div class="metrics-grid-2x2" style="margin-bottom: 0;">
            <div class="metric-card-box">
                <div class="metric-card-label">Chamadas IA</div>
                <div class="metric-card-value">{chamadas}</div>
            </div>
            <div class="metric-card-box">
                <div class="metric-card-label">Custo Est.</div>
                <div class="metric-card-value">{custo_str}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # ── 5. Controles de Sessão no Rodapé ──────────────────────────────────
    if st.button("Reiniciar Atendimento", key=f"btn_reset_{prefix}", use_container_width=True):
        st.session_state.agent.reset()
        st.session_state.session_id = str(uuid.uuid4())[:8]
        st.session_state.messages = [
            {
                "role": "ai",
                "content": (
                    "Bem-vindo à **Rash Rolamentos Industriais** — *Soluções em Movimento*.\n\n"
                    "Assistente técnico corporativo para consulta de catálogo determinístico, "
                    "verificação de medidas e emissão de cotações comerciais."
                ),
                "tools_used": [],
            }
        ]
        st.session_state.active_tab = "chat"
        st.rerun()

    active_model_name = getattr(st.session_state.get("agent"), "active_model", GEMINI_MODEL)
    st.caption(f"Sessão: `{st.session_state.session_id}` | Modelo: `{active_model_name}`")


def render_sidebar():
    """Renderiza a barra lateral para desktop."""
    with st.sidebar:
        render_painel_operacional(is_sidebar=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  CABEÇALHO PRINCIPAL, NAVEGAÇÃO DE ABAS & CHAT
# ═══════════════════════════════════════════════════════════════════════════════

def render_main_header():
    """Renderiza cabeçalho principal integrado com ícone e títulos."""
    icon_b64 = get_logo_icon_base64()
    if icon_b64:
        img_tag = f'<img src="data:image/png;base64,{icon_b64}" class="main-header-icon" alt="Rash Rolamentos">'
    else:
        img_tag = '<div style="font-size:2rem;line-height:1;">⚙️</div>'

    st.markdown(f"""
    <div class="main-header-wrapper">
        {img_tag}
        <div class="main-header-text">
            <h1 class="main-header-title">Rash Rolamentos Industriais</h1>
            <div class="main-header-subtitle">Atendimento Técnico & Comercial • Soluções em Movimento</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_top_navigation(qtd_pendentes: int):
    """Renderiza barra de abas exclusiva para alternância rápida no mobile."""
    st.markdown('<div class="mobile-nav-marker"></div>', unsafe_allow_html=True)
    col_chat, col_painel = st.columns([1, 1])

    is_chat = (st.session_state.active_tab == "chat")
    is_painel = (st.session_state.active_tab == "painel")

    with col_chat:
        if st.button("💬 Chat Técnico", key="tab_nav_chat", type="primary" if is_chat else "secondary", use_container_width=True):
            if not is_chat:
                st.session_state.active_tab = "chat"
                st.rerun()

    with col_painel:
        label_painel = f"📊 Painel & Cotações ({qtd_pendentes})" if qtd_pendentes > 0 else "📊 Painel Operacional"
        if st.button(label_painel, key="tab_nav_painel", type="primary" if is_painel else "secondary", use_container_width=True):
            if not is_painel:
                st.session_state.active_tab = "painel"
                st.rerun()


def extract_tool_names_from_agent_state() -> list[str]:
    """Extrai nomes técnicos das ferramentas executadas."""
    try:
        from langchain_core.messages import AIMessage as LC_AIMessage
        state = st.session_state.agent.graph.get_state(
            config=st.session_state.agent._config
        )
        tool_names = []
        messages = state.values.get("messages", [])
        for msg in reversed(messages):
            if isinstance(msg, LC_AIMessage):
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    for tc in msg.tool_calls:
                        name = tc.get("name", "ferramenta")
                        friendly = {
                            "tool_consultar_aplicacao": "Consulta por Aplicação",
                            "tool_consultar_dimensoes": "Consulta por Dimensões",
                            "tool_verificar_estoque_preco": "Verificação de Catálogo & Estoque",
                            "tool_gerar_cotacao": "Geração de Cotação",
                        }.get(name, name)
                        tool_names.append(friendly)
                break
        return tool_names
    except Exception:
        return []


def handle_user_input(user_input: str):
    """Processa mensagem do usuário com tratamento corporativo de erros."""
    st.session_state.messages.append({
        "role": "human",
        "content": user_input,
        "tools_used": [],
    })

    with st.spinner("Consultando catálogo técnico..."):
        try:
            resposta_texto = st.session_state.agent.chat(user_input)
            tools_usadas = extract_tool_names_from_agent_state()

            prompt_tk = len(user_input.split()) * 4
            comp_tk = len(str(resposta_texto).split()) * 4
            custo_est = (prompt_tk * 0.075 + comp_tk * 0.30) / 1_000_000
            db.registrar_auditoria(prompt_tk, comp_tk, custo_est, session_id=st.session_state.session_id)

            st.session_state.messages.append({
                "role": "ai",
                "content": resposta_texto,
                "tools_used": tools_usadas,
            })
        except Exception as exc:
            err_str = str(exc)
            logger.error("Erro no processamento do chat: %s", exc)
            if "429" in err_str or "quota" in err_str.lower() or "resource_exhausted" in err_str.lower():
                msg_erro = (
                    "**Limite temporário de requisições atingido (Quota 429)**:\n\n"
                    "O serviço atingiu a taxa limite de mensagens por minuto da chave da API. "
                    "Por favor, aguarde cerca de **30 segundos** e envie sua mensagem novamente."
                )
            else:
                msg_erro = (
                    "Ocorreu uma instabilidade na consulta com o assistente técnico.\n\n"
                    f"`{textwrap.shorten(err_str, width=150)}`\n\n"
                    "Por favor, tente novamente em instantes."
                )
            st.session_state.messages.append({
                "role": "ai",
                "content": msg_erro,
                "tools_used": [],
            })


def render_main_chat():
    """Renderiza a área de chat corporativa B2B."""
    
    # ── Container de Mensagens com Margem Inferior ─────────────────────────
    st.markdown('<div class="chat-scroll-area">', unsafe_allow_html=True)

    # Histórico de Mensagens
    for msg in st.session_state.messages:
        role = msg.get("role", "ai")
        content_raw = msg.get("content", "")
        content = extract_text_from_message_content(content_raw)
        tools = msg.get("tools_used", [])

        if role == "human":
            with st.chat_message("user"):
                st.markdown(content)
        else:
            with st.chat_message("assistant"):
                if tools:
                    badges_html = "".join(f'<span class="tool-badge">[Tool: {t}]</span>' for t in tools)
                    st.markdown(badges_html, unsafe_allow_html=True)
                st.markdown(content)

    # Sugestões Rápidas em Tons Escuros Discretos
    if len(st.session_state.messages) <= 1:
        st.markdown(
            '<p style="color:#94A3B8;font-size:0.75rem;font-weight:600;margin-top:0.6rem;margin-bottom:0.35rem;">'
            'Sugestões de consulta técnica:</p>',
            unsafe_allow_html=True,
        )
        sugestoes = [
            "Motor trifásico 15 CV (Alta rotação)",
            "Medidas: 60mm int. × 110mm ext. × 28mm",
            "Estoque e tabela do código 6204-2RSH",
            "Cotação de 10 un. do modelo 22212-E",
        ]
        col_sug1, col_sug2 = st.columns(2)
        for i, sug in enumerate(sugestoes):
            col = col_sug1 if i % 2 == 0 else col_sug2
            with col:
                if st.button(f"{sug}", key=f"sug_{i}", use_container_width=True):
                    handle_user_input(sug)
                    st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

    # ── Input do Chat Fixado na Base ───────────────────────────────────────
    user_input = st.chat_input("Digite sua especificação técnica ou código do rolamento...")
    if user_input and user_input.strip():
        handle_user_input(user_input.strip())
        st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
#  ENTRYPOINT
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    init_session()
    
    # Obtém cotações pendentes para badge dinâmico
    pendentes = get_cotacoes_pendentes()
    qtd_pendentes = len(pendentes)

    # Barra lateral (desktop)
    render_sidebar()
    
    # Cabeçalho Principal Integrado
    render_main_header()
    
    # Barra de Navegação de Abas (exclusiva mobile via CSS)
    render_top_navigation(qtd_pendentes)

    # Alternância de Visão no Conteúdo Principal
    if st.session_state.active_tab == "chat":
        render_main_chat()
    else:
        render_painel_operacional(is_sidebar=False)


if __name__ == "__main__":
    main()
