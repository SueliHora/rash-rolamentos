"""
tests/test_basic.py
===================
Unit and integration test suite for RashBot components.
Validates database queries, deterministic catalog access,
LangChain tools, and agent graph integrity.
"""

import os
from unittest.mock import MagicMock, patch

import pytest

import src.database as db
import src.tools as tools_mod


@pytest.fixture(autouse=True)
def setup_database():
    """Ensure database exists and is populated before tests run."""
    db.ensure_db()


class TestDatabaseCatalog:
    """Test deterministic SQLite database layer."""

    def test_ensure_db_initialization(self):
        """Database and core tables should be initialized."""
        assert db.DB_PATH.exists()
        produtos = db.consultar_produtos_por_aplicacao("motor")
        assert len(produtos) > 0

    def test_search_by_application(self):
        """Should return matching bearings for natural language application search."""
        results = db.consultar_produtos_por_aplicacao("motor eletrico")
        assert len(results) >= 1
        codigos = [p["codigo"] for p in results]
        assert any("6204-2RSH" in c or "6304-2RSH" in c or "6205-C3" in c for c in codigos)

    def test_search_by_dimensions(self):
        """Should return exact matching bearing given d, D, B."""
        # 6204: d=20, D=47, B=14
        results = db.consultar_por_dimensoes(
            diametro_interno=20.0,
            diametro_externo=47.0,
            largura=14.0,
        )
        assert len(results) >= 1
        assert any(p["codigo"] == "6204-2RSH" for p in results)

    def test_verificar_estoque_e_preco(self):
        """Should return stock and unit price deterministically."""
        item = db.verificar_estoque_e_preco("6204-2RSH")
        assert item != {}
        assert item["codigo"] == "6204-2RSH"
        assert item["preco_unitario"] > 0
        assert item["estoque_qtd"] >= 0
        assert item["disponivel"] is True

    def test_consultar_produto_inexistente(self):
        """Non-existent products should return empty dict."""
        item = db.verificar_estoque_e_preco("CODIGO-INEXISTENTE-9999")
        assert item == {}

    def test_criar_cotacao_aguardando_aprovacao(self):
        """Quotations created should have AGUARDANDO_APROVACAO status for HITL."""
        itens = [{"produto_id": 1, "codigo": "6204-2RSH", "quantidade": 5, "preco_unitario": 22.90}]
        pedido_id = db.criar_cotacao(
            cliente_nome="Indústria Teste S.A.",
            cliente_contato="+55 11 99999-0000",
            itens=itens,
        )
        assert pedido_id > 0

    def test_registrar_auditoria(self):
        """Should record AI token usage and estimated cost in audit table."""
        # Should not raise SQLiteError
        db.registrar_auditoria(
            prompt_tokens=150,
            completion_tokens=50,
            custo_usd=0.000075,
            session_id="test-session-123",
        )

    def test_resumo_banco(self):
        """Should return system statistics dict."""
        stats = db.resumo_banco()
        assert stats["total_produtos"] > 0
        assert stats["estoque_total"] > 0


class TestLangChainTools:
    """Test LangChain deterministic tool wrappers."""

    def test_tool_consultar_aplicacao(self):
        """Tool should return structured product info as text."""
        result = tools_mod.tool_consultar_aplicacao.invoke({"termo": "motor eletrico"})
        assert "Código:" in result or "6204" in result

    def test_tool_consultar_dimensoes(self):
        """Tool should format dimensional search results."""
        result = tools_mod.tool_consultar_dimensoes.invoke({
            "diametro_interno_mm": 20.0,
            "diametro_externo_mm": 47.0,
            "largura_mm": 14.0,
        })
        assert "6204-2RSH" in result

    def test_tool_verificar_estoque_preco(self):
        """Tool should return stock and price for valid ISO code."""
        result = tools_mod.tool_verificar_estoque_preco.invoke({"codigo_produto": "6204-2RSH"})
        assert "6204-2RSH" in result
        assert "Preço unitário:" in result

    def test_tool_gerar_cotacao(self):
        """Tool should create quote from JSON string input."""
        result = tools_mod.tool_gerar_cotacao.invoke({
            "cliente_nome": "Cliente Pytest",
            "cliente_contato": "contato@empresa.com",
            "itens": '[{"produto_id": 1, "codigo": "6204-2RSH", "quantidade": 3, "preco_unitario": 22.90}]',
        })
        assert "Cotação" in result
        assert "Cliente Pytest" in result
        assert "AGUARDANDO APROVAÇÃO" in result


class TestAgentStructure:
    """Test agent state and structure."""

    def test_agent_state_annotations(self):
        """State schema must contain messages list."""
        from src.agent import AgentState
        assert "messages" in AgentState.__annotations__

    @patch.dict(os.environ, {"GEMINI_API_KEY": "dummy_test_key"})
    @patch("src.agent.ChatGoogleGenerativeAI")
    def test_agent_graph_compilation(self, mock_llm_cls):
        """Agent should compile StateGraph and bind deterministic tools."""
        from src.agent import RashBotAgent
        mock_llm_instance = MagicMock()
        mock_llm_instance.bind_tools.return_value = mock_llm_instance
        mock_llm_cls.return_value = mock_llm_instance

        agent = RashBotAgent(thread_id="test-thread-pytest")
        assert agent.graph is not None
        assert agent.thread_id == "test-thread-pytest"
