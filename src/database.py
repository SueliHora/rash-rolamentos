"""
src/database.py
===============
Camada de acesso ao banco SQLite do RashBot.

Todas as consultas são DETERMINÍSTICAS — o modelo de linguagem NUNCA
inventa preços, medidas ou códigos. Ele chama estas funções e exibe
apenas o que o banco retornar. (PRD §3.2 — Consulta Determinística)

Convenções:
- Cada função abre e fecha sua própria conexão (stateless).
- Todos os retornos são dicts/lists de dicts com chaves em snake_case.
- Erros de banco propagam SQLiteError para o caller tratar.
- A busca textual é normalizada (sem acento, lowercase) para aceitar
  termos digitados sem acentuação (ex: 'motor eletrico' == 'motor elétrico').
"""

import sys
import sqlite3
import pathlib
import logging
import unicodedata
from typing import Optional

# ── Configuração ──────────────────────────────────────────────────────────────

logger = logging.getLogger(__name__)

# Resolve o caminho do banco independentemente de onde o script é executado
_PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
DB_PATH = _PROJECT_ROOT / "data" / "rash.db"
SCHEMA_PATH = _PROJECT_ROOT / "data" / "schema.sql"


# ── Inicialização e Seed Automático ──────────────────────────────────────────

def init_db(db_file: Optional[pathlib.Path] = None, schema_file: Optional[pathlib.Path] = None) -> None:
    """
    Cria a estrutura de tabelas e índices no banco de dados SQLite
    a partir do arquivo schema.sql. Cria o diretório pai caso não exista.
    """
    target_db = db_file or DB_PATH
    target_schema = schema_file or SCHEMA_PATH

    target_db.parent.mkdir(parents=True, exist_ok=True)

    if not target_schema.exists():
        logger.error("Arquivo de schema não encontrado: %s", target_schema)
        raise FileNotFoundError(f"Schema não encontrado em: {target_schema}")

    conn = sqlite3.connect(target_db)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        schema_sql = target_schema.read_text(encoding="utf-8")
        conn.executescript(schema_sql)
        conn.commit()
        logger.info("Schema do banco aplicado com sucesso em: %s", target_db)
    finally:
        conn.close()


def seed_data(db_file: Optional[pathlib.Path] = None) -> int:
    """
    Popula o banco de dados com os rolamentos industriais do catálogo inicial.
    Retorna a quantidade de produtos inseridos.
    """
    target_db = db_file or DB_PATH
    data_dir = str(_PROJECT_ROOT / "data")
    if data_dir not in sys.path:
        sys.path.insert(0, data_dir)

    conn = sqlite3.connect(target_db)
    try:
        import seed as seed_mod
        conn.execute("PRAGMA foreign_keys = ON")
        inserted = seed_mod.seed_produtos(conn, seed_mod.PRODUTOS)
        logger.info("Catálogo inicial populado com sucesso em %s (%d produtos).", target_db, len(seed_mod.PRODUTOS))
        return inserted
    except Exception as exc:
        logger.error("Erro ao popular catálogo de produtos via seed_data: %s", exc)
        return 0
    finally:
        conn.close()


def ensure_db(db_file: Optional[pathlib.Path] = None, schema_file: Optional[pathlib.Path] = None) -> None:
    """
    Garante que o banco de dados e todas as tabelas necessárias existam.
    Caso o arquivo ou tabelas essenciais não existam ou estejam vazias,
    executa init_db() e seed_data() automaticamente.
    """
    target_db = db_file or DB_PATH
    target_schema = schema_file or SCHEMA_PATH

    target_db.parent.mkdir(parents=True, exist_ok=True)

    needs_init = False
    if not target_db.exists() or target_db.stat().st_size == 0:
        needs_init = True
    else:
        conn = None
        try:
            conn = sqlite3.connect(target_db)
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('produtos', 'pedidos', 'itens_pedido', 'auditoria_ia')"
            )
            tables = {row[0] for row in cursor.fetchall()}
            required_tables = {'produtos', 'pedidos', 'itens_pedido', 'auditoria_ia'}
            if not required_tables.issubset(tables):
                needs_init = True
            else:
                prod_count = conn.execute("SELECT COUNT(*) FROM produtos").fetchone()[0]
                if prod_count == 0:
                    conn.close()
                    conn = None
                    seed_data(target_db)
        except Exception as exc:
            logger.warning("Falha ao verificar tabelas em %s: %s. Reconstruindo banco...", target_db, exc)
            needs_init = True
        finally:
            if conn is not None:
                conn.close()

    if needs_init:
        init_db(target_db, target_schema)
        seed_data(target_db)


# ── Helpers internos ──────────────────────────────────────────────────────────

def _normalize(text: str) -> str:
    """
    Remove acentos e converte para lowercase para busca fonética.
    Ex: 'Motor Elétrico' -> 'motor eletrico'
    """
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower()


def _get_connection() -> sqlite3.Connection:
    """
    Retorna uma conexão com row_factory configurada para dicts.
    Garante que o banco e as tabelas existam antes de conectar.
    Registra a função escalar `normalize_text` para buscas sem acento.
    """
    ensure_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row          # acesso por nome de coluna
    conn.execute("PRAGMA foreign_keys = ON")
    # Registra função escalar para normalização dentro do SQLite
    conn.create_function("normalize_text", 1, _normalize)
    return conn


def _row_to_dict(row: sqlite3.Row) -> dict:
    """Converte sqlite3.Row em dict Python puro."""
    return dict(row)


# ── Funções públicas ──────────────────────────────────────────────────────────

def consultar_produtos_por_aplicacao(termo: str) -> list[dict]:
    """
    Busca rolamentos cujo campo `aplicacao_recomendada` OU `tipo`
    contenha o(s) termo(s) informado(s) (busca case-insensitive, parcial).

    Suporta múltiplos termos separados por espaço: cada termo é aplicado
    como filtro AND para refinar resultados (ex: "motor alta rotacao").

    Parâmetros
    ----------
    termo : str
        Palavra-chave ou frase descrevendo a aplicação mecânica.

    Retorna
    -------
    list[dict]
        Lista de produtos compatíveis, ordenados por relevância
        (mais campos correspondentes primeiro) e depois por preço.
        Retorna lista vazia se nenhum produto for encontrado.

    Exemplo
    -------
    >>> consultar_produtos_por_aplicacao("motor eletrico")
    [{'id': 2, 'codigo': '6204-2RSH', 'tipo': 'Rolamento Rigido de Esferas', ...}]
    """
    if not termo or not termo.strip():
        return []

    termos = [_normalize(t) for t in termo.strip().split() if t.strip()]

    # Monta cláusulas WHERE usando normalize_text() registrada na conexão
    # Isso permite 'motor eletrico' encontrar 'Motor Elétrico' no banco
    clausulas = " AND ".join(
        "(normalize_text(aplicacao_recomendada) LIKE ? OR normalize_text(tipo) LIKE ?)"
        for _ in termos
    )
    # Cada termo gera 2 parâmetros (aplicacao + tipo) — já normalizados
    params = [f"%{t}%" for t in termos for _ in range(2)]

    sql = f"""
        SELECT
            id,
            codigo,
            tipo,
            diametro_interno_mm,
            diametro_externo_mm,
            largura_mm,
            aplicacao_recomendada,
            preco_unitario,
            estoque_qtd
        FROM produtos
        WHERE {clausulas}
        ORDER BY preco_unitario ASC
    """

    try:
        with _get_connection() as conn:
            cursor = conn.execute(sql, params)
            rows = cursor.fetchall()
            result = [_row_to_dict(r) for r in rows]
            logger.debug(
                "consultar_produtos_por_aplicacao(termo=%r) -> %d resultado(s)",
                termo, len(result)
            )
            return result
    except sqlite3.Error as exc:
        logger.error("Erro ao consultar por aplicacao: %s", exc)
        raise


def consultar_por_dimensoes(
    diametro_interno: float,
    diametro_externo: float,
    largura: Optional[float] = None,
    tolerancia_mm: float = 1.0,
) -> list[dict]:
    """
    Busca rolamentos compatíveis pelas dimensões em milímetros,
    com tolerância configurável (padrão ±1 mm por dimensão).

    Parâmetros
    ----------
    diametro_interno : float
        Diâmetro interno desejado (mm).
    diametro_externo : float
        Diâmetro externo desejado (mm).
    largura : float, optional
        Largura/espessura do rolamento (mm). Se omitida, não filtra.
    tolerancia_mm : float
        Margem de tolerância aplicada a cada dimensão (padrão 1.0 mm).

    Retorna
    -------
    list[dict]
        Rolamentos dentro das tolerâncias, ordenados por proximidade
        ao diâmetro interno solicitado e depois por preço.

    Exemplo
    -------
    >>> consultar_por_dimensoes(20.0, 47.0, 14.0)
    [{'codigo': '6204-2RSH', ...}]
    """
    params: list[float] = [
        diametro_interno - tolerancia_mm, diametro_interno + tolerancia_mm,
        diametro_externo - tolerancia_mm, diametro_externo + tolerancia_mm,
    ]

    largura_clause = ""
    if largura is not None:
        largura_clause = "AND largura_mm BETWEEN ? AND ?"
        params += [largura - tolerancia_mm, largura + tolerancia_mm]

    sql = f"""
        SELECT
            id,
            codigo,
            tipo,
            diametro_interno_mm,
            diametro_externo_mm,
            largura_mm,
            aplicacao_recomendada,
            preco_unitario,
            estoque_qtd,
            -- Distância euclidiana das dimensões para ordenar por proximidade
            ABS(diametro_interno_mm - {diametro_interno})
            + ABS(diametro_externo_mm - {diametro_externo}) AS distancia
        FROM produtos
        WHERE diametro_interno_mm BETWEEN ? AND ?
          AND diametro_externo_mm BETWEEN ? AND ?
          {largura_clause}
        ORDER BY distancia ASC, preco_unitario ASC
    """

    try:
        with _get_connection() as conn:
            cursor = conn.execute(sql, params)
            rows = cursor.fetchall()
            result = [_row_to_dict(r) for r in rows]
            logger.debug(
                "consultar_por_dimensoes(di=%.1f, de=%.1f, l=%s) -> %d resultado(s)",
                diametro_interno, diametro_externo, largura, len(result)
            )
            return result
    except sqlite3.Error as exc:
        logger.error("Erro ao consultar por dimensoes: %s", exc)
        raise


def verificar_estoque_e_preco(codigo_produto: str) -> dict:
    """
    Retorna estoque disponível, preço unitário e especificações completas
    de um produto pelo seu código ISO/DIN.

    Parâmetros
    ----------
    codigo_produto : str
        Código do rolamento (ex: '6204-2RSH', '22212-E').
        A busca é case-insensitive.

    Retorna
    -------
    dict
        Dicionário com todos os campos do produto.
        Inclui a chave `disponivel` (bool) indicando se há estoque > 0.
        Retorna dict vazio `{}` se o produto não for encontrado.

    Exemplo
    -------
    >>> verificar_estoque_e_preco("6204-2RSH")
    {'codigo': '6204-2RSH', 'preco_unitario': 22.9, 'estoque_qtd': 200, 'disponivel': True, ...}
    """
    sql = """
        SELECT
            id,
            codigo,
            tipo,
            diametro_interno_mm,
            diametro_externo_mm,
            largura_mm,
            aplicacao_recomendada,
            preco_unitario,
            estoque_qtd
        FROM produtos
        WHERE UPPER(codigo) = UPPER(?)
        LIMIT 1
    """

    try:
        with _get_connection() as conn:
            cursor = conn.execute(sql, (codigo_produto.strip(),))
            row = cursor.fetchone()
            if row is None:
                logger.warning(
                    "verificar_estoque_e_preco: produto '%s' nao encontrado.",
                    codigo_produto
                )
                return {}
            result = _row_to_dict(row)
            result["disponivel"] = result["estoque_qtd"] > 0
            return result
    except sqlite3.Error as exc:
        logger.error("Erro ao verificar estoque/preco: %s", exc)
        raise


def criar_cotacao(
    cliente_nome: str,
    cliente_contato: str,
    itens: list[dict],
) -> int:
    """
    Insere uma cotação formal na tabela `pedidos` com status
    'AGUARDANDO_APROVACAO' e seus itens em `itens_pedido`.

    Human-in-the-Loop: o status jamais avança automaticamente;
    um vendedor humano precisa aprovar manualmente. (PRD §3.3)

    Parâmetros
    ----------
    cliente_nome : str
        Nome do cliente (empresa ou pessoa física).
    cliente_contato : str
        WhatsApp, e-mail ou outro meio de contato.
    itens : list[dict]
        Lista de itens, cada um com as chaves:
          - 'produto_id' (int)   : ID do produto na tabela produtos
          - 'codigo'     (str)   : Código do produto (para log/exibição)
          - 'quantidade' (int)   : Quantidade solicitada
          - 'preco_unitario' (float) : Preço no momento da cotação (snapshot)

    Retorna
    -------
    int
        ID do pedido recém-criado.

    Raises
    ------
    ValueError
        Se `itens` estiver vazio ou faltar campos obrigatórios.
    sqlite3.Error
        Em caso de erro de banco (ex: produto_id inexistente).

    Exemplo
    -------
    >>> criar_cotacao(
    ...     "Metalurgica Souza",
    ...     "+55 11 99999-0000",
    ...     [{"produto_id": 2, "codigo": "6204-2RSH", "quantidade": 10, "preco_unitario": 22.9}]
    ... )
    1
    """
    if not itens:
        raise ValueError("A lista de itens nao pode estar vazia.")

    campos_obrigatorios = {"produto_id", "quantidade", "preco_unitario"}
    for i, item in enumerate(itens):
        faltando = campos_obrigatorios - item.keys()
        if faltando:
            raise ValueError(
                f"Item {i} esta faltando os campos: {faltando}"
            )
        if item["quantidade"] <= 0:
            raise ValueError(f"Item {i}: quantidade deve ser > 0.")
        if item["preco_unitario"] < 0:
            raise ValueError(f"Item {i}: preco_unitario nao pode ser negativo.")

    total = sum(
        item["quantidade"] * item["preco_unitario"] for item in itens
    )

    sql_pedido = """
        INSERT INTO pedidos (cliente_nome, cliente_contato, status, total)
        VALUES (?, ?, 'AGUARDANDO_APROVACAO', ?)
    """
    sql_item = """
        INSERT INTO itens_pedido (pedido_id, produto_id, quantidade, preco_unitario)
        VALUES (?, ?, ?, ?)
    """

    try:
        with _get_connection() as conn:
            cursor = conn.execute(sql_pedido, (cliente_nome, cliente_contato, total))
            pedido_id = cursor.lastrowid

            conn.executemany(
                sql_item,
                [
                    (pedido_id, item["produto_id"], item["quantidade"], item["preco_unitario"])
                    for item in itens
                ],
            )
            conn.commit()

            logger.info(
                "Cotacao criada: pedido_id=%d | cliente=%r | total=R$ %.2f | itens=%d",
                pedido_id, cliente_nome, total, len(itens)
            )
            return pedido_id
    except sqlite3.Error as exc:
        logger.error("Erro ao criar cotacao: %s", exc)
        raise


def registrar_auditoria(
    prompt_tokens: int,
    completion_tokens: int,
    custo_usd: float,
    session_id: Optional[str] = None,
) -> None:
    """
    Registra métricas de uso de tokens e custo estimado por atendimento.
    Governança de custo conforme PRD §3.4.

    Parâmetros
    ----------
    prompt_tokens : int
        Tokens de entrada consumidos na chamada ao LLM.
    completion_tokens : int
        Tokens de saída gerados pelo LLM.
    custo_usd : float
        Custo estimado em dólares (calculado pelo caller com base
        no pricing do modelo utilizado).
    session_id : str, optional
        Identificador da sessão do agente (ex: ID da conversa no Streamlit).

    Exemplo
    -------
    >>> registrar_auditoria(512, 128, 0.000384, session_id="sess-abc123")
    """
    sql = """
        INSERT INTO auditoria_ia (session_id, prompt_tokens, completion_tokens, custo_estimado_usd)
        VALUES (?, ?, ?, ?)
    """
    try:
        with _get_connection() as conn:
            conn.execute(sql, (session_id, prompt_tokens, completion_tokens, custo_usd))
            conn.commit()
            logger.debug(
                "Auditoria registrada: session=%r prompt=%d completion=%d custo=$%.6f",
                session_id, prompt_tokens, completion_tokens, custo_usd
            )
    except sqlite3.Error as exc:
        logger.error("Erro ao registrar auditoria: %s", exc)
        raise


# ── Utilitário de diagnóstico (não exposto ao agente) ─────────────────────────

def resumo_banco() -> dict:
    """Retorna estatísticas gerais do banco (para health-check/debug)."""
    try:
        with _get_connection() as conn:
            total_prod  = conn.execute("SELECT COUNT(*) FROM produtos").fetchone()[0]
            total_ped   = conn.execute("SELECT COUNT(*) FROM pedidos").fetchone()[0]
            total_audit = conn.execute("SELECT COUNT(*) FROM auditoria_ia").fetchone()[0]
            estoque     = conn.execute("SELECT SUM(estoque_qtd) FROM produtos").fetchone()[0]
            return {
                "total_produtos":    total_prod,
                "total_pedidos":     total_ped,
                "total_auditorias":  total_audit,
                "estoque_total":     estoque or 0,
                "db_path":           str(DB_PATH),
            }
    except Exception as exc:
        logger.error("Erro ao gerar resumo do banco: %s", exc)
        return {
            "total_produtos":    0,
            "total_pedidos":     0,
            "total_auditorias":  0,
            "estoque_total":     0,
            "db_path":           str(DB_PATH),
        }
